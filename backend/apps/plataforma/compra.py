"""Compra pública (self-service): catálogo, checagens, pedido, código no e-mail e criação da
empresa (`docs/api/compra.md`, T-435; PLT-01, PLT-11, PLT-13, PLT-16, USR-01).

O pedido não é a empresa: ela só nasce depois do código de 6 dígitos (D-430-01), numa tarefa do
Celery que chama `services.criar_empresa` com `origem=compra`. Status do pedido só muda por aqui,
pela máquina de estados (com auditoria no public, sem dados pessoais). O código nunca é gravado
(hash Argon2) nem vai para log; o IP também não (HMAC).
"""

import hashlib
import hmac
import logging
import re
import secrets
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django_tenants.utils import get_public_schema_name, schema_context, schema_exists

from comum import relogio
from comum.auditoria import Categoria, registrar_evento
from comum.dinheiro import formatar_reais
from comum.documentos import UFS, cnpj_valido, so_digitos
from comum.erros import Conflito, ErroDeNegocio, ErroDeValidacao, MuitasTentativas, NaoEncontrado
from comum.estados import transicionar
from integracoes.cnpj import consultar_cnpj

from . import catalogo
from .calendario import dia_e_mes
from .models import (
    DADOS_PESSOAIS_DO_PEDIDO,
    DIAS_DE_TESTE,
    Empresa,
    FormaAssinatura,
    Origem,
    PedidoCompra,
    Plano,
    SituacaoCnpj,
    StatusPedidoCompra,
    validar_nome_sem_quebra,
)
from .situacao_cnpj import (
    AVISO_JA_FOI_CLIENTE,
    MENSAGEM_EM_USO,
    MENSAGEM_FATURA_EM_ATRASO,
    situacao_do_cnpj,
)

logger = logging.getLogger(__name__)

VALIDADE_DO_CODIGO = timedelta(minutes=15)
VALIDADE_DO_PEDIDO = timedelta(hours=24)
ANDAMENTO_VISIVEL = timedelta(hours=24)  # depois do `pronto`, a chave deixa de responder
GUARDA_DO_PEDIDO_EXPIRADO = timedelta(days=7)
TENTATIVAS_DO_CODIGO = 5
REENVIOS = 3
INTERVALO_DO_REENVIO = timedelta(seconds=60)
PEDIDOS_POR_EMAIL_NO_DIA = 3
PEDIDOS_POR_CNPJ_NO_DIA = 3

SUBDOMINIO = re.compile(r"^[a-z0-9-]{3,30}$")
FORMATO_DO_SUBDOMINIO = "Use de 3 a 30 letras sem acento, números ou hífen."
SUBDOMINIO_PROIBIDO = "Este endereço não pode ser usado. Escolha outro."
SUBDOMINIO_EM_USO = "Este endereço já está em uso. Escolha outro."
PEDIDO_NAO_ENCONTRADO = "Este pedido não vale mais. Comece de novo pela escolha do plano."
MENSAGEM_FALHA = (
    "Não conseguimos criar o seu sistema agora. "
    "A equipe Giro já foi avisada e fala com você por e-mail."
)
MENSAGEM_ACIMA_DO_TETO = (
    "Recebemos o seu pedido. A equipe Giro libera o seu sistema e avisa você por e-mail."
)
# Corpo com dado de cartão é recusado antes de qualquer log (ADR 0023).
CAMPOS_DE_CARTAO = frozenset(
    {"numero_cartao", "cartao", "numero", "validade", "cvv", "cvc", "codigo_seguranca", "card"}
)
TEXTOS_DOS_PASSOS = (
    ("administrador", "Conta de administrador criada"),
    ("banco", "Banco de dados exclusivo da empresa"),
    ("endereco", "Endereço de acesso reservado"),
    ("assinatura", ""),  # montado pela empresa criada (teste ou 1ª fatura hoje)
)


# --- Erros próprios da compra ---


class PedidoNaoEncontrado(NaoEncontrado):
    """404 igual para chave desconhecida, expirada ou vencida (`compra.md`)."""

    def __init__(self) -> None:
        super().__init__("pedido_nao_encontrado", PEDIDO_NAO_ENCONTRADO)


class ErroDoCodigo(ErroDeNegocio):
    status_http = 400

    def como_dict(self) -> dict[str, Any]:
        # `tentativas_restantes` no primeiro nível, como no contrato.
        return {"codigo": self.codigo, "mensagem": self.mensagem, **(self.detalhes or {})}


class CartaoNaoAceito(ErroDeNegocio):
    status_http = 400

    def __init__(self) -> None:
        super().__init__(
            "cartao_nao_aceito",
            "Os dados do cartão não passam pelo Giro. Você paga na página do parceiro.",
        )


class LimiteDaCompra(MuitasTentativas):
    """429 que não diz qual limite estourou (`compra.md`)."""

    def __init__(
        self, mensagem: str = "Muitas tentativas. Tente de novo mais tarde.", codigo: str = "limite"
    ) -> None:
        super().__init__(codigo, mensagem)

    def como_dict(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "mensagem": self.mensagem}


# --- Utilidades ---


def codigo_do_plano(plano: Plano) -> str:
    return slugify(plano.nome)


def hash_do_ip(ip: str | None) -> str:
    """HMAC do IP com a chave dos segredos: o IP em claro não é gravado."""
    if not ip:
        return ""
    chave = hmac.new(str(settings.GIRO_PEPPER_HMAC).encode(), b"compra-ip", hashlib.sha256)
    return hmac.new(chave.digest(), ip.encode(), hashlib.sha256).hexdigest()


def mascarar_email(email: str) -> str:
    """`m•••••@motorapida.com.br`: a tela diz para onde foi o código sem repetir o e-mail."""
    nome, _, dominio = email.partition("@")
    return f"{nome[:1]}•••••@{dominio}"


def _novo_codigo() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _planos_a_venda() -> list[Plano]:
    with schema_context(get_public_schema_name()):
        return list(Plano.objects.filter(ativo=True, a_venda=True).order_by("ordem", "id"))


def _plano_pelo_codigo(codigo: Any) -> Plano:
    from .services import PlanoForaDaVenda, fora_da_venda

    if not isinstance(codigo, str):
        raise PlanoForaDaVenda("Escolha um dos planos da lista.")
    with schema_context(get_public_schema_name()):
        for plano in Plano.objects.filter(ativo=True):
            if codigo_do_plano(plano) == codigo:
                if not plano.a_venda:
                    raise PlanoForaDaVenda(fora_da_venda(plano))
                return plano
    raise PlanoForaDaVenda("Escolha um dos planos da lista.")


# --- Catálogo (GET planos) ---


@dataclass(frozen=True)
class DatasDoTeste:
    inicio: date
    fim: date
    lembrete: date
    primeira_fatura: date


def datas_do_teste(hoje: date) -> DatasDoTeste:
    """PLT-01 e PLT-02: teste de 14 dias, lembrete 3 dias antes da 1ª fatura."""
    fim = hoje + timedelta(days=DIAS_DE_TESTE)
    primeira = fim + timedelta(days=1)
    return DatasDoTeste(hoje, fim, primeira - timedelta(days=3), primeira)


def catalogo_a_venda() -> dict[str, Any]:
    """`GET /api/publico/compra/planos/`: só os planos à venda (PLT-11), com os textos do
    catálogo e as datas do teste de hoje."""
    planos = []
    for plano in _planos_a_venda():
        textos = catalogo.textos(plano.nome)
        planos.append(
            {
                "codigo": codigo_do_plano(plano),
                "nome": plano.nome,
                "descricao": textos.descricao,
                "mensal_centavos": int(plano.preco_mensal_centavos),
                "anual_centavos": plano.preco_anual_centavos,
                "limites": {
                    "veiculos": plano.limite_veiculos,
                    "filiais": plano.limite_filiais,
                    "usuarios": plano.limite_usuarios,
                },
                "inclui": list(textos.inclui),
                "destaque": plano.nome == catalogo.PLANO_EM_DESTAQUE,
            }
        )
    datas = datas_do_teste(relogio.hoje())
    return {
        "planos": planos,
        "teste": {
            "dias": DIAS_DE_TESTE,
            "inicio": datas.inicio,
            "fim": datas.fim,
            "lembrete": datas.lembrete,
            "primeira_fatura": datas.primeira_fatura,
        },
    }


# --- Checagem do CNPJ (PLT-16) e consulta pública (ADR 0039) ---


def _validar_cnpj(cnpj: Any) -> str:
    digitos = so_digitos(cnpj if isinstance(cnpj, str) else "")
    if not cnpj_valido(digitos):
        raise ErroDeValidacao({"cnpj": ["Confira o CNPJ. Os números não batem."]})
    return digitos


def checar_cnpj(cnpj: Any) -> dict[str, Any]:
    """`POST cnpj/`: a situação da `PLT-16` traduzida para a tela e, se pode comprar, os dados
    públicos da Receita para preencher o checkout (a pessoa confere e edita; ADR 0039)."""
    digitos = _validar_cnpj(cnpj)
    situacao = situacao_do_cnpj(digitos).situacao
    if situacao == SituacaoCnpj.EM_USO:
        return {"pode_comprar": False, "codigo": "cnpj_em_uso", "mensagem": MENSAGEM_EM_USO}
    if situacao == SituacaoCnpj.FATURA_EM_ATRASO:
        return {
            "pode_comprar": False,
            "codigo": "fatura_anterior_em_atraso",
            "mensagem": MENSAGEM_FATURA_EM_ATRASO,
        }
    resposta: dict[str, Any] = {
        "pode_comprar": True,
        "teste_gratis": situacao == SituacaoCnpj.NOVA,
        "aviso": None,
        "dados": None,
    }
    if situacao == SituacaoCnpj.JA_FOI_CLIENTE:
        resposta["aviso"] = AVISO_JA_FOI_CLIENTE
        resposta["primeira_fatura"] = relogio.hoje()
    dados = consultar_cnpj(digitos)
    if dados is not None:
        resposta["dados"] = {
            "razao_social": dados.razao_social,
            "nome_fantasia": dados.nome_fantasia,
            "cidade": dados.cidade,
            "uf": dados.uf if dados.uf in UFS else "",
            "ativo": dados.ativo,
        }
    return resposta


# --- Endereço de acesso ---


def _formato_do_subdominio(subdominio: str) -> str | None:
    from .services import _PREFIXO_DO_POSTGRES, SUBDOMINIOS_RESERVADOS

    if not SUBDOMINIO.match(subdominio):
        return FORMATO_DO_SUBDOMINIO
    if subdominio.startswith(_PREFIXO_DO_POSTGRES) or subdominio in (
        SUBDOMINIOS_RESERVADOS | {settings.SUBDOMINIO_PLATAFORMA}
    ):
        return SUBDOMINIO_PROIBIDO
    return None


def subdominio_livre(subdominio: str) -> bool:
    """Livre = nenhuma empresa com ele, nem apagada (continua reservado, `PLT-16`), e nenhum
    schema com o nome no Postgres."""
    from .services import schema_do_subdominio

    schema = schema_do_subdominio(subdominio)
    with schema_context(get_public_schema_name()):
        if Empresa.objects.filter(subdominio=subdominio).exists():
            return False
        if Empresa.objects.filter(schema_name=schema).exists():
            return False
        return not schema_exists(schema)


def _base_da_sugestao(nome: str) -> str:
    """Tira acentos, espaços e pontuação: "Moto Rápida" vira `motorapida`."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())[:28]


def sugerir_subdominio(nome: str) -> str | None:
    base = _base_da_sugestao(nome)
    if len(base) < 3:
        base = (base + "locadora")[:28]
    if _formato_do_subdominio(base) is None and subdominio_livre(base):
        return base
    for numero in range(2, 100):
        candidato = f"{base[: 30 - len(str(numero))]}{numero}"
        if _formato_do_subdominio(candidato) is None and subdominio_livre(candidato):
            return candidato
    return None


def checar_subdominio(dados: dict[str, Any]) -> dict[str, Any]:
    """`POST subdominio/`: com `subdominio`, diz se está livre; com `nome`, sugere um."""
    from .services import endereco_de_acesso

    subdominio = dados.get("subdominio")
    if not isinstance(subdominio, str) or not subdominio.strip():
        nome = dados.get("nome")
        if not isinstance(nome, str) or not nome.strip():
            raise ErroDeValidacao({"subdominio": [FORMATO_DO_SUBDOMINIO]})
        sugestao = sugerir_subdominio(nome)
        if sugestao is None:
            raise ErroDeValidacao({"subdominio": [FORMATO_DO_SUBDOMINIO]})
        return {
            "subdominio": sugestao,
            "disponivel": True,
            "endereco": endereco_de_acesso(sugestao),
        }
    subdominio = subdominio.strip().lower()
    erro = _formato_do_subdominio(subdominio)
    if erro:
        raise ErroDeValidacao({"subdominio": [erro]})
    if subdominio_livre(subdominio):
        return {
            "subdominio": subdominio,
            "disponivel": True,
            "endereco": endereco_de_acesso(subdominio),
        }
    return {
        "subdominio": subdominio,
        "disponivel": False,
        "sugestao": sugerir_subdominio(subdominio),
        "mensagem": SUBDOMINIO_EM_USO,
    }


# --- Pedido (POST pedidos) ---


def _texto(dados: Any, campo: str) -> str:
    valor = dados.get(campo) if isinstance(dados, dict) else None
    return valor.strip() if isinstance(valor, str) else ""


def _tem_cartao(dados: Any) -> bool:
    if isinstance(dados, dict):
        return any(
            chave.lower() in CAMPOS_DE_CARTAO or _tem_cartao(valor)
            for chave, valor in dados.items()
        )
    return False


@dataclass(frozen=True)
class DadosDoPedido:
    plano: Plano
    ciclo: str
    forma_pagamento: str
    nome: str
    email: str
    celular: str
    aceita_whatsapp: bool
    cnpj: str
    razao_social: str
    nome_exibicao: str
    cidade: str
    uf: str
    subdominio: str


def _ler_pedido(corpo: Any) -> DadosDoPedido:
    """Valida o corpo inteiro e junta todos os erros de campo num 400 só."""
    if not isinstance(corpo, dict):
        raise ErroDeValidacao({"corpo": ["Envie os dados do pedido."]})
    if _tem_cartao(corpo):
        raise CartaoNaoAceito
    plano = _plano_pelo_codigo(corpo.get("plano"))
    bruto_administrador = corpo.get("administrador")
    administrador: dict[str, Any] = (
        bruto_administrador if isinstance(bruto_administrador, dict) else {}
    )
    bruto_empresa = corpo.get("empresa")
    empresa: dict[str, Any] = bruto_empresa if isinstance(bruto_empresa, dict) else {}
    erros: dict[str, list[str]] = {}

    ciclo = corpo.get("ciclo")
    if ciclo not in Empresa.Ciclo.values:
        erros["ciclo"] = ["Escolha mensal ou anual."]
    forma = corpo.get("forma_pagamento") or ""
    if forma and forma not in FormaAssinatura.values:
        erros["forma_pagamento"] = ["Escolha cartão, Pix ou boleto."]
    if corpo.get("aceite_termos") is not True:
        erros["aceite_termos"] = [
            "Para continuar, aceite os Termos de uso e o Acordo de tratamento de dados."
        ]

    nome = _texto(administrador, "nome")
    if not nome:
        erros["administrador.nome"] = ["Informe seu nome completo."]
    elif len(nome) > 150:
        erros["administrador.nome"] = ["Use até 150 caracteres."]
    email = _texto(administrador, "email").lower()
    try:
        validate_email(email)
    except DjangoValidationError:
        erros["administrador.email"] = ["Confira o e-mail."]
    celular = so_digitos(_texto(administrador, "celular"))
    if len(celular) not in (10, 11):
        erros["administrador.celular"] = ["Confira o celular com DDD."]

    cnpj = so_digitos(_texto(empresa, "cnpj"))
    if not cnpj_valido(cnpj):
        erros["empresa.cnpj"] = ["Confira o CNPJ. Os números não batem."]
    razao_social = _texto(empresa, "razao_social")
    if not razao_social:
        erros["empresa.razao_social"] = ["Informe a razão social."]
    elif len(razao_social) > 150:
        erros["empresa.razao_social"] = ["Use até 150 caracteres."]
    nome_exibicao = _texto(empresa, "nome_exibicao")
    if not nome_exibicao:
        erros["empresa.nome_exibicao"] = ["Informe o nome da empresa."]
    elif len(nome_exibicao) > 80:
        erros["empresa.nome_exibicao"] = ["Use até 80 caracteres."]
    else:
        try:
            validar_nome_sem_quebra(nome_exibicao)
        except DjangoValidationError as erro:
            erros["empresa.nome_exibicao"] = list(erro.messages)
    for campo in ("nome", "razao_social", "nome_exibicao"):
        valor = nome if campo == "nome" else _texto(empresa, campo)
        if "\n" in valor or "\r" in valor:
            erros.setdefault(
                f"{'administrador' if campo == 'nome' else 'empresa'}.{campo}",
                ["Use um nome sem quebra de linha."],
            )
    cidade = _texto(empresa, "cidade")
    if not cidade:
        erros["empresa.cidade"] = ["Informe a cidade."]
    elif len(cidade) > 80:
        erros["empresa.cidade"] = ["Use até 80 caracteres."]
    uf = _texto(empresa, "uf").upper()
    if uf not in UFS:
        erros["empresa.uf"] = ["Escolha a UF."]
    subdominio = _texto(empresa, "subdominio").lower()
    erro_subdominio = _formato_do_subdominio(subdominio)
    if erro_subdominio:
        erros["empresa.subdominio"] = [erro_subdominio]
    if erros:
        raise ErroDeValidacao(erros)
    return DadosDoPedido(
        plano=plano,
        ciclo=str(ciclo),
        forma_pagamento=str(forma),
        nome=nome,
        email=email,
        celular=celular,
        aceita_whatsapp=administrador.get("aceita_whatsapp") is True,
        cnpj=cnpj,
        razao_social=razao_social,
        nome_exibicao=nome_exibicao,
        cidade=cidade,
        uf=uf,
        subdominio=subdominio,
    )


def _conferir_cnpj_e_subdominio(cnpj: str, subdominio: str) -> None:
    """As mesmas respostas das checagens, agora como 409 (não reserva nada)."""
    situacao = situacao_do_cnpj(cnpj).situacao
    if situacao == SituacaoCnpj.EM_USO:
        raise Conflito("cnpj_em_uso", MENSAGEM_EM_USO)
    if situacao == SituacaoCnpj.FATURA_EM_ATRASO:
        raise Conflito("fatura_anterior_em_atraso", MENSAGEM_FATURA_EM_ATRASO)
    if not subdominio_livre(subdominio):
        raise Conflito("subdominio_em_uso", SUBDOMINIO_EM_USO)


def _conferir_limites_do_pedido(dados: DadosDoPedido, agora: Any) -> None:
    """3 pedidos por dia por e-mail e por CNPJ (`compra.md`). Conta no banco, porque o pedido
    que substitui outro do mesmo e-mail e CNPJ não conta de novo no limite por CNPJ."""
    desde = agora - timedelta(days=1)
    recentes = PedidoCompra.objects.filter(criado_em__gte=desde)
    if recentes.filter(administrador_email=dados.email).count() >= PEDIDOS_POR_EMAIL_NO_DIA:
        raise LimiteDaCompra
    outros_emails = (
        recentes.filter(cnpj=dados.cnpj)
        .exclude(administrador_email=dados.email)
        .values("administrador_email")
        .distinct()
        .count()
    )
    if outros_emails + 1 > PEDIDOS_POR_CNPJ_NO_DIA:
        raise LimiteDaCompra


def _enviar_codigo(email: str, codigo: str) -> None:
    """E-mail com o código, com a marca do Giro (tela de compra). O código não vai para log."""
    try:
        send_mail(
            "Seu código para criar o sistema no Giro",
            f"Seu código é {codigo}. Ele vale por 15 minutos. "
            "Se você não pediu, ignore este e-mail.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
    except Exception:  # o e-mail falhou: a pessoa pede outro código
        logger.warning("Falha ao enviar o código da compra pública", exc_info=False)


def criar_pedido_compra(corpo: Any, ip: str | None) -> dict[str, Any]:
    """ "Criar minha conta": grava o pedido e manda o código. Não cria empresa (D-430-01)."""
    dados = _ler_pedido(corpo)
    agora = relogio.agora()
    codigo = _novo_codigo()
    with schema_context(get_public_schema_name()), transaction.atomic():
        _conferir_cnpj_e_subdominio(dados.cnpj, dados.subdominio)
        anteriores = list(
            PedidoCompra.objects.select_for_update().filter(
                administrador_email=dados.email,
                cnpj=dados.cnpj,
                status=StatusPedidoCompra.AGUARDANDO_CONFIRMACAO,
            )
        )
        if not anteriores:
            _conferir_limites_do_pedido(dados, agora)
        for anterior in anteriores:  # o pedido novo substitui o anterior
            transicionar(anterior, StatusPedidoCompra.EXPIRADO, acao="compra.substituir")
        pedido = PedidoCompra.objects.create(
            plano=dados.plano,
            ciclo=dados.ciclo,
            forma_pagamento=dados.forma_pagamento,
            administrador_nome=dados.nome,
            administrador_email=dados.email,
            administrador_celular=dados.celular,
            aceita_whatsapp=dados.aceita_whatsapp,
            cnpj=dados.cnpj,
            razao_social=dados.razao_social,
            nome_exibicao=dados.nome_exibicao,
            cidade=dados.cidade,
            uf=dados.uf,
            subdominio=dados.subdominio,
            codigo_hash=make_password(codigo),
            codigo_expira_em=agora + VALIDADE_DO_CODIGO,
            codigo_enviado_em=agora,
            aceite_termos_versao=str(settings.GIRO_TERMOS_VERSAO),
            aceite_termos_em=agora,
            ip_hash=hash_do_ip(ip),
            expira_em=agora + VALIDADE_DO_PEDIDO,
        )
        registrar_evento("compra.pedido", Categoria.CONFIGURACOES, objeto=pedido, regra="PLT-01")
        email = dados.email
        transaction.on_commit(lambda: _enviar_codigo(email, codigo))
    mascarado = mascarar_email(dados.email)
    return {
        "chave": pedido.chave,
        "status": pedido.status,
        "email": mascarado,
        "codigo_expira_em": pedido.codigo_expira_em,
        "mensagem": (
            f"Enviamos um código de 6 dígitos para {mascarado}. "
            "Digite o código para criar o seu sistema."
        ),
    }


# --- Confirmar e reenviar o código ---


def _pedido_travado(chave: Any) -> PedidoCompra:
    """O pedido vivo pela chave, com a linha travada. Expirado ou desconhecido: o mesmo 404."""
    try:
        chave_uuid = UUID(str(chave))
    except ValueError as erro:
        raise PedidoNaoEncontrado from erro
    pedido: PedidoCompra | None = (
        PedidoCompra.objects.select_for_update().filter(chave=chave_uuid).first()
    )
    if pedido is None or pedido.status == StatusPedidoCompra.EXPIRADO:
        raise PedidoNaoEncontrado
    if (
        pedido.status == StatusPedidoCompra.AGUARDANDO_CONFIRMACAO
        and pedido.expira_em <= relogio.agora()
    ):
        raise PedidoNaoEncontrado
    return pedido


def criadas_hoje_pela_compra() -> int:
    """Pedidos que já passaram do teto do dia: os que criaram ou estão criando hoje (D-430-08)."""
    # `atualizado_em` é gravado pelo relógio real (auto_now), então o dia também é o real.
    inicio = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return PedidoCompra.objects.filter(
        status__in=[StatusPedidoCompra.CRIANDO, StatusPedidoCompra.PRONTO],
        atualizado_em__gte=inicio,
    ).count()


def _avisar_equipe(assunto: str, texto: str) -> None:
    try:
        send_mail(assunto, texto, settings.DEFAULT_FROM_EMAIL, [settings.GIRO_EMAIL_EQUIPE])
    except Exception:
        logger.warning("Falha ao avisar a equipe Giro: %s", assunto)


def _agendar_criacao(pedido: PedidoCompra) -> None:
    from .tasks import plataforma_executar_pedido_compra

    pedido_id = pedido.pk
    transaction.on_commit(lambda: plataforma_executar_pedido_compra.delay(pedido_id))


def confirmar_pedido_compra(chave: Any, codigo: Any) -> dict[str, Any]:
    """Código certo e no prazo: `confirmado` e, abaixo do teto do dia, `criando` com a tarefa
    agendada. Já confirmado: devolve o andamento (o duplo clique não cria duas empresas)."""
    erro: ErroDoCodigo | None = None
    with schema_context(get_public_schema_name()), transaction.atomic():
        pedido = _pedido_travado(chave)
        if pedido.status != StatusPedidoCompra.AGUARDANDO_CONFIRMACAO:
            return andamento_do_pedido(pedido.chave)
        agora = relogio.agora()
        texto = codigo if isinstance(codigo, str) else ""
        if pedido.tentativas_codigo >= TENTATIVAS_DO_CODIGO or not pedido.codigo_hash:
            erro = ErroDoCodigo("codigo_bloqueado", "Muitas tentativas. Peça um código novo.")
        elif pedido.codigo_expira_em is None or pedido.codigo_expira_em <= agora:
            erro = ErroDoCodigo("codigo_expirado", "O código venceu. Peça um código novo.")
        elif not (
            len(texto) == 6 and texto.isdigit() and check_password(texto, pedido.codigo_hash)
        ):
            pedido.tentativas_codigo += 1
            restantes = TENTATIVAS_DO_CODIGO - pedido.tentativas_codigo
            if restantes <= 0:
                pedido.codigo_hash = ""  # o código morre na 5ª errada
                erro = ErroDoCodigo("codigo_bloqueado", "Muitas tentativas. Peça um código novo.")
            else:
                palavra = "tentativa" if restantes == 1 else "tentativas"
                erro = ErroDoCodigo(
                    "codigo_invalido",
                    f"Código incorreto. Você tem mais {restantes} {palavra}.",
                    {"tentativas_restantes": restantes},
                )
            pedido.save(update_fields=["tentativas_codigo", "codigo_hash", "atualizado_em"])
        if erro is None:
            pedido.codigo_hash = ""
            transicionar(
                pedido,
                StatusPedidoCompra.CONFIRMADO,
                acao="compra.confirmar",
                regra="PLT-01",
                mais_campos=("codigo_hash",),
            )
            if criadas_hoje_pela_compra() >= int(settings.GIRO_COMPRA_TETO_DIARIO):
                transaction.on_commit(
                    lambda: _avisar_equipe(
                        "Compra pública acima do teto do dia",
                        f"O pedido {pedido.chave} foi confirmado e espera a liberação pelo "
                        "Django Admin (D-430-08).",
                    )
                )
            else:
                transicionar(pedido, StatusPedidoCompra.CRIANDO, acao="compra.criar_empresa")
                _agendar_criacao(pedido)
    if erro is not None:  # fora da transação: a tentativa errada fica gravada
        raise erro
    return andamento_do_pedido(pedido.chave)


def liberar_pedido_compra(pedido: PedidoCompra) -> None:
    """A equipe libera, pelo Django Admin, o pedido confirmado acima do teto (D-430-08)."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        pedido = PedidoCompra.objects.select_for_update().get(pk=pedido.pk)
        if pedido.status != StatusPedidoCompra.CONFIRMADO:
            raise Conflito("transicao_pedido", "Só um pedido confirmado espera liberação.")
        transicionar(pedido, StatusPedidoCompra.CRIANDO, acao="compra.liberar")
        _agendar_criacao(pedido)


def reenviar_codigo(chave: Any) -> dict[str, Any]:
    """Código novo (o anterior deixa de valer): até 3 por pedido, 60 s entre eles."""
    codigo = _novo_codigo()
    with schema_context(get_public_schema_name()), transaction.atomic():
        pedido = _pedido_travado(chave)
        if pedido.status != StatusPedidoCompra.AGUARDANDO_CONFIRMACAO:
            raise PedidoNaoEncontrado
        agora = relogio.agora()
        if pedido.reenvios >= REENVIOS:
            raise LimiteDaCompra("Você já pediu 3 códigos. Comece de novo pela escolha do plano.")
        if pedido.codigo_enviado_em and agora - pedido.codigo_enviado_em < INTERVALO_DO_REENVIO:
            raise LimiteDaCompra("Aguarde um minuto para pedir outro código.", "limite_reenvio")
        pedido.codigo_hash = make_password(codigo)
        pedido.codigo_expira_em = agora + VALIDADE_DO_CODIGO
        pedido.codigo_enviado_em = agora
        pedido.tentativas_codigo = 0
        pedido.reenvios += 1
        pedido.save(
            update_fields=[
                "codigo_hash",
                "codigo_expira_em",
                "codigo_enviado_em",
                "tentativas_codigo",
                "reenvios",
                "atualizado_em",
            ]
        )
        email = pedido.administrador_email
        transaction.on_commit(lambda: _enviar_codigo(email, codigo))
    return {"codigo_expira_em": pedido.codigo_expira_em, "mensagem": "Enviamos um código novo."}


# --- Andamento (GET pedido) ---


def _texto_da_assinatura(empresa: Empresa) -> str:
    if empresa.status == Empresa.Status.EM_TESTE and empresa.teste_fim:
        return f"Teste de {DIAS_DE_TESTE} dias ativo, até {dia_e_mes(empresa.teste_fim)}"
    valor = formatar_reais(int(empresa.preco_contratado_centavos))
    return f"1ª fatura de {valor} vence hoje"


_LINK_DO_CONVITE: list[Callable[[str], str | None]] = []


def registrar_link_do_convite(gerar: Callable[[str], str | None]) -> None:
    """`contas` registra no `ready` quem gera o link do convite do administrador (ADR 0011: a
    plataforma fica acima de `contas` e não a importa)."""
    _LINK_DO_CONVITE[:] = [gerar]


def _link_de_acesso(pedido: PedidoCompra) -> str | None:
    """D-430-06: o link do convite sai uma vez só, na 1ª leitura depois do `pronto`."""
    from .services import no_schema_da_empresa

    if pedido.empresa is None or pedido.acesso_entregue_em is not None or not _LINK_DO_CONVITE:
        return None
    pedido.acesso_entregue_em = relogio.agora()
    pedido.save(update_fields=["acesso_entregue_em", "atualizado_em"])
    with no_schema_da_empresa(pedido.empresa):
        return _LINK_DO_CONVITE[0](pedido.administrador_email)


def andamento_do_pedido(chave: Any) -> dict[str, Any]:
    """`GET pedidos/{chave}/`. Antes de `confirmado`, só o status. Depois do `pronto`, responde
    por 24 h."""
    from .services import endereco_de_acesso

    with schema_context(get_public_schema_name()), transaction.atomic():
        pedido = _pedido_travado(chave)
        agora = relogio.agora()
        if (
            pedido.status == StatusPedidoCompra.PRONTO
            and pedido.pronto_em
            and agora - pedido.pronto_em > ANDAMENTO_VISIVEL
        ):
            raise PedidoNaoEncontrado
        resposta: dict[str, Any] = {"status": pedido.status}
        if pedido.status == StatusPedidoCompra.AGUARDANDO_CONFIRMACAO:
            return resposta
        if pedido.status == StatusPedidoCompra.FALHOU:
            resposta["mensagem"] = pedido.mensagem_falha or MENSAGEM_FALHA
            return resposta
        resposta["administrador"] = {
            "nome": pedido.administrador_nome.split(" ")[0],
            "email": pedido.administrador_email,
        }
        resposta["empresa"] = {
            "nome_exibicao": pedido.nome_exibicao,
            "endereco": endereco_de_acesso(pedido.subdominio),
        }
        if pedido.status == StatusPedidoCompra.CONFIRMADO:
            resposta["mensagem"] = MENSAGEM_ACIMA_DO_TETO
        passos = []
        empresa = pedido.empresa
        for passo, texto in TEXTOS_DOS_PASSOS:
            if passo == "assinatura":
                texto = _texto_da_assinatura(empresa) if empresa else "Assinatura do plano"
            passos.append({"passo": passo, "texto": texto, "feito_em": pedido.andamento.get(passo)})
        resposta["passos"] = passos
        acessar = None
        if pedido.status == StatusPedidoCompra.PRONTO:
            url = _link_de_acesso(pedido)
            acessar = {"url": url, "uma_vez": True} if url else None
        resposta["acessar"] = acessar
        return resposta


# --- Criação (tarefa) e expiração (diária) ---


def executar_pedido_compra(pedido_id: int) -> str:
    """Chama `criar_empresa` com os dados do pedido (`compra.md`, "O que a criação faz"). Sem
    nova tentativa automática: a falha vira `falhou`, o Sentry e a equipe ficam sabendo."""
    from .services import Administrador, criar_empresa, escolher_forma_pagamento

    with schema_context(get_public_schema_name()), transaction.atomic():
        pedido = PedidoCompra.objects.select_for_update().select_related("plano").get(pk=pedido_id)
        if pedido.status != StatusPedidoCompra.CRIANDO:
            return str(pedido.status)
        situacao = situacao_do_cnpj(pedido.cnpj).situacao
        pedido.situacao_cnpj = situacao
        pedido.save(update_fields=["situacao_cnpj", "atualizado_em"])
    if situacao in (SituacaoCnpj.EM_USO, SituacaoCnpj.FATURA_EM_ATRASO):
        mensagem = MENSAGEM_EM_USO if situacao == SituacaoCnpj.EM_USO else MENSAGEM_FATURA_EM_ATRASO
        return _falhar(pedido_id, mensagem, avisar=False)
    andamento: dict[str, str] = {}
    try:
        empresa = criar_empresa(
            razao_social=pedido.razao_social,
            nome_exibicao=pedido.nome_exibicao,
            cnpj=pedido.cnpj,
            subdominio=pedido.subdominio,
            plano=pedido.plano,
            administrador=Administrador(
                nome=pedido.administrador_nome,
                email=pedido.administrador_email,
                celular=pedido.administrador_celular,
            ),
            ciclo=pedido.ciclo,
            cidade=pedido.cidade,
            uf=pedido.uf,
            origem=Origem.COMPRA,
            aceite_termos_versao=pedido.aceite_termos_versao,
            aceite_termos_em=pedido.aceite_termos_em,
            andamento=andamento,
        )
    except Conflito as erro:
        da_regra = {
            "cnpj_em_uso": MENSAGEM_EM_USO,
            "fatura_anterior_em_atraso": MENSAGEM_FATURA_EM_ATRASO,
        }.get(erro.codigo)
        if da_regra:
            return _falhar(pedido_id, da_regra, avisar=False)
        logger.exception("Compra pública: conflito ao criar a empresa (pedido %s)", pedido_id)
        return _falhar(pedido_id, MENSAGEM_FALHA, avisar=True)
    except Exception:  # o rollback de `criar_empresa` já desfez o schema
        logger.exception("Compra pública: falha ao criar a empresa (pedido %s)", pedido_id)
        return _falhar(pedido_id, MENSAGEM_FALHA, avisar=True)
    with schema_context(get_public_schema_name()), transaction.atomic():
        pedido = PedidoCompra.objects.select_for_update().get(pk=pedido_id)
        pedido.empresa = empresa
        pedido.andamento = andamento
        pedido.pronto_em = relogio.agora()
        transicionar(
            pedido,
            StatusPedidoCompra.PRONTO,
            acao="compra.criar_empresa",
            regra="PLT-16" if pedido.situacao_cnpj == SituacaoCnpj.JA_FOI_CLIENTE else "PLT-01",
            mais_campos=("empresa", "andamento", "pronto_em"),
        )
    if pedido.forma_pagamento:  # PLT-13: só grava a forma; falha aqui não desfaz a empresa
        try:
            escolher_forma_pagamento(empresa, pedido.forma_pagamento)
        except Exception:
            logger.warning("Compra pública: forma de pagamento não gravada (pedido %s)", pedido_id)
    return StatusPedidoCompra.PRONTO


def _falhar(pedido_id: int, mensagem: str, *, avisar: bool) -> str:
    with schema_context(get_public_schema_name()), transaction.atomic():
        pedido = PedidoCompra.objects.select_for_update().get(pk=pedido_id)
        pedido.mensagem_falha = mensagem
        transicionar(
            pedido,
            StatusPedidoCompra.FALHOU,
            acao="compra.falhou",
            regra="PLT-16",
            mais_campos=("mensagem_falha",),
        )
        chave = pedido.chave
    if avisar:
        _avisar_equipe(
            "Compra pública falhou",
            f"O pedido {chave} não criou a empresa. Veja o Sentry e fale com a pessoa por e-mail.",
        )
    return StatusPedidoCompra.FALHOU


def expirar_pedidos_compra() -> dict[str, int]:
    """Diária: pedidos `aguardando_confirmacao` vencidos viram `expirado`; 7 dias depois, os
    dados pessoais do pedido expirado saem (fica plano, ciclo, datas e status para o funil)."""
    agora = relogio.agora()
    expirados = apagados = 0
    with schema_context(get_public_schema_name()):
        vencidos = PedidoCompra.objects.filter(
            status=StatusPedidoCompra.AGUARDANDO_CONFIRMACAO, expira_em__lte=agora
        ).values_list("pk", flat=True)
        for pk in list(vencidos):
            with transaction.atomic():
                pedido = PedidoCompra.objects.select_for_update().get(pk=pk)
                if pedido.status == StatusPedidoCompra.AGUARDANDO_CONFIRMACAO:
                    transicionar(pedido, StatusPedidoCompra.EXPIRADO, acao="compra.expirar")
                    expirados += 1
        vazios = {campo: "" for campo in DADOS_PESSOAIS_DO_PEDIDO}
        apagados = PedidoCompra.objects.filter(
            status=StatusPedidoCompra.EXPIRADO,
            dados_apagados_em__isnull=True,
            expira_em__lte=agora - GUARDA_DO_PEDIDO_EXPIRADO,
        ).update(**vazios, codigo_hash="", ip_hash="", dados_apagados_em=agora, atualizado_em=agora)
    return {"expirados": expirados, "dados_apagados": apagados}
