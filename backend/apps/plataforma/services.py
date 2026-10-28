"""Regras da plataforma (PLT-01, PLT-03, PLT-07, IMP-05). Único lugar que cria empresa, mexe no
uso e abre ou encerra o acesso de suporte.

Os apps da empresa usam só `exigir_limite`, `vagas_no_plano` (importação), `atualizar_uso`,
`registrar_passo_implantacao`, `concluir_implantacao`, `registrar_acesso` e
`registrar_contador` (contrato da plataforma, "Interface interna").
"""

import hmac
import logging
import re
import secrets
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
from functools import partial
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, ProgrammingError, models, transaction
from django.db.models import Q
from django.utils import timezone
from django_tenants.utils import (
    get_public_schema_name,
    schema_context,
    schema_exists,
    tenant_context,
)

from comum import empresa as comum_empresa
from comum import modulos, relogio
from comum.auditoria import (
    ATOR_SISTEMA,
    Ator,
    Categoria,
    TipoAtor,
    ator_atual,
    auditar,
    diferenca,
    registrar_evento,
    retrato,
    usar_ator,
)
from comum.autenticacao import SUPORTE_TERMINOU, AtorSuporte, emitir_token_suporte
from comum.conexao import conexao
from comum.dinheiro import formatar_reais, proporcional
from comum.documentos import UFS, cnpj_valido, so_digitos
from comum.erros import (
    Conflito,
    ErroDeRegra,
    ErroDeValidacao,
    LimiteDoPlano,
    NaoAutenticado,
    NaoEncontrado,
    ParceiroForaDoAr,
)
from comum.estados import transicionar
from comum.eventos import publicar
from comum.models import WebhookRecebido
from comum.tarefas import EmpresaIndisponivel
from integracoes.pagamentos import (
    cobrar_cartao_guardado,
    conta_principal,
    hash_do_token,
    provedor,
    referencia,
)
from integracoes.pagamentos.base import (
    Autorizacao,
    CartaoGuardado,
    CartaoRecusado,
    DadosEmpresa,
    Endereco,
    EventoWebhook,
    Pagador,
    ParceiroIndisponivel,
    ParceiroRecusou,
    PedidoCobranca,
    PedidoRecorrencia,
    StatusDesconhecido,
    aviso_sem_cartao,
)

from .calendario import (
    DIAS_ATE_APAGAR,
    DIAS_DO_AVISO_DO_APAGAMENTO,
    MESES_DE_PAUSA,
    DatasDoCancelamento,
    Periodo,
    datas_do_cancelamento,
    descricao_da_fatura,
    dia_e_mes,
    dia_mes_e_ano,
    periodo_da_pausa,
    proximo_periodo,
    vencimento_da_reativacao,
)
from .models import (
    CAMPOS_DO_ENDERECO,
    DADOS_APAGADOS_DA_EMPRESA,
    DIAS_DE_TESTE,
    DURACOES_DO_SUPORTE,
    TENTATIVAS_DO_CARTAO,
    AcessoSuporte,
    ContaPagamento,
    Dominio,
    Empresa,
    FaturaAssinatura,
    FormaAssinatura,
    FormaPagaFatura,
    FormaPagamentoAssinatura,
    Item,
    MotivoCancelamento,
    MotivoCancelamentoFatura,
    PermissaoSuporte,
    Plano,
    StatusAcessoSuporte,
    StatusContaPagamento,
    StatusFatura,
    StatusFormaPagamento,
    TipoFatura,
    UsoEmpresa,
    validar_nome_sem_quebra,
)

logger = logging.getLogger(__name__)

SUBDOMINIOS_RESERVADOS = frozenset(
    {"admin", "www", "api", "app", "suporte", "status", "public", "information-schema"}
)
# Schemas do próprio Postgres (`pg_catalog`, `pg_toast`...): o subdomínio `pg-*` viraria um deles.
_PREFIXO_DO_POSTGRES = "pg-"
RESERVADO = "Este endereço é reservado. Escolha outro."
_SUBDOMINIO = re.compile(r"^[a-z0-9-]{3,30}$")

# Passos do assistente de implantação, na ordem do contrato (Plat-Empresa-Detalhe).
PASSOS_IMPLANTACAO: list[tuple[str, str]] = [
    ("conta", "Conta e acesso"),
    ("marca", "Empresa e marca"),
    ("filial", "Primeira filial"),
    ("ramo", "O que a empresa faz"),
    ("precos", "Tabela de preços"),
    ("contrato", "Contrato"),
    ("recebimentos", "Recebimentos"),
    ("importar", "Importar dados"),
    ("equipe", "Equipe"),
    ("primeira_locacao", "1ª locação"),
]
# Etapa do funil (IMP-05) → passo que a conclui. "Dados" é o passo de importar.
FUNIL: list[tuple[str, str]] = [
    ("conta", "conta"),
    ("marca", "marca"),
    ("filial", "filial"),
    ("precos", "precos"),
    ("dados", "importar"),
    ("primeira_locacao", "primeira_locacao"),
]

ACESSO_A_CADA = timedelta(minutes=5)

# Frase da recusa por item (PLT-03): "Seu plano permite até 3 filiais. Para abrir outra, ...".
_FRASE_DO_LIMITE = {
    Item.VEICULOS: ("veículos", "cadastrar outro"),
    Item.FILIAIS: ("filiais", "abrir outra"),
    Item.USUARIOS: ("usuários", "convidar outro"),
}


@dataclass(frozen=True)
class Administrador:
    nome: str
    email: str
    celular: str = ""


# --- Criação da empresa (PLT-01) ---


def schema_do_subdominio(subdominio: str) -> str:
    return subdominio.replace("-", "_")


def endereco_de_acesso(subdominio: str) -> str:
    return f"{subdominio}.{settings.DOMINIO_BASE}"


def _validar(subdominio: str, cnpj: str, administrador: Administrador) -> dict[str, list[str]]:
    erros: dict[str, list[str]] = {}
    if not _SUBDOMINIO.match(subdominio):
        erros["subdominio"] = ["Use de 3 a 30 letras minúsculas, números ou hífen."]
    elif subdominio.startswith(_PREFIXO_DO_POSTGRES) or subdominio in (
        SUBDOMINIOS_RESERVADOS | {settings.SUBDOMINIO_PLATAFORMA}
    ):
        erros["subdominio"] = [RESERVADO]
    if not cnpj_valido(cnpj):
        erros["cnpj"] = ["CNPJ inválido"]
    if not administrador.nome.strip():
        erros["administrador.nome"] = ["Informe o nome."]
    if "@" not in administrador.email:
        erros["administrador.email"] = ["Informe um e-mail válido."]
    return erros


def validar_criacao(subdominio: str, cnpj: str, administrador: Administrador) -> None:
    """400 `validacao` para formato; 409 `subdominio_em_uso` ou `cnpj_em_uso` (PLT-01).

    Subdomínio cujo schema já existe no Postgres sem ser de empresa (`information_schema`, de
    extensão, de ferramenta) é recusado como reservado (P-04 da T-057).
    """
    erros = _validar(subdominio, cnpj, administrador)
    if erros:
        raise ErroDeValidacao(erros)
    with schema_context(get_public_schema_name()):
        schema = schema_do_subdominio(subdominio)
        if (
            Empresa.objects.filter(subdominio=subdominio).exists()
            or Empresa.objects.filter(schema_name=schema).exists()
        ):
            raise Conflito("subdominio_em_uso", "Este endereço já está em uso. Escolha outro.")
        if schema_exists(schema):
            raise ErroDeValidacao({"subdominio": [RESERVADO]})
        if Empresa.objects.filter(cnpj=so_digitos(cnpj)).exists():
            raise Conflito("cnpj_em_uso", "Já existe uma empresa com este CNPJ.")


def criar_empresa(
    *,
    razao_social: str,
    nome_exibicao: str,
    cnpj: str,
    subdominio: str,
    plano: Plano,
    administrador: Administrador,
    ciclo: str = Empresa.Ciclo.MENSAL,
    cidade: str = "",
    uf: str = "",
) -> Empresa:
    """Empresa em teste, domínio, schema, uso, a 1ª fatura (PLT-01) e administrador
    convidado, numa transação.

    O administrador nasce `convite_pendente` no schema da empresa (`contas`, pelo evento
    `plataforma.empresa_criada`); o e-mail do convite sai só depois do commit. Se algo falha,
    o schema volta junto (DDL do PostgreSQL é transacional).
    """
    subdominio = subdominio.strip()
    cnpj = so_digitos(cnpj)
    try:
        validar_nome_sem_quebra(nome_exibicao.strip())
    except DjangoValidationError as erro:
        raise ErroDeValidacao({"nome_exibicao": list(erro.messages)}) from erro
    with schema_context(get_public_schema_name()), transaction.atomic():
        validar_criacao(subdominio, cnpj, administrador)
        hoje = relogio.hoje()
        empresa = Empresa(
            schema_name=schema_do_subdominio(subdominio),
            subdominio=subdominio,
            razao_social=razao_social.strip(),
            nome_exibicao=nome_exibicao.strip(),
            cnpj=cnpj,
            cidade=cidade.strip(),
            uf=uf.strip().upper(),
            responsavel_nome=administrador.nome.strip(),
            responsavel_email=administrador.email.strip().lower(),
            responsavel_telefone=so_digitos(administrador.celular),
            email_cobranca=administrador.email.strip().lower(),
            plano=plano,
            ciclo=ciclo,
            preco_contratado_centavos=preco_no_ciclo(plano, ciclo),
            status=Empresa.Status.EM_TESTE,
            teste_inicio=hoje,
            teste_fim=hoje + timedelta(days=DIAS_DE_TESTE),
            # PLT-01: o dia da 1ª fatura (dia seguinte ao fim do teste).
            dia_vencimento=(hoje + timedelta(days=DIAS_DE_TESTE + 1)).day,
            etapa_implantacao=Empresa.EtapaImplantacao.CONTA,
            etapa_implantacao_desde=relogio.agora(),
        )
        # O schema é criado aqui, sem `check_if_exists`: um schema que já existe dá erro e desfaz
        # tudo, em vez de ser reaproveitado sem tabelas (P-04 da T-057).
        empresa.auto_create_schema = False
        try:
            with transaction.atomic():
                empresa.save()
                empresa.create_schema(check_if_exists=False)  # e aplica as migrações
        except IntegrityError as erro:  # outra criação ganhou a corrida
            raise Conflito("subdominio_em_uso", "Este endereço já está em uso.") from erro
        except ProgrammingError as erro:  # o schema já existe no Postgres
            raise ErroDeValidacao({"subdominio": [RESERVADO]}) from erro
        Dominio.objects.create(
            domain=endereco_de_acesso(subdominio), tenant=empresa, is_primary=True
        )
        UsoEmpresa.objects.create(empresa=empresa)
        FormaPagamentoAssinatura.objects.create(empresa=empresa)
        registrar_evento(
            "empresa.criar",
            Categoria.CONFIGURACOES,
            objeto=empresa,
            depois=retrato(empresa),
            regra="PLT-01",
        )
        criar_primeira_fatura(empresa)
        with no_schema_da_empresa(empresa, com_tenant=True):
            publicar(
                "plataforma.empresa_criada",
                empresa_id=empresa.pk,
                administrador=asdict(administrador),
            )
    return empresa


# --- Uso do plano (PLT-03) ---


def _empresa(empresa: Empresa | None) -> Empresa:
    if empresa is not None:
        return empresa
    atual = getattr(conexao(), "tenant", None)
    if not isinstance(atual, Empresa) or atual.schema_name == get_public_schema_name():
        raise RuntimeError("Sem empresa na conexão.")
    return atual


def _uso_travado(empresa: Empresa) -> UsoEmpresa:
    """`SELECT ... FOR UPDATE` no resumo: duas criações simultâneas esperam uma pela outra."""
    UsoEmpresa.objects.get_or_create(empresa=empresa)
    return UsoEmpresa.objects.select_for_update().get(empresa=empresa)


def _plano_atual(empresa: Empresa) -> Plano | None:
    return Plano.objects.filter(pk=empresa.plano_id).first() if empresa.plano_id else None


def exigir_limite(item: str, empresa: Empresa | None = None) -> None:
    """Recusa o cadastro novo do `item` quando o uso chegou ao limite (422 `PLT-03`).

    Chame dentro da transação do cadastro e, na mesma transação, `atualizar_uso(item, 1)`:
    a trava no `UsoEmpresa` dura até o commit, e a outra criação vê o uso já somado.
    """
    if item not in Item.values:
        raise ValueError(f"Item sem limite no plano: {item}")
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("exigir_limite precisa rodar dentro da transação do cadastro.")
    empresa = _empresa(empresa)
    uso = _uso_travado(empresa)
    plano = _plano_atual(empresa)
    limite = plano.limite(item) if plano else None
    usado = int(getattr(uso, item))
    if limite is not None and usado >= limite:
        nome, acao = _FRASE_DO_LIMITE[Item(item)]
        raise LimiteDoPlano(
            f"Seu plano permite até {limite} {nome}. Para {acao}, mude de plano.",
            {"item": item, "usado": usado, "limite": limite},
        )


@dataclass(frozen=True)
class Vagas:
    """Quantos `item` ainda cabem no plano; `cabem` e `limite` nulos quando não há limite."""

    cabem: int | None
    limite: int | None
    plano: str


def vagas_no_plano(item: str, empresa: Empresa | None = None) -> Vagas:
    """IMP-03: trava o `UsoEmpresa` (`SELECT ... FOR UPDATE`, até o commit) e devolve quantos
    `item` cabem. Para gravar vários cadastros de uma vez sem passar do limite."""
    if item not in Item.values:
        raise ValueError(f"Item sem limite no plano: {item}")
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("vagas_no_plano precisa rodar dentro da transação dos cadastros.")
    empresa = _empresa(empresa)
    uso = _uso_travado(empresa)
    plano = _plano_atual(empresa)
    limite = plano.limite(item) if plano else None
    cabem = None if limite is None else max(0, limite - int(getattr(uso, item)))
    return Vagas(cabem=cabem, limite=limite, plano=plano.nome if plano else "")


def chegou_a_90(usado: int, limite: int | None) -> bool:
    return limite is not None and usado * 10 >= limite * 9


def atualizar_uso(item: str, delta: int, empresa: Empresa | None = None) -> None:
    """Soma `delta` ao uso do item. Chamado ao criar (+1), desativar (-1) ou reativar (+1).

    Ao chegar a 90% do limite, agenda o aviso aos administradores uma vez por item e por mês.
    """
    if item not in Item.values:
        raise ValueError(f"Item sem limite no plano: {item}")
    empresa = _empresa(empresa)
    with transaction.atomic():
        uso = _uso_travado(empresa)
        novo = max(0, int(getattr(uso, item)) + delta)
        setattr(uso, item, novo)
        campos = [item, "atualizado_em"]
        plano = _plano_atual(empresa)
        mes = relogio.hoje().strftime("%Y-%m")
        if (
            delta > 0
            and chegou_a_90(novo, plano.limite(item) if plano else None)
            and uso.aviso_90_enviado.get(item) != mes
        ):
            uso.aviso_90_enviado = {**uso.aviso_90_enviado, item: mes}
            campos.append("aviso_90_enviado")
            _agendar_aviso_90(empresa.schema_name, item)
        uso.save(update_fields=campos)


def _agendar_aviso_90(schema_name: str, item: str) -> None:
    from .tasks import plataforma_avisar_limite_90

    transaction.on_commit(lambda: plataforma_avisar_limite_90.delay(schema_name, item))


# Contagem real por item, registrada pelos apps donos no `ready()` (contas, filiais, veiculos).
# A tarefa noturna corrige o resumo com ela, sem `plataforma` importar os apps de baixo.
_contadores: dict[str, Callable[[], int]] = {}


def registrar_contador(item: str, contar: Callable[[], int]) -> None:
    if item not in Item.values:
        raise ValueError(f"Item sem limite no plano: {item}")
    _contadores[item] = contar


def recalcular_uso(empresa: Empresa) -> dict[str, int]:
    """Conta de verdade no schema da empresa e corrige o resumo. Item sem contador fica."""
    with no_schema_da_empresa(empresa, com_tenant=True):
        valores = {item: contar() for item, contar in _contadores.items()}
    with schema_context(get_public_schema_name()), transaction.atomic():
        uso = _uso_travado(empresa)
        for item, valor in valores.items():
            setattr(uso, item, valor)
        uso.save(update_fields=[*valores, "atualizado_em"])
    return valores


# --- Implantação (IMP-05) e acesso ---


def etapa_do_funil(passos_concluidos: dict[str, Any]) -> str:
    for etapa, passo in FUNIL:
        if passo not in passos_concluidos:
            return etapa
    return Empresa.EtapaImplantacao.CONCLUIDA


def registrar_passo_implantacao(passo: str, empresa: Empresa | None = None) -> bool:
    """Marca o passo como concluído hoje e move a etapa do funil quando ela muda.

    Devolve se o passo é novo (False quando já estava concluído).
    """
    if passo not in dict(PASSOS_IMPLANTACAO):
        raise ValueError(f"Passo desconhecido: {passo}")
    empresa = _empresa(empresa)
    with schema_context(get_public_schema_name()), transaction.atomic():
        uso = _uso_travado(empresa)
        novo = passo not in uso.passos_implantacao
        if novo:
            uso.passos_implantacao = {
                **uso.passos_implantacao,
                passo: relogio.hoje().isoformat(),
            }
            uso.save(update_fields=["passos_implantacao", "atualizado_em"])
        etapa = etapa_do_funil(uso.passos_implantacao)
        atual = Empresa.objects.select_for_update().get(pk=empresa.pk)
        if atual.etapa_implantacao != etapa:
            atual.etapa_implantacao = etapa
            atual.etapa_implantacao_desde = relogio.agora()
            atual.save(update_fields=["etapa_implantacao", "etapa_implantacao_desde"])
    return novo


def concluir_implantacao(objeto: models.Model, empresa: Empresa | None = None) -> bool:
    """IMP-01: a 1ª locação (ou venda) conclui a implantação, uma vez só e com auditoria.

    Chamada dentro da transação que confirma `objeto`: se ela desfaz, o passo também sai. A
    leitura sem trava evita disputar a linha de `UsoEmpresa` a cada locação depois da primeira.
    """
    empresa = _empresa(empresa)
    with schema_context(get_public_schema_name()):
        feito = UsoEmpresa.objects.filter(
            empresa=empresa, passos_implantacao__has_key="primeira_locacao"
        ).exists()
    if feito or not registrar_passo_implantacao("primeira_locacao", empresa):
        return False
    registrar_evento("implantacao.concluir", Categoria.CONFIGURACOES, objeto=objeto, regra="IMP-01")
    return True


def registrar_acesso(empresa: Empresa | None = None) -> None:
    """`ultimo_acesso_em`, no máximo uma escrita a cada 5 minutos por empresa."""
    empresa = _empresa(empresa)
    agora = relogio.agora()
    UsoEmpresa.objects.filter(empresa=empresa).filter(
        Q(ultimo_acesso_em__isnull=True) | Q(ultimo_acesso_em__lte=agora - ACESSO_A_CADA)
    ).update(ultimo_acesso_em=agora)


# --- Acesso de suporte (PLT-07, AUD-03; ADR 0013, item 2) ---
#
# `AcessoSuporte` e o usuário da equipe ficam no `public`. Do host da empresa, o `search_path`
# acharia primeiro a tabela de usuários da empresa: por isso toda leitura e escrita do acesso
# roda em `schema_context(public)`. Cada fato vai para as duas auditorias (PLT-07).

SUPORTE_BLOQUEADO = ("PLT-07", "O administrador da empresa bloqueou o acesso do suporte")
# T-199, M-02: o pedido de dados da cancelada é atendido pela equipe (AUD-08), sem o suporte.
SUPORTE_NA_CANCELADA = (
    "empresa_cancelada",
    "Esta empresa cancelou a assinatura. O suporte não entra.",
)


def no_publico() -> Any:
    return schema_context(get_public_schema_name())


class EmpresaApagada(EmpresaIndisponivel):
    """O schema da empresa saiu no 90º dia (AUD-08): nada entra nele."""


def no_schema_da_empresa(empresa: Empresa, *, com_tenant: bool = False) -> Any:
    """Entrada única no schema da empresa (T-199, M-02). Depois do `DROP` do 90º dia, o
    `search_path` "<schema>, public" cairia nas tabelas da plataforma sem erro (as de
    `contas` e `auditoria` existem nos dois): a empresa apagada é recusada antes.
    `com_tenant` entra com a empresa real, para quem precisa do id dela (a cifra)."""
    if empresa.apagada_em is not None:
        raise EmpresaApagada(f"Empresa {empresa.pk} foi apagada (AUD-08).")
    return tenant_context(empresa) if com_tenant else schema_context(empresa.schema_name)


def _ator_do_suporte(acesso: AcessoSuporte) -> Ator:
    """O suporte como ator na auditoria da empresa, com o acesso que justifica (AUD-03)."""
    atual = ator_atual()
    return Ator(
        tipo=TipoAtor.SUPORTE,
        nome=acesso.usuario.nome,
        ip=atual.ip,
        aparelho=atual.aparelho,
        acesso_suporte_id=acesso.pk,
    )


def _auditar_na_empresa(
    acesso: AcessoSuporte, acao: str, *, motivo: str, pelo_suporte: bool
) -> None:
    """O mesmo fato na auditoria da empresa (AUD-03: com destaque, pelo ator `suporte`)."""
    depois = {"status": acesso.status, "permissao": acesso.permissao, "fim": acesso.fim}
    ator = _ator_do_suporte(acesso) if pelo_suporte else ator_atual()
    with no_schema_da_empresa(acesso.empresa), usar_ator(ator):
        registrar_evento(
            acao, Categoria.SUPORTE, objeto=acesso, depois=depois, motivo=motivo, regra="PLT-07"
        )


def abrir_acesso_suporte(
    empresa: Empresa, usuario: Any, *, motivo: str, duracao_minutos: int, permissao: str
) -> tuple[AcessoSuporte, str]:
    """Entrar como suporte (PLT-07). Devolve o acesso e o token, que vence no `fim`.

    Empresa com o suporte bloqueado: 422 `PLT-07`. O administrador recebe e-mail na hora.
    """
    erros: dict[str, list[str]] = {}
    if not motivo.strip():
        erros["motivo"] = ["Informe o motivo, de preferência o chamado."]
    if duracao_minutos not in DURACOES_DO_SUPORTE:
        erros["duracao_minutos"] = ["Use 15, 30 ou 60 minutos."]
    if permissao not in PermissaoSuporte.values:
        erros["permissao"] = ["Use ver ou ver_editar."]
    if erros:
        raise ErroDeValidacao(erros)
    with no_publico(), transaction.atomic():
        empresa = Empresa.objects.select_for_update().get(pk=empresa.pk)
        if empresa.status == Empresa.Status.CANCELADA:
            raise Conflito(*SUPORTE_NA_CANCELADA)
        if empresa.suporte_bloqueado:
            raise ErroDeRegra(*SUPORTE_BLOQUEADO)
        agora = relogio.agora()
        acesso = AcessoSuporte.objects.create(
            usuario=usuario,
            empresa=empresa,
            motivo=motivo.strip(),
            permissao=permissao,
            inicio=agora,
            fim=agora + timedelta(minutes=duracao_minutos),
        )
        acesso.refresh_from_db(fields=["inicio", "fim"])  # em UTC, como o resto da API
        registrar_evento(
            "suporte.entrar",
            Categoria.SUPORTE,
            objeto=acesso,
            depois=retrato(acesso),
            motivo=acesso.motivo,
            regra="PLT-07",
        )
        _auditar_na_empresa(acesso, "suporte.entrar", motivo=acesso.motivo, pelo_suporte=True)
        token = emitir_token_suporte(
            acesso_suporte_id=acesso.pk,
            permissao=permissao,
            fim=acesso.fim,
            schema=empresa.schema_name,
            empresa_id=empresa.pk,
        )
        from .tasks import plataforma_avisar_entrada_do_suporte

        schema, acesso_id = empresa.schema_name, acesso.pk
        transaction.on_commit(lambda: plataforma_avisar_entrada_do_suporte.delay(schema, acesso_id))
    return acesso, str(token)


def url_de_entrada_do_suporte(acesso: AcessoSuporte, token: str) -> str:
    """O token no fragmento: não vai ao servidor nem ao proxy (contrato da plataforma)."""
    with no_publico():
        dominio = Dominio.objects.get(tenant_id=acesso.empresa_id, is_primary=True).domain
    return f"https://{dominio}/suporte/entrar#{token}"


def conferir_acesso_suporte(acesso_suporte_id: int, empresa_id: int) -> AtorSuporte:
    """A cada requisição com token de suporte (registrada em `comum.autenticacao`)."""
    with no_publico():
        acesso = (
            AcessoSuporte.objects.select_related("usuario", "empresa")
            .filter(pk=acesso_suporte_id, empresa_id=empresa_id)
            .first()
        )
        if (
            acesso is None
            or acesso.status != StatusAcessoSuporte.ATIVO
            or acesso.fim <= relogio.agora()
            or acesso.empresa.suporte_bloqueado
        ):
            raise NaoAutenticado(*SUPORTE_TERMINOU)
        return AtorSuporte(
            acesso_suporte_id=acesso.pk,
            nome=acesso.usuario.nome,
            permissao=acesso.permissao,
            fim=acesso.fim,
            motivo=acesso.motivo,
        )


def _terminar(
    acesso: AcessoSuporte, status: str, acao: str, *, motivo: str, pelo_suporte: bool
) -> AcessoSuporte:
    with no_publico(), transaction.atomic():
        acesso = (
            AcessoSuporte.objects.select_for_update()
            .select_related("usuario", "empresa")
            .get(pk=acesso.pk)
        )
        if acesso.status != StatusAcessoSuporte.ATIVO:
            return acesso
        acesso.encerrado_em = relogio.agora()
        acesso.save(update_fields=["encerrado_em", "atualizado_em"])
        ator = _ator_do_suporte(acesso) if pelo_suporte else ator_atual()
        with usar_ator(ator):
            transicionar(acesso, status, acao=acao, motivo=motivo, regra="PLT-07")
        _auditar_na_empresa(acesso, acao, motivo=motivo, pelo_suporte=pelo_suporte)
    return acesso


def sair_do_suporte(acesso_suporte_id: int) -> AcessoSuporte:
    """`POST /api/auth/suporte/sair/`: o acesso vai para `encerrado`."""
    with no_publico():
        acesso = AcessoSuporte.objects.get(pk=acesso_suporte_id)
    return _terminar(
        acesso,
        StatusAcessoSuporte.ENCERRADO,
        "suporte.sair",
        motivo="O suporte saiu",
        pelo_suporte=True,
    )


def revogar_acesso_suporte(acesso: AcessoSuporte, motivo: str = "") -> AcessoSuporte:
    """O administrador da empresa revoga um acesso (status `revogado`, na hora)."""
    return _terminar(
        acesso,
        StatusAcessoSuporte.REVOGADO,
        "suporte.revogar",
        motivo=motivo or "Revogado pelo administrador",
        pelo_suporte=False,
    )


def encerrar_acessos_vencidos() -> int:
    """AUT-15: acessos `ativo` com o `fim` passado vão para `encerrado`. Idempotente."""
    with no_publico():
        vencidos = list(
            AcessoSuporte.objects.filter(
                status=StatusAcessoSuporte.ATIVO, fim__lte=relogio.agora()
            ).values_list("pk", flat=True)
        )
        acessos = list(AcessoSuporte.objects.filter(pk__in=vencidos))
    for acesso in acessos:
        _terminar(
            acesso,
            StatusAcessoSuporte.ENCERRADO,
            "suporte.encerrar",
            motivo="O prazo do acesso acabou",
            pelo_suporte=False,
        )
    return len(acessos)


def definir_bloqueio_do_suporte(empresa: Empresa, *, bloquear: bool, motivo: str = "") -> bool:
    """O administrador bloqueia ou libera o suporte (PLT-07). Bloquear revoga na hora os
    acessos ativos."""
    acao = "suporte.bloquear" if bloquear else "suporte.liberar"
    with no_publico(), transaction.atomic():
        empresa = Empresa.objects.select_for_update().get(pk=empresa.pk)
        antes = empresa.suporte_bloqueado
        if antes != bloquear:
            empresa.suporte_bloqueado = bloquear
            empresa.save(update_fields=["suporte_bloqueado", "atualizado_em"])
            for entrar in (no_publico, lambda: no_schema_da_empresa(empresa)):
                with entrar():
                    registrar_evento(
                        acao,
                        Categoria.SUPORTE,
                        objeto=empresa,
                        antes={"suporte_bloqueado": antes},
                        depois={"suporte_bloqueado": bloquear},
                        motivo=motivo,
                        regra="PLT-07",
                    )
        ativos = list(
            AcessoSuporte.objects.filter(empresa=empresa, status=StatusAcessoSuporte.ATIVO)
        )
        if bloquear:
            for acesso in ativos:
                revogar_acesso_suporte(acesso, motivo or "Suporte bloqueado pelo administrador")
    return bloquear


# --- Recebimentos: subconta no parceiro de pagamentos (passo 10, ADR 0007, T-029) ---

PARCEIRO_FORA_DO_AR = (
    "parceiro_indisponivel",
    "Não conseguimos falar com o parceiro de pagamento. Tente de novo em alguns minutos.",
)


def url_do_webhook_de_pagamentos() -> str:
    """No host da plataforma (contrato de financeiro, "Webhooks"). `GIRO_URL_WEBHOOK_PAGAMENTOS`
    troca o endereço no desenvolvimento com o sandbox (um túnel HTTPS até a máquina)."""
    return getattr(settings, "GIRO_URL_WEBHOOK_PAGAMENTOS", "") or (
        f"https://{settings.SUBDOMINIO_PLATAFORMA}.{settings.DOMINIO_BASE}"
        "/api/webhooks/pagamentos/asaas/"
    )


def conectar_recebimentos(
    *,
    nome: str,
    documento: str,
    email: str,
    celular: str,
    logradouro: str,
    numero: str,
    bairro: str,
    cep: str,
    faturamento_mensal_centavos: int,
    complemento: str = "",
    tipo_empresa: str = "",
) -> ContaPagamento:
    """CA-029-01: abre a subconta da empresa da conexão no parceiro e guarda a chave cifrada
    (S-05) e o hash do token do webhook (S-14). A subconta nasce `pendente` até o parceiro
    aprovar; o passo `recebimentos` da implantação fica feito. Recusa do parceiro: nada é
    gravado, e o motivo vai para a tela (CA-029-02)."""
    empresa = _empresa(None)
    if ContaPagamento.objects.filter(empresa=empresa).exists():
        raise Conflito("recebimentos_conectados", "Os recebimentos já estão conectados.")
    token = secrets.token_urlsafe(32)
    try:
        subconta = provedor().criar_subconta(
            DadosEmpresa(
                nome=nome,
                documento=so_digitos(documento),
                email=email,
                celular=so_digitos(celular),
                logradouro=logradouro,
                numero=numero,
                bairro=bairro,
                cep=so_digitos(cep),
                faturamento_mensal_centavos=faturamento_mensal_centavos,
                webhook_url=url_do_webhook_de_pagamentos(),
                webhook_token=token,
                complemento=complemento,
                tipo_empresa=tipo_empresa,
            )
        )
    except ParceiroRecusou as erro:
        raise ErroDeRegra("parceiro_recusou", erro.mensagem) from erro
    except ParceiroIndisponivel as erro:
        raise ParceiroForaDoAr(*PARCEIRO_FORA_DO_AR) from erro
    conta = ContaPagamento(
        empresa=empresa,
        provedor=getattr(settings, "GIRO_PROVEDOR_PAGAMENTOS", "asaas"),
        conta_externa_id=subconta.conta_externa_id,
        carteira_id=subconta.carteira_id,
        webhook_token_hash=hash_do_token(token),
    )
    conta.definir_chave_api_cifrada(subconta.chave_api)
    with transaction.atomic():
        with auditar(conta, "conta_pagamento.criar", Categoria.CONFIGURACOES, regra="FIN-04"):
            conta.save()
        registrar_passo_implantacao("recebimentos", empresa)
    return conta


def atualizar_recebimentos() -> ContaPagamento | None:
    """Consulta no parceiro se a subconta `pendente` da empresa da conexão foi aprovada ou
    recusada. Só com a aprovação o Pix e o boleto ficam ligados (CA-029-02)."""
    conta: ContaPagamento | None = ContaPagamento.objects.filter(empresa=_empresa(None)).first()
    if conta is None or conta.status != StatusContaPagamento.PENDENTE:
        return conta
    situacao = provedor().consultar_subconta(referencia(conta))
    if situacao in (StatusContaPagamento.APROVADA, StatusContaPagamento.RECUSADA):
        transicionar(conta, situacao, acao=f"conta_pagamento.{situacao}", regra="FIN-04")
    return conta


# --- Faturas da assinatura e conta principal (PLT-01, PLT-13, PLT-14, PLT-15; T-184, ADR 0023) ---


def preco_no_ciclo(plano: Plano, ciclo: str) -> int:
    """Preço de tabela do plano no ciclo (PLT-05): é o que vira o preço contratado."""
    if ciclo == Empresa.Ciclo.ANUAL:
        return plano.preco_anual_centavos
    return int(plano.preco_mensal_centavos)


def criar_fatura(
    empresa: Empresa,
    *,
    tipo: str,
    vencimento: date,
    periodo: Periodo,
    plano: Plano,
    ciclo: str,
    valor_centavos: int,
    regra: str = "PLT-14",
) -> FaturaAssinatura:
    """Única porta de entrada das faturas, no public, com o código `FAT-NNNN` da empresa."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        fatura = FaturaAssinatura(
            empresa=empresa,
            tipo=tipo,
            competencia=periodo.competencia,
            periodo_inicio=periodo.inicio,
            periodo_fim=periodo.fim,
            plano=plano,
            ciclo=ciclo,
            valor_centavos=valor_centavos,
            vencimento=vencimento,
        )
        with auditar(fatura, "fatura_assinatura.criar", Categoria.FINANCEIRO, regra=regra):
            fatura.save()
    return fatura


def criar_primeira_fatura(empresa: Empresa) -> FaturaAssinatura:
    """PLT-01: a 1ª fatura nasce com a empresa, `aberta`, vencendo no dia seguinte ao fim do
    teste, pelo plano e pelo preço contratados (Moto Rápida: FAT-0001, 22 out, 44900)."""
    if empresa.plano is None or empresa.primeira_cobranca is None or not empresa.dia_vencimento:
        raise ValueError("Empresa sem plano, teste ou dia de vencimento.")
    vencimento = empresa.primeira_cobranca
    return criar_fatura(
        empresa,
        tipo=TipoFatura.MENSALIDADE,
        vencimento=vencimento,
        periodo=proximo_periodo(empresa.dia_vencimento, empresa.ciclo, vencimento),
        plano=empresa.plano,
        ciclo=empresa.ciclo,
        valor_centavos=int(empresa.preco_contratado_centavos),
        regra="PLT-01",
    )


def nfse_ligada() -> bool:
    """`GIRO_NFSE_ASSINATURA_ATIVA`: desligada até o cadastro municipal do Giro (T-197)."""
    return bool(getattr(settings, "GIRO_NFSE_ASSINATURA_ATIVA", False))


def _agendar_notas_pendentes(empresa_id: int) -> None:
    if not nfse_ligada():
        return
    from .tasks import plataforma_pedir_notas_pendentes

    transaction.on_commit(lambda: plataforma_pedir_notas_pendentes.delay(empresa_id))


def copiar_endereco_da_matriz(
    endereco: Mapping[str, Any], filial_id: int | None = None, empresa: Empresa | None = None
) -> bool:
    """PLT-15 (T-213): a filial que nasce matriz dá o endereço da nota da assinatura, uma vez só.
    Chamado por `filiais.services.criar_filial` na mesma transação. Se a empresa já tem endereço
    (de uma matriz anterior ou dos dados fiscais), não faz nada e devolve `False`. Depois, a nota
    e a filial mudam cada uma por conta própria."""
    empresa = _empresa(empresa)
    with schema_context(get_public_schema_name()), transaction.atomic():
        atual = Empresa.objects.select_for_update().get(pk=empresa.pk)
        if atual.endereco_cep:
            return False
        motivo = f"Endereço da filial matriz {filial_id}" if filial_id else "Endereço da matriz"
        antes = retrato(atual)
        for campo in CAMPOS_DO_ENDERECO:
            setattr(atual, f"endereco_{campo}", endereco.get(campo) or "")
        atual.save(update_fields=[f"endereco_{c}" for c in CAMPOS_DO_ENDERECO])
        mudou_antes, mudou_depois = diferenca(antes, retrato(atual))
        # Nos dois lugares (T-236): o endereço completo só no schema da empresa.
        with usar_ator(ATOR_SISTEMA):
            _registrar_nos_dois(
                atual,
                "empresa.dados_fiscais",
                antes=mudou_antes,
                depois=mudou_depois,
                categoria_publica=Categoria.CONFIGURACOES,
                motivo=motivo,
                regra="PLT-15",
            )
        _agendar_notas_pendentes(atual.pk)
    for campo in CAMPOS_DO_ENDERECO:
        setattr(empresa, f"endereco_{campo}", getattr(atual, f"endereco_{campo}"))
    return True


def pagador_da_empresa(empresa: Empresa, cliente_externo_id: str = "") -> Pagador:
    """A empresa como cliente da conta principal: razão social, CNPJ, endereço da nota e o
    e-mail de cobrança (PLT-15)."""
    endereco = empresa.endereco
    return Pagador(
        nome=empresa.razao_social or empresa.nome_exibicao,
        documento=empresa.cnpj or "",
        celular=empresa.responsavel_telefone,
        email=empresa.email_cobranca or empresa.responsavel_email,
        endereco=(
            Endereco(
                cep=endereco["cep"] or "",
                logradouro=endereco["logradouro"] or "",
                numero=endereco["numero"] or "",
                bairro=endereco["bairro"] or "",
                cidade=endereco["cidade"] or "",
                uf=endereco["uf"] or "",
                complemento=endereco["complemento"] or "",
            )
            if endereco
            else None
        ),
        id_externo=cliente_externo_id,
    )


def forma_pagamento_da_empresa(empresa: Empresa) -> FormaPagamentoAssinatura:
    """A linha da forma de pagamento, criada vazia na primeira vez (`forma` nula)."""
    with schema_context(get_public_schema_name()):
        forma, _ = FormaPagamentoAssinatura.objects.get_or_create(empresa=empresa)
    return forma


def atualizar_pagador(empresa: Empresa) -> str:
    """Cria ou atualiza o pagador da empresa na conta principal (antes da cobrança e quando os
    dados fiscais mudam) e guarda o id dele. Parceiro fora do ar: 503; recusou: 422."""
    forma = forma_pagamento_da_empresa(empresa)
    try:
        cliente_id = provedor().criar_ou_atualizar_pagador(
            conta_principal(), pagador_da_empresa(empresa, forma.cliente_externo_id)
        )
    except ParceiroRecusou as erro:
        raise ErroDeRegra("parceiro_recusou", erro.mensagem) from erro
    except ParceiroIndisponivel as erro:
        raise ParceiroForaDoAr(*PARCEIRO_FORA_DO_AR) from erro
    if cliente_id != forma.cliente_externo_id:
        with schema_context(get_public_schema_name()), transaction.atomic():
            forma = FormaPagamentoAssinatura.objects.select_for_update().get(pk=forma.pk)
            forma.cliente_externo_id = cliente_id
            forma.save(update_fields=["cliente_externo_id", "atualizado_em"])
    return cliente_id


def gravar_tomador(fatura: FaturaAssinatura) -> bool:
    """PLT-14 (T-236, CA-ASS-59): a fatura guarda para quem a nota saiu, como estava na
    `Empresa` naquele momento, e isso não muda depois. Grava uma vez só (devolve `False` se já
    estava gravado). Único lugar que escreve nos `tomador_*`; sem evento próprio de auditoria."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        travada = (
            FaturaAssinatura.objects.select_for_update(of=("self",))
            .select_related("empresa")
            .get(pk=fatura.pk)
        )
        if travada.tomador_gravado_em is not None:
            return False
        empresa = travada.empresa
        travada.tomador_razao_social = empresa.razao_social
        travada.tomador_cnpj = empresa.cnpj or ""
        travada.tomador_endereco = empresa.endereco
        travada.tomador_gravado_em = relogio.agora()
        campos = ["tomador_razao_social", "tomador_cnpj", "tomador_endereco", "tomador_gravado_em"]
        travada.save(update_fields=[*campos, "atualizado_em"])
    for campo in campos:
        setattr(fatura, campo, getattr(travada, campo))
    return True


# Webhook da conta principal (assinatura.md, "Faturas, cobrança e régua"; S-14)


def token_da_conta_principal(token: str) -> bool:
    """O token do aviso confere com o hash do webhook da conta principal, guardado só em
    configuração (`GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH`). Sem hash configurado, nunca confere."""
    esperado = getattr(settings, "GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH", "") or ""
    return bool(esperado and token) and hmac.compare_digest(esperado, hash_do_token(token))


def registrar_webhook_principal(evento: EventoWebhook, corpo: Any) -> WebhookRecebido | None:
    """Grava o aviso da conta principal no public. O mesmo `evento_id` de novo: `None`, e nada
    acontece (idempotência)."""
    with schema_context(get_public_schema_name()):
        try:
            with transaction.atomic():
                return WebhookRecebido.objects.create(
                    provedor=evento.provedor,
                    evento_id=evento.evento_id,
                    recebido_em=relogio.agora(),
                    corpo={
                        "evento": {
                            "tipo": evento.tipo,
                            "cobranca_id": evento.cobranca_id,
                            "referencia_externa": evento.referencia_externa,
                            "autorizacao_id": evento.autorizacao_id,
                        },
                        "conta": "principal",
                        "bruto": aviso_sem_cartao(corpo),  # ADR 0023, M-01 da T-189
                    },
                )
        except IntegrityError:
            return None


def processar_webhook_fatura(webhook_id: int) -> str:
    """Baixa da fatura da assinatura pelo aviso da conta principal (PLT-14). Não confia no
    corpo: consulta a cobrança no parceiro. Paga com o valor da fatura → `paga`, com `pago_em` e
    a `forma`; pago na página do parceiro com a forma `cartao`, o cartão fica guardado (ADR 0023).
    Valor diferente, estorno, fatura que não está em aberto ou situação desconhecida: não baixa;
    fica no resultado do aviso para a equipe (Django Admin). Idempotente."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        webhook: WebhookRecebido = WebhookRecebido.objects.select_for_update().get(pk=webhook_id)
        if webhook.processado_em is not None:
            return webhook.resultado
        resultado = _processar_fatura(webhook)
        webhook.processado_em = relogio.agora()
        webhook.resultado = resultado
        webhook.save(update_fields=["processado_em", "resultado"])
    if resultado not in ("baixada", "autorizada"):
        logger.warning("Aviso %s da conta principal: %s", webhook.pk, resultado)
    return resultado


def _processar_fatura(webhook: WebhookRecebido) -> str:
    autorizacao_id = str(webhook.corpo.get("evento", {}).get("autorizacao_id") or "")
    if autorizacao_id:
        return _processar_autorizacao(autorizacao_id)
    cobranca_id = str(webhook.corpo.get("evento", {}).get("cobranca_id", ""))
    fatura: FaturaAssinatura | None = (
        FaturaAssinatura.objects.select_for_update(of=("self",))
        .select_related("empresa")
        .filter(cobranca_externa_id=cobranca_id)
        .first()
    )
    if fatura is None or not cobranca_id:
        return "cobranca_desconhecida"
    try:
        situacao = provedor().consultar_cobranca(conta_principal(), cobranca_id)
    except StatusDesconhecido:
        return "status_desconhecido"
    if situacao.status == "estornada":
        return "estornada_no_parceiro"  # cancelamento da nota e devolução: equipe (fase 2)
    if situacao.status != "paga":
        return situacao.status
    if fatura.status == StatusFatura.PAGA:
        return "ja_baixada"
    if fatura.status not in (StatusFatura.ABERTA, StatusFatura.ATRASADA):
        return "fatura_nao_aberta"
    if situacao.valor_pago_centavos != fatura.valor_centavos:
        return "valor_diferente"
    if not nfse_ligada():
        # Sem a emissão da nota (MVP, até a T-197), o tomador nasce na baixa (PLT-14, T-236).
        gravar_tomador(fatura)
    fatura.pago_em = situacao.pago_em or relogio.agora()
    fatura.forma = situacao.forma if situacao.forma in FormaPagaFatura.values else ""
    fatura.recibo_url = situacao.recibo_url[:500]
    campos: tuple[str, ...] = ("pago_em", "forma", "recibo_url")
    apagada = fatura.empresa.apagada_em is not None
    if apagada and not nfse_ligada():
        # AUD-08 (CA-ASS-60): o e-mail de cobrança sai da fatura na baixa. Com a nota ligada, sai
        # depois de a nota ser pedida (T-197).
        fatura.email_cobranca = ""
        campos += ("email_cobranca",)
    with usar_ator(ATOR_SISTEMA):
        transicionar(
            fatura,
            StatusFatura.PAGA,
            acao="fatura_assinatura.pagar",
            regra="PLT-14",
            mais_campos=campos,
        )
        if apagada:
            # Empresa apagada: só a fatura e a auditoria do public, sem transição de estado, sem
            # evento no schema (que não existe mais) e sem e-mail ao administrador (AUD-08).
            return "baixada"
        if situacao.cartao is not None:
            _guardar_cartao(fatura.empresa, situacao.cartao)
        voltar_a_ativa_ao_pagar(_empresa_travada(fatura.empresa), relogio.hoje())
    return "baixada"


def _processar_autorizacao(autorizacao_id: str) -> str:
    """PLT-13: o aviso de que a autorização do Pix Automático mudou. Não confia no corpo: consulta
    a autorização no parceiro. Ativa → a forma sai de `aguardando_autorizacao` e as próximas
    faturas são cobradas por ela (`gerar_faturas`). Outra situação (recusada, expirada,
    cancelada no banco) não muda a forma: fica no resultado do aviso para a equipe."""
    forma = (
        FormaPagamentoAssinatura.objects.select_for_update()
        .filter(autorizacao_externa_id=autorizacao_id)
        .first()
    )
    if forma is None:
        return "autorizacao_desconhecida"  # de uma forma já trocada, ou de outra conta
    try:
        autorizacao = provedor().consultar_autorizacao(conta_principal(), autorizacao_id)
    except StatusDesconhecido:
        return "status_desconhecido"
    if autorizacao.status != "ativa":
        return f"autorizacao_{autorizacao.status}"
    if forma.forma != FormaAssinatura.PIX_AUTOMATICO or forma.status == StatusFormaPagamento.ATIVA:
        return "ja_autorizada"
    with usar_ator(ATOR_SISTEMA):
        transicionar(
            forma, StatusFormaPagamento.ATIVA, acao="assinatura.forma_ativa", regra="PLT-13"
        )
    return "autorizada"


def _guardar_cartao(empresa: Empresa, cartao: CartaoGuardado) -> None:
    """ADR 0023: o cartão digitado na página do parceiro fica para as próximas faturas, só se a
    forma escolhida é o cartão. Pagar por cartão com outra forma (`meio` no "Pagar") não troca a
    forma nem guarda token."""
    forma = FormaPagamentoAssinatura.objects.select_for_update().filter(empresa=empresa).first()
    if forma is None or forma.forma != FormaAssinatura.CARTAO:
        return
    with auditar(forma, "assinatura.cartao_guardado", Categoria.FINANCEIRO, regra="PLT-13"):
        forma.definir_cartao_token_cifrado(cartao.token)
        forma.cartao_bandeira = cartao.bandeira[:20]
        forma.cartao_final = cartao.final[-4:]
        forma.save(
            update_fields=[
                "cartao_token_cifrado",
                "cartao_bandeira",
                "cartao_final",
                "atualizado_em",
            ]
        )
    if forma.status != StatusFormaPagamento.ATIVA:
        transicionar(
            forma, StatusFormaPagamento.ATIVA, acao="assinatura.forma_ativa", regra="PLT-13"
        )


# --- Mudança de plano e dados fiscais (PLT-04, PLT-05, PLT-15; T-185, assinatura.md) ---

POR_ADMINISTRADOR = "administrador"  # pela tela Admin-Assinatura
POR_EQUIPE = "equipe"  # pela plataforma (Django Admin no MVP): só ela muda o ciclo
STATUS_QUE_MUDAM_DE_PLANO = frozenset({Empresa.Status.EM_TESTE, Empresa.Status.ATIVA})
PAGUE_ANTES = ("transicao_empresa", "Pague a fatura em atraso antes de mudar de plano.")
DESFACA_O_CANCELAMENTO = ("transicao_empresa", "Desfaça o cancelamento antes de mudar de plano.")
MUDANCA_CICLO = ("mudanca_ciclo", "Para mudar entre mensal e anual, fale com o suporte.")
MESMO_PLANO = ("mesmo_plano", "Este já é o seu plano.")
DIAS_PARA_PAGAR_A_DIFERENCA = 3  # PLT-04


def cancelamento_marcado(empresa: Empresa) -> bool:
    """Cancelamento pedido e a empresa ainda com acesso (`cancelamento.md`, T-195)."""
    return empresa.acesso_ate is not None and empresa.status != Empresa.Status.CANCELADA


def _mensalidades(empresa: Empresa) -> models.QuerySet[FaturaAssinatura]:
    return FaturaAssinatura.objects.filter(
        empresa_id=empresa.pk, tipo=TipoFatura.MENSALIDADE
    ).exclude(status=StatusFatura.CANCELADA)


def periodo_pago_correndo(empresa: Empresa, hoje: date) -> FaturaAssinatura | None:
    """A mensalidade paga cujo período ainda não acabou (no teste com a 1ª paga, a 1ª)."""
    return (
        _mensalidades(empresa)
        .filter(status=StatusFatura.PAGA, periodo_fim__gte=hoje)
        .order_by("periodo_inicio")
        .first()
    )


@dataclass(frozen=True)
class ProximaMensalidade:
    """A próxima fatura do período ainda não paga, ou a que ainda vai nascer (PLT-01)."""

    vencimento: date
    periodo: Periodo
    plano: Plano
    ciclo: str
    valor_centavos: int
    fatura: FaturaAssinatura | None = None

    @property
    def descricao(self) -> str:
        return descricao_da_fatura(
            TipoFatura.MENSALIDADE,
            self.plano.nome,
            self.ciclo,
            self.periodo.inicio,
            self.periodo.fim,
        )


def _o_que_vale_na_virada(empresa: Empresa) -> tuple[Plano, str, int]:
    """Plano, ciclo e preço da próxima fatura: o agendado (downgrade ou ciclo pela equipe), pelo
    preço de tabela, ou o de hoje, pelo preço contratado (PLT-04, PLT-05)."""
    plano = empresa.plano
    if plano is None:
        raise ValueError("Empresa sem plano.")
    if empresa.plano_proximo_id or empresa.ciclo_proximo:
        proximo = empresa.plano_proximo or plano
        ciclo = empresa.ciclo_proximo or empresa.ciclo
        return proximo, ciclo, preco_no_ciclo(proximo, ciclo)
    return plano, empresa.ciclo, int(empresa.preco_contratado_centavos)


def proxima_mensalidade(empresa: Empresa) -> ProximaMensalidade | None:
    """A mensalidade em aberto mais antiga; sem ela, a que nasce depois do último período pago.
    `None` sem nenhuma das duas (empresa sem fatura)."""
    aberta = (
        _mensalidades(empresa)
        .filter(status__in=[StatusFatura.ABERTA, StatusFatura.ATRASADA])
        .select_related("plano")
        .order_by("vencimento")
        .first()
    )
    if aberta is not None:
        return ProximaMensalidade(
            aberta.vencimento,
            Periodo(aberta.periodo_inicio, aberta.periodo_fim),
            aberta.plano,
            aberta.ciclo,
            int(aberta.valor_centavos),
            aberta,
        )
    paga = _mensalidades(empresa).filter(status=StatusFatura.PAGA).order_by("-periodo_fim").first()
    if paga is None or not empresa.dia_vencimento or empresa.plano is None:
        return None
    plano, ciclo, valor = _o_que_vale_na_virada(empresa)
    vencimento = paga.periodo_fim + timedelta(days=1)
    return ProximaMensalidade(
        vencimento, proximo_periodo(empresa.dia_vencimento, ciclo, vencimento), plano, ciclo, valor
    )


def _juntar(textos: list[str], conector: str) -> str:
    """ "a, b e c" (ou "a ou b")."""
    if len(textos) <= 1:
        return "".join(textos)
    return f"{', '.join(textos[:-1])} {conector} {textos[-1]}"


def pendencias_dos_modulos(
    empresa: Empresa | None, recursos_que_saem: Iterable[str]
) -> list[dict[str, Any]]:
    """O que está aberto nos módulos que saem (PLT-12, ADR 0024, itens 7 e 9):
    `[{grupo, quantidade, texto}]`, só os grupos com quantidade, na ordem do contrato. Conta no
    schema da empresa; com `empresa=None`, no schema corrente (a troca de ramo)."""
    saem = sorted(set(recursos_que_saem))
    if not saem:
        return []
    if empresa is None or conexao().schema_name == empresa.schema_name:
        return modulos.pendencias(saem)
    with no_schema_da_empresa(empresa):
        return modulos.pendencias(saem)


def _atividade_da_empresa(empresa: Empresa) -> str:
    """O ramo guardado da empresa (`comum.empresa.atividade`), lido no schema dela."""
    if conexao().schema_name == empresa.schema_name:
        return comum_empresa.atividade()
    with no_schema_da_empresa(empresa):
        return comum_empresa.atividade()


# Na fase 1 (PLT-12, T-356), a recusa do downgrade confere só as despesas; os outros grupos
# (OS, vendas e comissões) entram quando os módulos existirem. A troca de ramo não muda.
GRUPOS_DO_DOWNGRADE = frozenset({"despesas_aguardando_aprovacao", "despesas_a_pagar"})


def excede_no_plano(empresa: Empresa, plano: Plano, uso: UsoEmpresa) -> dict[str, Any]:
    """O que não cabe em `plano` (PLT-03, PLT-04, PLT-12): a atividade que o plano não aceita, os
    itens acima do limite (86 de 30) e o que está aberto nos módulos que saem (ADR 0024, itens 7
    e 10). Vazio = cabe."""
    from .selectors import atividades_aceitas, recursos_para

    excede: dict[str, Any] = {}
    atividade = _atividade_da_empresa(empresa)
    aceitas = atividades_aceitas(plano)
    if atividade not in aceitas:
        excede["atividade"] = {"atual": atividade, "aceitas": list(aceitas)}
    for item in Item.values:
        limite = plano.limite(item)
        usado = int(getattr(uso, item))
        if limite is not None and usado > limite:
            excede[item] = {"usado": usado, "limite": limite}
    saem = recursos_para(empresa.plano, atividade) - recursos_para(plano, atividade)
    abertos = [
        grupo
        for grupo in pendencias_dos_modulos(empresa, saem)
        if grupo["grupo"] in GRUPOS_DO_DOWNGRADE
    ]
    if abertos:
        excede["abertos"] = abertos
        excede["abertos_texto"] = _juntar([grupo["texto"] for grupo in abertos], "e")
    return excede


def _recusa_do_downgrade(plano: Plano, excede: dict[str, Any]) -> ErroDeRegra:
    """422 `PLT-04` com tudo o que não cabe de uma vez, como a `FIL-06`. Com a atividade, a
    mensagem é a dela: o ramo se resolve primeiro (`assinatura.md`, CA-ASS-52)."""
    if "atividade" in excede:
        return ErroDeRegra(
            "PLT-04",
            f"O plano {plano.nome} não inclui vendas. Para mudar, sua empresa precisa alugar.",
            excede,
        )
    itens = _juntar([Item(item).label for item in Item.values if item in excede], "ou")
    abertos = excede.get("abertos_texto", "")
    if itens and abertos:
        acao = f"Desative {itens} e resolva o que está aberto antes de mudar: {abertos}."
    elif itens:
        acao = f"Desative {itens} antes de mudar."
    else:
        acao = f"Resolva o que está aberto antes de mudar: {abertos}."
    return ErroDeRegra("PLT-04", f"Seu uso não cabe no plano {plano.nome}. {acao}", excede)


def plano_acima(novo: Plano, atual: Plano) -> bool:
    """Pela `ordem` do catálogo; na mesma ordem, pelo preço."""
    return (novo.ordem, int(novo.preco_mensal_centavos)) > (
        atual.ordem,
        int(atual.preco_mensal_centavos),
    )


@dataclass(frozen=True)
class FaturaDaDiferenca:
    valor_centavos: int
    vencimento: date
    periodo: Periodo
    descricao: str


@dataclass(frozen=True)
class Simulacao:
    """O que acontece numa mudança de plano (simular e confirmar dão o mesmo, ADR 0005)."""

    tipo: str  # upgrade, downgrade ou ciclo (só a equipe)
    plano: Plano
    ciclo: str
    vale_em: date
    vale_agora: bool
    preco_novo_centavos: int
    diferenca_centavos: int
    fatura_diferenca: FaturaDaDiferenca | None
    proxima: ProximaMensalidade | None
    mensagem: str
    # No teste com a 1ª fatura em aberto: troca livre, sem cobrança (PLT-04).
    livre_no_teste: bool = False


def _conferir_estado(empresa: Empresa) -> None:
    """Só `em_teste` e `ativa` mudam de plano, e sem cancelamento marcado (PLT-04, PLT-06)."""
    if cancelamento_marcado(empresa):
        raise Conflito(*DESFACA_O_CANCELAMENTO)
    if empresa.status in (Empresa.Status.INADIMPLENTE, Empresa.Status.SUSPENSA):
        raise Conflito(*PAGUE_ANTES)
    if empresa.status not in STATUS_QUE_MUDAM_DE_PLANO:
        raise Conflito("transicao_empresa", "Sua empresa não pode mudar de plano agora.")


def _diferenca_do_upgrade(
    empresa: Empresa, plano: Plano, ciclo: str, preco_novo: int, hoje: date
) -> FaturaDaDiferenca | None:
    """(novo − contratado) × dias que faltam ÷ dias do período, contando o dia da mudança,
    arredondada uma vez (PLT-04, ADR 0009): 45000 × 21 ÷ 31 = 30483,87 → 30484."""
    correndo = periodo_pago_correndo(empresa, hoje)
    if correndo is None:
        return None
    inicio = max(hoje, correndo.periodo_inicio)
    dias = (correndo.periodo_fim - correndo.periodo_inicio).days + 1
    faltam = (correndo.periodo_fim - inicio).days + 1
    valor = proporcional(preco_novo - int(empresa.preco_contratado_centavos), faltam, dias)
    if valor <= 0:
        return None
    return FaturaDaDiferenca(
        valor,
        hoje + timedelta(days=DIAS_PARA_PAGAR_A_DIFERENCA),
        Periodo(inicio, correndo.periodo_fim),
        descricao_da_fatura(
            TipoFatura.DIFERENCA_PLANO, plano.nome, ciclo, inicio, correndo.periodo_fim
        ),
    )


def _simular(
    empresa: Empresa, plano: Plano, ciclo: str, uso: UsoEmpresa, hoje: date, por: str
) -> Simulacao:
    atual = empresa.plano
    if atual is None:
        raise ValueError("Empresa sem plano.")
    _conferir_estado(empresa)
    muda_ciclo = ciclo != empresa.ciclo
    if muda_ciclo and por != POR_EQUIPE:
        raise ErroDeRegra(*MUDANCA_CICLO)
    if plano.pk == atual.pk and not muda_ciclo:
        raise ErroDeRegra(*MESMO_PLANO)
    preco_novo = preco_no_ciclo(plano, ciclo)
    sobe = plano_acima(plano, atual)
    tipo = "ciclo" if muda_ciclo else ("upgrade" if sobe else "downgrade")
    if tipo != "upgrade" and plano.pk != atual.pk:
        excede = excede_no_plano(empresa, plano, uso)
        if excede:
            raise _recusa_do_downgrade(plano, excede)
    proxima = proxima_mensalidade(empresa)
    nova = (
        replace(proxima, plano=plano, ciclo=ciclo, valor_centavos=preco_novo) if proxima else None
    )

    livre = (
        empresa.status == Empresa.Status.EM_TESTE
        and not muda_ciclo
        and not _mensalidades(empresa).filter(status=StatusFatura.PAGA).exists()
    )
    if livre:
        mensagem = f"O plano {plano.nome} vale agora."
        if nova is not None:
            mensagem += (
                f" A primeira fatura, em {dia_e_mes(nova.vencimento)}, "
                f"fica em {formatar_reais(preco_novo)}."
            )
        return Simulacao(
            tipo, plano, ciclo, hoje, True, preco_novo, 0, None, nova, mensagem, livre_no_teste=True
        )

    vale_em = proxima.vencimento if proxima else hoje
    if (empresa.plano_proximo_id is not None and tipo != "upgrade") or empresa.ciclo_proximo:
        raise Conflito(
            "transicao_empresa",
            f"Já existe uma mudança agendada para {dia_e_mes(vale_em)}. "
            "Desfaça antes de escolher outra.",
        )
    if tipo == "upgrade":
        fatura = _diferenca_do_upgrade(empresa, plano, ciclo, preco_novo, hoje)
        mensagem = f"O plano {plano.nome} vale agora."
        if fatura is not None:
            mensagem += (
                f" A diferença de {formatar_reais(fatura.valor_centavos)} vence em "
                f"{dia_e_mes(fatura.vencimento)}."
            )
        diferenca = fatura.valor_centavos if fatura else 0
        return Simulacao(
            tipo, plano, ciclo, hoje, True, preco_novo, diferenca, fatura, nova, mensagem
        )
    if nova is not None and muda_ciclo:
        dia = empresa.dia_vencimento or vale_em.day
        nova = replace(nova, periodo=proximo_periodo(dia, ciclo, vale_em))
    if tipo == "ciclo":
        mensagem = f"O plano {plano.nome} {ciclo} vale a partir de {dia_e_mes(vale_em)}."
    else:
        mensagem = (
            f"O plano {plano.nome} vale a partir de {dia_e_mes(vale_em)}. "
            f"Até lá, você continua no {atual.nome}."
        )
    return Simulacao(tipo, plano, ciclo, vale_em, False, preco_novo, 0, None, nova, mensagem)


def plano_para_mudar(plano_id: int, empresa: Empresa) -> Plano:
    """O plano pedido: ativo, ou o atual mesmo desativado (PLT-05). Outro: 404."""
    with no_publico():
        plano = Plano.objects.filter(pk=plano_id).first()
    if plano is None or (not plano.ativo and plano.pk != empresa.plano_id):
        raise NaoEncontrado("nao_encontrado", "Plano não encontrado.")
    return plano


def _uso_sem_trava(empresa: Empresa) -> UsoEmpresa:
    return UsoEmpresa.objects.filter(empresa_id=empresa.pk).first() or UsoEmpresa(empresa=empresa)


def simular_mudanca_plano(
    empresa: Empresa, plano: Plano, ciclo: str, por: str = POR_ADMINISTRADOR
) -> Simulacao:
    """Não grava nada (ADR 0005)."""
    with no_publico():
        empresa = Empresa.objects.select_related("plano", "plano_proximo").get(pk=empresa.pk)
        return _simular(empresa, plano, ciclo, _uso_sem_trava(empresa), relogio.hoje(), por)


def _registrar_nos_dois(
    empresa: Empresa,
    acao: str,
    *,
    antes: dict[str, Any],
    depois: dict[str, Any],
    categoria_publica: str,
    categoria_empresa: str = Categoria.CONFIGURACOES,
    motivo: str = "",
    regra: str = "",
) -> None:
    """O mesmo fato no public e no schema da empresa (ADR 0010). No public, os dados que o
    apagamento limpa vão como `{"alterado": true}` (AUD-08, `omitir_no_public`)."""
    for entrar, categoria in (
        (no_publico, categoria_publica),
        (lambda: no_schema_da_empresa(empresa), categoria_empresa),
    ):
        with entrar():
            registrar_evento(
                acao,
                categoria,
                objeto=empresa,
                antes=antes,
                depois=depois,
                motivo=motivo,
                regra=regra,
            )


def _mudar_valor_da_fatura(fatura: FaturaAssinatura, plano: Plano, valor_centavos: int) -> None:
    """A fatura em aberto passa ao plano e ao valor novos (PLT-04). A cobrança já emitida no
    parceiro é cancelada, e a emissão sai de novo com o valor novo (`gerar_faturas`, PLT-02)."""
    if fatura.plano_id == plano.pk and int(fatura.valor_centavos) == valor_centavos:
        return
    campos = ["plano", "valor_centavos"]
    cobranca_id = fatura.cobranca_externa_id
    if cobranca_id:
        _no_parceiro(lambda: provedor().cancelar_cobranca(conta_principal(), cobranca_id))
        campos += _limpar_cobranca(fatura)
    with auditar(fatura, "fatura_assinatura.mudar_valor", Categoria.FINANCEIRO, regra="PLT-04"):
        fatura.plano = plano
        fatura.valor_centavos = valor_centavos
        fatura.save(update_fields=[*campos, "atualizado_em"])


def _abertas_a_partir_de(empresa: Empresa, dia: date) -> list[FaturaAssinatura]:
    """Mensalidades em aberto cujo período começa em `dia` ou depois, travadas."""
    return list(
        FaturaAssinatura.objects.select_for_update()
        .filter(
            empresa_id=empresa.pk,
            tipo=TipoFatura.MENSALIDADE,
            status=StatusFatura.ABERTA,
            periodo_inicio__gte=dia,
        )
        .order_by("vencimento")
    )


def _empresa_travada(empresa: Empresa) -> Empresa:
    travada: Empresa = (
        Empresa.objects.select_for_update(of=("self",))
        .select_related("plano", "plano_proximo")
        .get(pk=empresa.pk)
    )
    return travada


def mudar_plano(
    empresa: Empresa,
    plano: Plano,
    ciclo: str,
    por: str = POR_ADMINISTRADOR,
    motivo: str | None = None,
    *,
    confirmar_valor_centavos: int | None = None,
) -> Simulacao:
    """Serviço único da mudança de plano (PLT-04, PLT-05): a tela do administrador e a ação da
    plataforma (`por=POR_EQUIPE`, que também muda o ciclo, valendo na próxima fatura).

    - No teste com a 1ª fatura em aberto: vale na hora, sem cobrança; a 1ª fatura passa ao valor
      do plano novo (CA-ASS-13).
    - Upgrade com período pago: vale na hora e cobra a diferença proporcional numa fatura avulsa
      que vence em 3 dias (CA-ASS-14: R$ 304,84).
    - Downgrade: só se couber; fica agendado em `plano_proximo` e vale na próxima fatura, que já
      sai pelo plano menor (CA-ASS-16). A virada é da `virar_estados` (T-186).

    Trava a `Empresa` e o `UsoEmpresa` para a conta do uso e a mudança serem da mesma foto.
    `confirmar_valor_centavos` diferente da diferença de agora: 409 `valor_mudou`, nada gravado.
    """
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        uso = UsoEmpresa.objects.select_for_update().filter(empresa_id=empresa.pk).first()
        hoje = relogio.hoje()
        simulacao = _simular(empresa, plano, ciclo, uso or UsoEmpresa(empresa=empresa), hoje, por)
        if (
            confirmar_valor_centavos is not None
            and confirmar_valor_centavos != simulacao.diferenca_centavos
        ):
            raise Conflito(
                "valor_mudou",
                "O valor da diferença mudou. Confira o novo valor antes de confirmar.",
                {"diferenca_centavos": simulacao.diferenca_centavos},
            )
        atual = empresa.plano
        if atual is None:
            raise ValueError("Empresa sem plano.")
        antes = {
            "plano": atual.nome,
            "ciclo": empresa.ciclo,
            "preco_contratado_centavos": int(empresa.preco_contratado_centavos),
        }
        if simulacao.vale_agora:
            empresa.plano = plano
            empresa.preco_contratado_centavos = simulacao.preco_novo_centavos
            # Um upgrade desfaz o downgrade que estava agendado (assinatura.md).
            empresa.plano_proximo = None
            empresa.save(
                update_fields=[
                    "plano",
                    "preco_contratado_centavos",
                    "plano_proximo",
                    "atualizado_em",
                ]
            )
            # No teste, a 1ª fatura; com período pago, as dos períodos que ainda não começaram.
            desde = date.min if simulacao.livre_no_teste else hoje + timedelta(days=1)
            for fatura in _abertas_a_partir_de(empresa, desde):
                _mudar_valor_da_fatura(fatura, plano, simulacao.preco_novo_centavos)
            if simulacao.fatura_diferenca is not None:
                avulsa = simulacao.fatura_diferenca
                diferenca = criar_fatura(
                    empresa,
                    tipo=TipoFatura.DIFERENCA_PLANO,
                    vencimento=avulsa.vencimento,
                    periodo=avulsa.periodo,
                    plano=plano,
                    ciclo=ciclo,
                    valor_centavos=avulsa.valor_centavos,
                    regra="PLT-04",
                )
                _cobrar_diferenca_no_cartao(empresa, diferenca)
        else:
            empresa.plano_proximo = plano
            empresa.ciclo_proximo = ciclo if simulacao.tipo == "ciclo" else ""
            empresa.save(update_fields=["plano_proximo", "ciclo_proximo", "atualizado_em"])
            if simulacao.tipo != "ciclo":
                # A fatura da virada já gerada sai pelo plano menor (CA-ASS-16, CA-ASS-41).
                for fatura in _abertas_a_partir_de(empresa, simulacao.vale_em):
                    _mudar_valor_da_fatura(fatura, plano, simulacao.preco_novo_centavos)
        _registrar_nos_dois(
            empresa,
            "empresa.mudar_ciclo" if simulacao.tipo == "ciclo" else "empresa.mudar_plano",
            antes=antes,
            depois={
                "plano": plano.nome,
                "ciclo": ciclo,
                "preco_contratado_centavos": simulacao.preco_novo_centavos,
                "diferenca_centavos": simulacao.diferenca_centavos,
                "vale_em": simulacao.vale_em.isoformat(),
            },
            categoria_publica=Categoria.FINANCEIRO,
            motivo=motivo or "",
            regra="PLT-04",
        )
    return simulacao


def _cobrar_diferenca_no_cartao(empresa: Empresa, fatura: FaturaAssinatura) -> None:
    """PLT-04: com o cartão guardado, a diferença do upgrade é cobrada na hora, depois do commit
    (o parceiro fora do ar não desfaz a mudança: a tarefa tenta de novo). Nas outras formas, a
    cobrança sai na `gerar_faturas`, que emite as faturas que vencem em até 5 dias."""
    forma = FormaPagamentoAssinatura.objects.filter(empresa_id=empresa.pk).first()
    if not _cartao_guardado(forma):
        return
    from .tasks import plataforma_cobrar_cartao

    fatura_id = fatura.pk
    transaction.on_commit(lambda: plataforma_cobrar_cartao.delay(fatura_id))


def desfazer_mudanca_plano(empresa: Empresa) -> None:
    """Desfaz o downgrade agendado pelo administrador até a véspera (PLT-04, CA-ASS-16). A
    fatura da virada já gerada pelo plano menor volta ao plano e ao preço de hoje. Sem downgrade
    agendado, ou com a mudança de ciclo da equipe (só ela desfaz): 404."""
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        _conferir_estado(empresa)
        agendado, atual = empresa.plano_proximo, empresa.plano
        if agendado is None or empresa.ciclo_proximo or atual is None:
            raise NaoEncontrado("nao_encontrado", "Não há mudança de plano agendada.")
        proxima = proxima_mensalidade(empresa)
        hoje = relogio.hoje()
        if proxima is not None and proxima.vencimento <= hoje:
            raise Conflito(
                "transicao_empresa",
                f"A mudança para o plano {agendado.nome} já vale desde "
                f"{dia_e_mes(proxima.vencimento)}.",
            )
        empresa.plano_proximo = None
        empresa.save(update_fields=["plano_proximo", "atualizado_em"])
        for fatura in _abertas_a_partir_de(empresa, hoje + timedelta(days=1)):
            _mudar_valor_da_fatura(fatura, atual, int(empresa.preco_contratado_centavos))
        _registrar_nos_dois(
            empresa,
            "empresa.desfazer_mudanca_plano",
            antes={"plano_proximo": agendado.nome},
            depois={"plano_proximo": None},
            categoria_publica=Categoria.FINANCEIRO,
            regra="PLT-04",
        )


def _validar_endereco(endereco: Any, erros: dict[str, list[str]]) -> dict[str, str]:
    """O endereço da nota no formato do endereço da filial (`filiais.md`), o bloco inteiro."""
    if not isinstance(endereco, Mapping):
        erros["endereco"] = ["Informe o endereço completo."]
        return {}
    cep = so_digitos(str(endereco.get("cep") or ""))
    if len(cep) != 8:
        erros["endereco.cep"] = ["Informe o CEP com 8 dígitos."]
    uf = str(endereco.get("uf") or "").strip().upper()
    if uf not in UFS:
        erros["endereco.uf"] = ["UF inválida."]
    limpo = {"cep": cep, "uf": uf}
    for campo in ("logradouro", "numero", "complemento", "bairro", "cidade"):
        valor = str(endereco.get(campo) or "").strip()
        tamanho = getattr(Empresa._meta.get_field(f"endereco_{campo}"), "max_length", 0) or 0
        if campo != "complemento" and not valor:
            erros[f"endereco.{campo}"] = ["Campo obrigatório."]
        elif len(valor) > tamanho:
            erros[f"endereco.{campo}"] = [f"Use até {tamanho} caracteres."]
        limpo[campo] = valor
    return limpo


def _validar_dados_fiscais(dados: Mapping[str, Any]) -> dict[str, str]:
    erros: dict[str, list[str]] = {}
    if "cnpj" in dados:
        erros["cnpj"] = ["O CNPJ não muda por aqui. Fale com o suporte."]
    campos: dict[str, str] = {}
    if "razao_social" in dados:
        razao = str(dados["razao_social"] or "").strip()
        if not razao:
            erros["razao_social"] = ["Informe a razão social."]
        elif len(razao) > 150:
            erros["razao_social"] = ["Use até 150 caracteres."]
        campos["razao_social"] = razao
    if "email_cobranca" in dados:
        email = str(dados["email_cobranca"] or "").strip().lower()
        try:
            validate_email(email)
        except DjangoValidationError:
            erros["email_cobranca"] = ["Informe um e-mail válido."]
        campos["email_cobranca"] = email
    if "endereco" in dados:
        for campo, valor in _validar_endereco(dados["endereco"], erros).items():
            campos[f"endereco_{campo}"] = valor
    if erros:
        raise ErroDeValidacao(erros)
    return campos


def atualizar_dados_fiscais(empresa: Empresa, dados: Mapping[str, Any]) -> Empresa:
    """Dados da nota da assinatura (PLT-15): razão social, endereço (o bloco inteiro; nulo é
    recusado) e e-mail de cobrança. O CNPJ não muda por aqui. Editar o endereço não muda filial
    nenhuma (CA-ASS-48). Atualiza o pagador na conta principal depois do commit; com o endereço
    novo, pede as notas que esperavam por ele."""
    campos = _validar_dados_fiscais(dados)
    with no_publico(), transaction.atomic():
        atual: Empresa = Empresa.objects.select_for_update().get(pk=empresa.pk)
        tinha_endereco = bool(atual.endereco_cep)
        antes = retrato(atual)
        for campo, valor in campos.items():
            setattr(atual, campo, valor)
        mudou_antes, mudou_depois = diferenca(antes, retrato(atual))
        if not mudou_depois:
            return atual
        atual.save(update_fields=[*campos, "atualizado_em"])
        _registrar_nos_dois(
            atual,
            "empresa.dados_fiscais",
            antes=mudou_antes,
            depois=mudou_depois,
            categoria_publica=Categoria.CONFIGURACOES,
            regra="PLT-15",
        )
        if not tinha_endereco and atual.endereco_cep:
            _agendar_notas_pendentes(atual.pk)
        tem_pagador = (
            FormaPagamentoAssinatura.objects.filter(empresa=atual)
            .exclude(cliente_externo_id="")
            .exists()
        )
        if tem_pagador:
            from .tasks import plataforma_atualizar_pagador

            empresa_id = atual.pk
            transaction.on_commit(lambda: plataforma_atualizar_pagador.delay(empresa_id))
    return atual


# --- Forma de pagamento e faturas (PLT-02, PLT-13, PLT-14; T-185 parte 2, ADR 0023) ---

MEIOS_DE_PAGAR = ("cartao", "pix", "boleto")
# Na fatura, a cobrança no parceiro: o cartão é sempre a página dele (ADR 0023).
TIPO_DA_COBRANCA = {"cartao": "cartao_link", "pix": "pix", "boleto": "boleto"}
MEIO_DA_FORMA = {
    FormaAssinatura.CARTAO: "cartao",
    FormaAssinatura.PIX_AUTOMATICO: "pix",
    FormaAssinatura.BOLETO: "boleto",
}
# A cobrança que não é do "Pagar": a do Pix Automático pela autorização e a do cartão guardado.
# Um "Pagar" depois delas cria a de outro tipo (Pix avulso, página do cartão) e cancela a antiga.
COBRANCA_PELA_AUTORIZACAO = "pix_auto"
COBRANCA_NO_CARTAO_GUARDADO = "cartao"
EM_ABERTO = (StatusFatura.ABERTA, StatusFatura.ATRASADA)
FATURA_NAO_PAGAVEL = ("fatura_nao_pagavel", "Esta fatura já foi paga ou cancelada.")
SEM_FORMA_PAGAMENTO = ("sem_forma_pagamento", "Escolha a forma de pagamento antes.")
# O QR da autorização do Pix automático vale 24 horas no parceiro (`immediateQrCode`).
VALIDADE_DO_QR_DA_AUTORIZACAO = timedelta(hours=24)
CAMPOS_DA_COBRANCA_VIVA = (
    "cobranca_externa_id",
    "cobranca_emitida_em",
    "cobranca_tipo",
    "cobranca_pix_copia_e_cola",
    "cobranca_linha_digitavel",
    "cobranca_boleto_url",
    "cobranca_url_pagina",
)


def _no_parceiro[T](chamada: Callable[[], T]) -> T:
    """A chamada à conta principal: fora do ar, 503; recusou, 422 com a mensagem dele."""
    try:
        return chamada()
    except ParceiroIndisponivel as erro:
        raise ParceiroForaDoAr(*PARCEIRO_FORA_DO_AR) from erro
    except ParceiroRecusou as erro:
        raise ErroDeRegra("parceiro_recusou", erro.mensagem) from erro


def _limpar_cobranca(fatura: FaturaAssinatura) -> list[str]:
    fatura.cobranca_externa_id = None
    fatura.cobranca_emitida_em = None
    for campo in CAMPOS_DA_COBRANCA_VIVA[2:]:
        setattr(fatura, campo, "")
    return list(CAMPOS_DA_COBRANCA_VIVA)


def _cancelar_cobranca_viva(fatura: FaturaAssinatura) -> bool:
    """Uma cobrança viva por fatura: cancela a de agora no parceiro antes de outra nascer. Se o
    parceiro diz que ela já foi paga, nada é cancelado (a baixa segue pelo webhook) e devolve
    `False`."""
    cobranca_id = fatura.cobranca_externa_id
    if not cobranca_id:
        return True
    try:
        situacao = _no_parceiro(
            lambda: provedor().consultar_cobranca(conta_principal(), cobranca_id)
        )
    except StatusDesconhecido:
        return False
    if situacao.status == "paga":
        return False
    if situacao.status not in ("cancelada", "estornada"):
        _no_parceiro(lambda: provedor().cancelar_cobranca(conta_principal(), cobranca_id))
    campos = _limpar_cobranca(fatura)
    with auditar(
        fatura, "fatura_assinatura.cancelar_cobranca", Categoria.FINANCEIRO, regra="PLT-14"
    ):
        fatura.save(update_fields=[*campos, "atualizado_em"])
    return True


def _pedido_da_fatura(fatura: FaturaAssinatura, tipo: str) -> PedidoCobranca:
    """A fatura vencida sai para hoje (o parceiro não emite com vencimento passado)."""
    empresa = Empresa.objects.get(pk=fatura.empresa_id)
    cliente = atualizar_pagador(empresa)
    return PedidoCobranca(
        tipo,
        int(fatura.valor_centavos),
        max(fatura.vencimento, relogio.hoje()),
        f"fatura-{fatura.pk}",
        pagador_da_empresa(empresa, cliente),
    )


def _emitir_cobranca(
    fatura: FaturaAssinatura, meio: str, autorizacao_id: str = ""
) -> FaturaAssinatura:
    """Cria a cobrança da fatura na conta principal, pelo `meio`, e guarda o que a tela mostra.
    Com `autorizacao_id`, é a cobrança do Pix Automático pela autorização (PLT-02, PLT-13)."""
    pedido = _pedido_da_fatura(fatura, TIPO_DA_COBRANCA[meio])
    if autorizacao_id:
        cobranca = _no_parceiro(
            lambda: provedor().cobrar_com_autorizacao(conta_principal(), autorizacao_id, pedido)
        )
    else:
        cobranca = _no_parceiro(lambda: provedor().criar_cobranca(conta_principal(), pedido))
    fatura.cobranca_externa_id = cobranca.id
    fatura.cobranca_emitida_em = relogio.agora()
    fatura.cobranca_tipo = COBRANCA_PELA_AUTORIZACAO if autorizacao_id else pedido.tipo
    fatura.cobranca_pix_copia_e_cola = cobranca.pix_copia_e_cola
    fatura.cobranca_linha_digitavel = cobranca.linha_digitavel[:60]
    fatura.cobranca_boleto_url = cobranca.boleto_url[:500]
    fatura.cobranca_url_pagina = cobranca.url_pagina[:500]
    with auditar(fatura, "fatura_assinatura.emitir_cobranca", Categoria.FINANCEIRO, regra="PLT-14"):
        fatura.save(update_fields=[*CAMPOS_DA_COBRANCA_VIVA, "atualizado_em"])
    return fatura


def _cobranca_pelo_meio(fatura: FaturaAssinatura, meio: str) -> FaturaAssinatura:
    """A cobrança viva no mesmo meio é devolvida como está (não cria duas); em outro meio, a
    antiga é cancelada antes (uma cobrança viva por fatura)."""
    if fatura.cobranca_externa_id and fatura.cobranca_tipo == TIPO_DA_COBRANCA[meio]:
        return fatura
    if not _cancelar_cobranca_viva(fatura):
        raise Conflito(*FATURA_NAO_PAGAVEL)
    return _emitir_cobranca(fatura, meio)


def pagar_fatura(empresa: Empresa, codigo: str, meio: str | None = None) -> FaturaAssinatura:
    """O "Pagar" da fatura `aberta` ou `atrasada` (PLT-14). Sem `meio`, pela forma cadastrada
    (cartão: a página do parceiro; Pix automático: o Pix avulso da fatura, ou o boleto vivo da
    fatura emitida sem a autorização; boleto). Com `meio`,
    paga por outro meio sem trocar a forma (PLT-02, depois da 2ª recusa do cartão; a `suspensa`
    sem forma, CA-ASS-27). A baixa nunca vem daqui: vem do webhook."""
    if meio is not None and meio not in MEIOS_DE_PAGAR:
        raise ErroDeValidacao({"meio": ["Use cartao, pix ou boleto."]})
    with no_publico(), transaction.atomic():
        fatura = (
            FaturaAssinatura.objects.select_for_update()
            .filter(empresa_id=empresa.pk, codigo=codigo)
            .first()
        )
        if fatura is None:
            raise NaoEncontrado("nao_encontrado", "Fatura não encontrada.")
        if fatura.status not in EM_ABERTO:
            raise Conflito(*FATURA_NAO_PAGAVEL)
        if meio is None:
            forma = FormaPagamentoAssinatura.objects.filter(empresa_id=empresa.pk).first()
            if forma is None or not forma.forma:
                raise ErroDeRegra(*SEM_FORMA_PAGAMENTO)
            meio = MEIO_DA_FORMA[FormaAssinatura(forma.forma)]
            if (
                forma.forma == FormaAssinatura.PIX_AUTOMATICO
                and fatura.cobranca_externa_id
                and fatura.cobranca_tipo == "boleto"
            ):
                # Emitida em boleto por falta da autorização: fica no boleto, que já traz o Pix
                # (PLT-13, T-298); um Pix avulso cancelaria o boleto que foi por e-mail.
                meio = "boleto"
        return _cobranca_pelo_meio(fatura, meio)


def _esquecer_cartao(forma: FormaPagamentoAssinatura) -> list[str]:
    """ADR 0023, item 3: trocar de forma apaga o token, a bandeira e o final, na linha travada
    (um aviso atrasado do parceiro não regrava o cartão, `_guardar_cartao`)."""
    forma.definir_cartao_token_cifrado(None)
    forma.cartao_bandeira = ""
    forma.cartao_final = ""
    return ["cartao_token_cifrado", "cartao_bandeira", "cartao_final"]


def _autorizar_pix(empresa: Empresa) -> Autorizacao:
    """A autorização recorrente na conta principal: frequência do ciclo, valor = preço
    contratado, a partir da próxima fatura (PLT-13)."""
    cliente = atualizar_pagador(empresa)
    proxima = proxima_mensalidade(empresa)
    pedido = PedidoRecorrencia(
        referencia_externa=f"assinatura-{empresa.pk}",
        frequencia="anual" if empresa.ciclo == Empresa.Ciclo.ANUAL else "mensal",
        inicio=proxima.vencimento if proxima else relogio.hoje(),
        valor_centavos=int(empresa.preco_contratado_centavos),
        primeira_cobranca_centavos=0,
        pagador=pagador_da_empresa(empresa, cliente),
        descricao=f"Assinatura {empresa.nome_exibicao}",
    )
    return _no_parceiro(lambda: provedor().criar_autorizacao_recorrente(conta_principal(), pedido))


def _status_da_forma(forma: FormaPagamentoAssinatura) -> str:
    """Boleto vale na hora; Pix automático espera a autorização no banco; cartão espera ser
    digitado na página do parceiro (o que já está guardado continua valendo)."""
    if forma.forma == FormaAssinatura.BOLETO:
        return StatusFormaPagamento.ATIVA
    if forma.forma == FormaAssinatura.CARTAO and forma.cartao_final:
        return str(forma.status)
    return StatusFormaPagamento.PENDENTE


def escolher_forma_pagamento(empresa: Empresa, nova: str) -> dict[str, Any] | None:
    """PLT-13: grava a forma e devolve o próximo passo. Não muda o estado da empresa (CA-ASS-02).
    Vale para a próxima cobrança e para a fatura em aberto (CA-ASS-26): a forma anterior é
    desfeita no parceiro (autorização do Pix cancelada, cartão esquecido) e a cobrança viva de
    outra forma é cancelada; a nova sai na emissão ou no "Pagar". Os dados do cartão nunca passam
    pelo Giro (ADR 0023)."""
    if nova not in FormaAssinatura.values:
        raise ErroDeValidacao({"forma": ["Escolha cartão, Pix automático ou boleto."]})
    proximo_passo: dict[str, Any] | None = None
    with no_publico(), transaction.atomic():
        empresa = Empresa.objects.select_related("plano").get(pk=empresa.pk)
        FormaPagamentoAssinatura.objects.get_or_create(empresa=empresa)
        forma = FormaPagamentoAssinatura.objects.select_for_update().get(empresa=empresa)
        antiga = forma.forma
        autorizacao_antiga = forma.autorizacao_externa_id
        campos = ["forma", "autorizacao_externa_id"]
        # O que é novo no parceiro primeiro: se ele recusar, nada da forma antiga se perde.
        if nova == FormaAssinatura.PIX_AUTOMATICO:
            autorizacao = _autorizar_pix(empresa)
            forma.autorizacao_externa_id = autorizacao.id
            proximo_passo = {
                "tipo": "autorizar_pix",
                "pix_copia_e_cola": autorizacao.pix_copia_e_cola,
                "expira_em": relogio.agora() + VALIDADE_DO_QR_DA_AUTORIZACAO,
            }
        else:
            forma.autorizacao_externa_id = ""
        if autorizacao_antiga and autorizacao_antiga != forma.autorizacao_externa_id:
            _no_parceiro(
                lambda: provedor().cancelar_autorizacao(conta_principal(), autorizacao_antiga)
            )
        if antiga == FormaAssinatura.CARTAO and nova != FormaAssinatura.CARTAO:
            campos += _esquecer_cartao(forma)
        forma.forma = nova
        forma.save(update_fields=[*campos, "atualizado_em"])
        status = _status_da_forma(forma)
        if status != forma.status:
            transicionar(forma, status, acao="assinatura.forma_situacao", regra="PLT-13")
        tipo_novo = TIPO_DA_COBRANCA[MEIO_DA_FORMA[FormaAssinatura(nova)]]
        em_aberto = list(
            FaturaAssinatura.objects.select_for_update()
            .filter(empresa=empresa, status__in=EM_ABERTO)
            .order_by("vencimento")
        )
        # Para pagar agora: a atrasada, ou a aberta já emitida (antes de cancelar a cobrança).
        pagavel = next(
            (
                f
                for f in em_aberto
                if f.status == StatusFatura.ATRASADA or f.cobranca_emitida_em is not None
            ),
            None,
        )
        for fatura in em_aberto:
            if fatura.cobranca_externa_id and fatura.cobranca_tipo != tipo_novo:
                _cancelar_cobranca_viva(fatura)
        if nova == FormaAssinatura.CARTAO and pagavel is not None:
            _cobranca_pelo_meio(pagavel, "cartao")
            proximo_passo = {
                "tipo": "pagina_parceiro",
                "url": pagavel.cobranca_url_pagina,
                "fatura": pagavel.codigo,
            }
        if antiga != nova:
            # Só a forma antiga e a nova: nunca token nem dado do cartão (T-189, item 5).
            for entrar in (no_publico, lambda: no_schema_da_empresa(empresa)):
                with entrar():
                    registrar_evento(
                        "assinatura.forma_pagamento",
                        Categoria.FINANCEIRO,
                        objeto=forma,
                        antes={"forma": antiga or None},
                        depois={"forma": nova},
                        regra="PLT-13",
                    )
    return proximo_passo


# --- Estados da empresa e virada do dia (PLT-01, PLT-02, PLT-04; T-186, assinatura.md) ---

DIAS_ATE_SUSPENDER = 15  # PLT-02: D+15 da fatura atrasada mais antiga
STATUS_QUE_VOLTAM_AO_PAGAR = frozenset({Empresa.Status.INADIMPLENTE, Empresa.Status.SUSPENSA})


def transicionar_empresa(empresa: Empresa, novo: str, *, regra: str, motivo: str = "") -> None:
    """Muda o estado da empresa no public e registra o mesmo fato na empresa (ADR 0010).
    Quem chama trava a `Empresa` e escolhe o ator (a virada e o webhook usam o sistema)."""
    antigo = empresa.status
    with schema_context(get_public_schema_name()):
        transicionar(empresa, novo, acao=f"empresa.{novo}", regra=regra, motivo=motivo)
    with no_schema_da_empresa(empresa):
        registrar_evento(
            f"empresa.{novo}",
            Categoria.CONFIGURACOES,
            objeto=empresa,
            antes={"status": antigo},
            depois={"status": novo},
            motivo=motivo,
            regra=regra,
        )


def _atrasada_mais_antiga(empresa: Empresa) -> FaturaAssinatura | None:
    """A fatura atrasada mais antiga, mensalidade ou diferença do upgrade."""
    return (
        FaturaAssinatura.objects.filter(empresa_id=empresa.pk, status=StatusFatura.ATRASADA)
        .order_by("vencimento", "numero")
        .first()
    )


def _primeira_paga(empresa: Empresa) -> bool:
    primeira = _mensalidades(empresa).order_by("periodo_inicio", "numero").first()
    return primeira is not None and primeira.status == StatusFatura.PAGA


def _tem_forma(empresa: Empresa) -> bool:
    return FormaPagamentoAssinatura.objects.filter(empresa_id=empresa.pk).exclude(forma="").exists()


def marcar_faturas_atrasadas(hoje: date) -> int:
    """PLT-02: a fatura `aberta` sem pagamento passa a `atrasada` no dia seguinte ao vencimento
    (D+1). Idempotente: a já atrasada não entra de novo."""
    vencidas = list(
        FaturaAssinatura.objects.filter(status=StatusFatura.ABERTA, vencimento__lt=hoje)
        .order_by("empresa_id", "vencimento")
        .values_list("pk", flat=True)
    )
    marcadas = 0
    for pk in vencidas:
        with transaction.atomic():
            fatura = FaturaAssinatura.objects.select_for_update().get(pk=pk)
            if fatura.status != StatusFatura.ABERTA:
                continue
            transicionar(
                fatura, StatusFatura.ATRASADA, acao="fatura_assinatura.atrasar", regra="PLT-02"
            )
            marcadas += 1
    return marcadas


def estado_do_dia(empresa: Empresa, hoje: date) -> str | None:
    """Para onde a empresa vai hoje pela tabela de transições (`assinatura.md`), ou `None`. Só
    as do relógio: a volta a `ativa` ao pagar é da baixa (`voltar_a_ativa_ao_pagar`). Cancelar,
    pausar e voltar da pausa vêm antes destas (`_virar_cancelamentos_e_pausas`); a `pausada` não
    passa por aqui (não vira `inadimplente` nem `suspensa` durante a pausa, CA-ASS-57)."""
    status = empresa.status
    if status == Empresa.Status.EM_TESTE:
        if empresa.teste_fim is None or hoje <= empresa.teste_fim:
            return None
        if _primeira_paga(empresa):
            return Empresa.Status.ATIVA  # paga no teste: ativa no dia seguinte ao fim dele
        if not _tem_forma(empresa):
            return Empresa.Status.SUSPENSA  # CA-ASS-06: sem forma no fim do teste
        if _atrasada_mais_antiga(empresa) is not None:
            return Empresa.Status.INADIMPLENTE  # CA-ASS-05: com forma e sem pagar, em D+1
        return None
    atrasada = _atrasada_mais_antiga(empresa)
    if atrasada is None:
        return None
    if status == Empresa.Status.ATIVA:
        return Empresa.Status.INADIMPLENTE
    suspende_em = atrasada.vencimento + timedelta(days=DIAS_ATE_SUSPENDER)
    if status == Empresa.Status.INADIMPLENTE and hoje >= suspende_em:
        return Empresa.Status.SUSPENSA
    return None


def virar_estado_da_empresa(empresa_id: int, hoje: date) -> str | None:
    """Aplica `estado_do_dia` com a `Empresa` travada. Devolve o estado novo, se mudou."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = Empresa.objects.select_for_update(of=("self",)).get(pk=empresa_id)
        novo = estado_do_dia(empresa, hoje)
        if novo is None:
            return None
        with usar_ator(ATOR_SISTEMA):
            transicionar_empresa(empresa, novo, regra="PLT-02")
    return novo


def voltar_a_ativa_ao_pagar(empresa: Empresa, hoje: date) -> bool:
    """Tabela de estados: a `inadimplente` ou a `suspensa` sem outra fatura atrasada volta a
    `ativa` na hora; a `em_teste` também, se a 1ª fatura foi paga depois do fim do teste.
    Chamada na baixa, com a `Empresa` travada e o ator do sistema."""
    if empresa.status == Empresa.Status.EM_TESTE:
        fim_do_teste = empresa.teste_fim is not None and hoje > empresa.teste_fim
        if not fim_do_teste or not _primeira_paga(empresa):
            return False
    elif empresa.status not in STATUS_QUE_VOLTAM_AO_PAGAR:
        return False
    if _atrasada_mais_antiga(empresa) is not None:
        return False
    transicionar_empresa(empresa, Empresa.Status.ATIVA, regra="PLT-02")
    return True


def aplicar_mudanca_agendada(empresa_id: int, hoje: date) -> bool:
    """PLT-04 (CA-ASS-41): no dia do vencimento, o plano agendado (downgrade ou ciclo pela
    equipe) passa a valer, se a fatura do período que começa já saiu por ele. Não confere o uso
    de novo: o que passar do limite segue a PLT-03. Idempotente."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = _empresa_travada(Empresa(pk=empresa_id))
        novo, atual = empresa.plano_proximo, empresa.plano
        if novo is None or atual is None:
            return False
        ciclo = empresa.ciclo_proximo or empresa.ciclo
        gerada = (
            _mensalidades(empresa)
            .filter(periodo_inicio__lte=hoje, periodo_fim__gte=hoje, plano_id=novo.pk, ciclo=ciclo)
            .exists()
        )
        if not gerada:
            return False
        antes = {
            "plano": atual.nome,
            "ciclo": empresa.ciclo,
            "preco_contratado_centavos": int(empresa.preco_contratado_centavos),
        }
        empresa.plano = novo
        empresa.ciclo = ciclo
        empresa.preco_contratado_centavos = preco_no_ciclo(novo, ciclo)
        empresa.plano_proximo = None
        empresa.ciclo_proximo = ""
        empresa.save(
            update_fields=[
                "plano",
                "ciclo",
                "preco_contratado_centavos",
                "plano_proximo",
                "ciclo_proximo",
                "atualizado_em",
            ]
        )
        with usar_ator(ATOR_SISTEMA):
            _registrar_nos_dois(
                empresa,
                "empresa.mudar_plano",
                antes=antes,
                depois={
                    "plano": novo.nome,
                    "ciclo": ciclo,
                    "preco_contratado_centavos": int(empresa.preco_contratado_centavos),
                    "vale_em": hoje.isoformat(),
                },
                categoria_publica=Categoria.FINANCEIRO,
                regra="PLT-04",
            )
    recalcular_uso(empresa)
    return True


@dataclass(frozen=True)
class Virada:
    atrasadas: int
    mudancas_de_plano: int
    estados: dict[str, int]


def virar_estados(hoje: date | None = None) -> Virada:
    """A virada do dia (00:05): faturas vencidas em `atrasada`; o cancelamento marcado que chegou
    ao fim do acesso, o começo e a volta das pausas (PLT-06, `cancelamento.md`); os planos
    agendados que valem hoje; e os estados das empresas, cada empresa na sua transação.
    Idempotente: rodar de novo no mesmo dia não muda nada, e o que falhou entra na rodada
    seguinte."""
    hoje = hoje or relogio.hoje()
    with schema_context(get_public_schema_name()):
        atrasadas = marcar_faturas_atrasadas(hoje)
        estados: dict[str, int] = {}
        _virar_cancelamentos_e_pausas(hoje, estados)
        agendadas = list(
            Empresa.objects.filter(plano_proximo__isnull=False).values_list("pk", flat=True)
        )
        mudancas = sum(aplicar_mudanca_agendada(pk, hoje) for pk in agendadas)
        vivas = list(
            Empresa.objects.filter(
                status__in=[
                    Empresa.Status.EM_TESTE,
                    Empresa.Status.ATIVA,
                    Empresa.Status.INADIMPLENTE,
                ]
            ).values_list("pk", flat=True)
        )
        for pk in vivas:
            novo = virar_estado_da_empresa(pk, hoje)
            if novo is not None:
                estados[novo] = estados.get(novo, 0) + 1
    return Virada(atrasadas, mudancas, estados)


# --- Geração, emissão e cartão guardado (PLT-02, PLT-04, PLT-13; T-186 parte 2, assinatura.md) ---

DIAS_DE_ANTECEDENCIA = 5  # PLT-02: a fatura e a cobrança nascem 5 dias antes do vencimento
STATUS_QUE_GERAM_FATURA = frozenset(
    {
        Empresa.Status.EM_TESTE,
        Empresa.Status.ATIVA,
        Empresa.Status.INADIMPLENTE,
        Empresa.Status.SUSPENSA,
    }
)


def destinatarios_da_cobranca(empresa: Empresa) -> list[str]:
    """PLT-02, PLT-15: o e-mail de cobrança e os administradores ativos da empresa, sem repetir."""
    from django.contrib.auth import get_user_model

    with no_schema_da_empresa(empresa):
        administradores = list(
            get_user_model()
            .objects.filter(perfil="administrador", status="ativo")
            .order_by("pk")
            .values_list("email", flat=True)
        )
    destinatarios: list[str] = []
    for email in [empresa.email_cobranca, *administradores]:
        if email and email.lower() not in {d.lower() for d in destinatarios}:
            destinatarios.append(email)
    return destinatarios


def texto_do_que_excede(excede: Mapping[str, Any]) -> str:
    """Os limites e os abertos do downgrade recusado, sem a atividade (CA-ASS-71): "11 de 10
    usuários e 1 OS aberta"."""
    partes = [
        f"{excede[item]['usado']} de {excede[item]['limite']} {Item(item).label}"
        for item in Item.values
        if item in excede
    ]
    if excede.get("abertos_texto"):
        partes.append(str(excede["abertos_texto"]))
    return _juntar(partes, "e")


def motivo_do_downgrade_recusado(excede: Mapping[str, Any], plano: str) -> str:
    """O motivo da 1ª linha do e-mail (CA-ASS-71): a lista, a atividade ou os dois."""
    atividade = (
        f"o plano {plano} não inclui vendas, e a empresa hoje só vende. "
        "Para mudar, ela precisa alugar."
    )
    lista = texto_do_que_excede(excede)
    if not lista and "atividade" in excede:
        return f"mas {atividade}"
    motivo = f"mas o uso de hoje não cabe nele: {lista}."
    if "atividade" in excede:
        motivo += f" Além disso, {atividade}"
    return motivo


def _recusar_downgrade_agendado(
    empresa: Empresa, agendado: Plano, excede: dict[str, Any], vencimento: date
) -> None:
    """CA-ASS-40: o uso deixou de caber no plano agendado. O agendamento cai, a fatura sai pelo
    plano atual, e o administrador e o e-mail de cobrança recebem o motivo."""
    empresa.plano_proximo = None
    empresa.ciclo_proximo = ""
    empresa.save(update_fields=["plano_proximo", "ciclo_proximo", "atualizado_em"])
    with usar_ator(ATOR_SISTEMA):
        _registrar_nos_dois(
            empresa,
            "empresa.mudar_plano_recusado",
            antes={"plano_proximo": agendado.nome},
            depois={"plano_proximo": None, "detalhes": excede},
            categoria_publica=Categoria.FINANCEIRO,
            regra="PLT-04",
        )
    from .tasks import plataforma_avisar_downgrade_recusado

    empresa_id, plano_id, dia = empresa.pk, agendado.pk, vencimento.isoformat()
    transaction.on_commit(
        lambda: plataforma_avisar_downgrade_recusado.delay(empresa_id, plano_id, dia, excede)
    )


def gerar_fatura_do_periodo(empresa_id: int, hoje: date) -> FaturaAssinatura | None:
    """PLT-02: 5 dias antes do vencimento seguinte, a fatura do período seguinte, pelo que vale na
    virada (o plano agendado pelo preço de tabela, ou o de hoje pelo preço contratado). Antes,
    confere se o downgrade agendado ainda cabe (PLT-04, CA-ASS-40 e 41), com a `Empresa` e o
    `UsoEmpresa` travados. Não gera para a `pausada` nem a `cancelada`, nem o período que começa
    depois do fim do acesso (cancelamento marcado) ou em `pausa_inicio` e depois (pausa agendada,
    PLT-06). Idempotente: uma mensalidade por período."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = _empresa_travada(Empresa(pk=empresa_id))
        if empresa.status not in STATUS_QUE_GERAM_FATURA or not empresa.dia_vencimento:
            return None
        ultima = _mensalidades(empresa).order_by("-periodo_fim").first()
        if ultima is None or empresa.plano is None:
            return None  # a 1ª fatura nasce com a empresa (criar_primeira_fatura)
        vencimento = ultima.periodo_fim + timedelta(days=1)
        if hoje < vencimento - timedelta(days=DIAS_DE_ANTECEDENCIA):
            return None
        if empresa.acesso_ate is not None and vencimento > empresa.acesso_ate:
            return None  # PLT-06: nada é cobrado depois do fim do acesso
        if empresa.pausa_inicio is not None and vencimento >= empresa.pausa_inicio:
            return None  # PLT-06: nada é cobrado no período da pausa
        agendado = empresa.plano_proximo
        if agendado is not None and agendado.pk != empresa.plano_id:
            uso = UsoEmpresa.objects.select_for_update().filter(empresa_id=empresa.pk).first()
            excede = excede_no_plano(empresa, agendado, uso or UsoEmpresa(empresa=empresa))
            if excede:
                _recusar_downgrade_agendado(empresa, agendado, excede, vencimento)
        plano, ciclo, valor = _o_que_vale_na_virada(empresa)
        return criar_fatura(
            empresa,
            tipo=TipoFatura.MENSALIDADE,
            vencimento=vencimento,
            periodo=proximo_periodo(empresa.dia_vencimento, ciclo, vencimento),
            plano=plano,
            ciclo=ciclo,
            valor_centavos=valor,
            regra="PLT-02",
        )


def _cartao_guardado(forma: FormaPagamentoAssinatura | None) -> bool:
    return (
        forma is not None
        and forma.forma == FormaAssinatura.CARTAO
        and bool(forma.cartao_final)
        and bool(forma.cartao_token_cifrado)
    )


def _emitir_boleto(fatura: FaturaAssinatura, pix_pendente: bool = False) -> None:
    """O boleto com Pix e o e-mail nesse dia (PLT-02); com `pix_pendente`, o e-mail diz que o Pix
    automático ainda não foi autorizado (PLT-13)."""
    _emitir_cobranca(fatura, "boleto")
    from .tasks import plataforma_enviar_boleto

    fatura_id = fatura.pk
    transaction.on_commit(lambda: plataforma_enviar_boleto.delay(fatura_id, pix_pendente))


def emitir_cobranca_da_fatura(fatura_id: int, hoje: date) -> str:
    """PLT-02, PLT-13: a cobrança da fatura `aberta` sem cobrança, 5 dias antes do vencimento,
    pela forma no dia da emissão: o boleto com Pix (e o e-mail nesse dia), a cobrança do Pix
    Automático pela autorização (sem a autorização ativa, o boleto com Pix, CA-ASS-63), ou a
    página do parceiro para o cartão ainda não digitado. O cartão guardado
    é cobrado no dia do vencimento (`cobrar_cartao_da_fatura`). Devolve o que foi feito.
    Idempotente: a fatura com cobrança não sai de novo."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        fatura = FaturaAssinatura.objects.select_for_update().get(pk=fatura_id)
        limite = hoje + timedelta(days=DIAS_DE_ANTECEDENCIA)
        if (
            fatura.status != StatusFatura.ABERTA
            or fatura.cobranca_externa_id
            or fatura.vencimento > limite
        ):
            return "nada"
        forma = FormaPagamentoAssinatura.objects.filter(empresa_id=fatura.empresa_id).first()
        if forma is None or not forma.forma:
            return "sem_forma"  # paga pelo "Pagar" com `meio` (CA-ASS-27)
        if forma.forma == FormaAssinatura.BOLETO:
            _emitir_boleto(fatura)
            return "boleto"
        if forma.forma == FormaAssinatura.PIX_AUTOMATICO:
            if forma.status != StatusFormaPagamento.ATIVA or not forma.autorizacao_externa_id:
                # PLT-13, CA-ASS-63: sem a autorização, a fatura sai como no boleto e fica nele
                # até o fim; a forma não muda.
                _emitir_boleto(fatura, pix_pendente=True)
                return "boleto_sem_autorizacao"
            _emitir_cobranca(fatura, "pix", forma.autorizacao_externa_id)
            return "pix_automatico"
        if _cartao_guardado(forma):
            return "cartao_guardado"
        _emitir_cobranca(fatura, "cartao")  # o link vai no lembrete do D-3 e no "Pagar"
        return "cartao_link"


def _cobravel_no_cartao(fatura: FaturaAssinatura, hoje: date) -> str | None:
    """Por que a fatura não é cobrada no cartão hoje, ou `None` se é. A do período no dia do
    vencimento; a da diferença do upgrade, na hora (PLT-04); recusada, uma vez a mais no dia
    seguinte, e não há terceira (PLT-02, CA-ASS-12)."""
    if fatura.status not in EM_ABERTO:
        return "nao_aberta"
    if fatura.cobranca_tipo == COBRANCA_NO_CARTAO_GUARDADO and fatura.cobranca_externa_id:
        return "ja_cobrada"  # a baixa vem pelo webhook
    if fatura.tentativas_cartao >= TENTATIVAS_DO_CARTAO:
        return "sem_tentativa"
    if fatura.cartao_recusado_em is not None:
        if timezone.localdate(fatura.cartao_recusado_em) >= hoje:
            return "tenta_amanha"
    elif fatura.tipo == TipoFatura.MENSALIDADE and fatura.vencimento > hoje:
        return "antes_do_vencimento"
    return None


def cobrar_cartao_da_fatura(fatura_id: int, hoje: date) -> str:
    """PLT-02, ADR 0023: cobra a fatura no cartão guardado, pelo token, que só é decifrado na
    porta de `integracoes/pagamentos`. Recusado: grava `cartao_recusado_em`, soma uma tentativa e
    a régua segue. A baixa vem pelo webhook. Parceiro fora do ar: `ParceiroForaDoAr`, e nada muda
    (a tentativa não conta). Idempotente."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        fatura = FaturaAssinatura.objects.select_for_update().get(pk=fatura_id)
        motivo = _cobravel_no_cartao(fatura, hoje)
        if motivo is not None:
            return motivo
        forma = (
            FormaPagamentoAssinatura.objects.select_for_update()
            .filter(empresa_id=fatura.empresa_id)
            .first()
        )
        if forma is None or not _cartao_guardado(forma):
            return "sem_cartao"
        if not _cancelar_cobranca_viva(fatura):
            return "ja_paga"  # a página ou o boleto de antes já foi pago; a baixa segue
        pedido = _pedido_da_fatura(fatura, COBRANCA_NO_CARTAO_GUARDADO)
        try:
            cobranca = _no_parceiro(lambda: cobrar_cartao_guardado(forma, pedido))
        except CartaoRecusado:
            fatura.tentativas_cartao += 1
            fatura.cartao_recusado_em = relogio.agora()
            with (
                usar_ator(ATOR_SISTEMA),
                auditar(
                    fatura,
                    "fatura_assinatura.cartao_recusado",
                    Categoria.FINANCEIRO,
                    regra="PLT-02",
                ),
            ):
                fatura.save(
                    update_fields=["tentativas_cartao", "cartao_recusado_em", "atualizado_em"]
                )
            return "recusado"
        fatura.cobranca_externa_id = cobranca.id
        fatura.cobranca_emitida_em = relogio.agora()
        fatura.cobranca_tipo = COBRANCA_NO_CARTAO_GUARDADO
        with (
            usar_ator(ATOR_SISTEMA),
            auditar(
                fatura, "fatura_assinatura.cobrar_cartao", Categoria.FINANCEIRO, regra="PLT-02"
            ),
        ):
            fatura.save(
                update_fields=[
                    "cobranca_externa_id",
                    "cobranca_emitida_em",
                    "cobranca_tipo",
                    "atualizado_em",
                ]
            )
        return "cobrada"


def _cada_uma(nome: str, chamada: Callable[[], Any]) -> Any:
    """Uma falha (parceiro fora do ar, recusa) não para as outras: fica no log, e a rodada
    seguinte tenta de novo (nada foi gravado pela metade)."""
    try:
        return chamada()
    except (ParceiroForaDoAr, ErroDeRegra, Conflito):
        logger.warning("%s: fica para a próxima rodada", nome, exc_info=True)
        return None


def _contar(contagem: dict[str, int], feito: str | None) -> None:
    if feito:
        contagem[feito] = contagem.get(feito, 0) + 1


@dataclass(frozen=True)
class Geracao:
    faturas: int
    emitidas: dict[str, int]
    cartoes: dict[str, int]


def gerar_faturas(hoje: date | None = None) -> Geracao:
    """Às 06:00 (PLT-02): as faturas do período seguinte 5 dias antes do vencimento, com a
    conferência do downgrade; a emissão das faturas `aberta` sem cobrança que vencem em até 5 dias
    (as novas e as que nasceram de outro jeito, como a diferença do upgrade); e o cartão guardado
    no vencimento, com uma tentativa a mais no dia seguinte. Idempotente no mesmo dia."""
    dia = hoje or relogio.hoje()
    with schema_context(get_public_schema_name()):
        empresas = list(
            Empresa.objects.filter(status__in=STATUS_QUE_GERAM_FATURA)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        geradas = 0
        for pk in empresas:
            if _cada_uma(f"Fatura da empresa {pk}", partial(gerar_fatura_do_periodo, pk, dia)):
                geradas += 1
        a_emitir = list(
            FaturaAssinatura.objects.filter(
                status=StatusFatura.ABERTA,
                cobranca_externa_id__isnull=True,
                vencimento__lte=dia + timedelta(days=DIAS_DE_ANTECEDENCIA),
                empresa__status__in=STATUS_QUE_GERAM_FATURA,
            )
            .order_by("vencimento", "pk")
            .values_list("pk", flat=True)
        )
        emitidas: dict[str, int] = {}
        for pk in a_emitir:
            _contar(
                emitidas,
                _cada_uma(f"Cobrança da fatura {pk}", partial(emitir_cobranca_da_fatura, pk, dia)),
            )
        no_cartao = list(
            FaturaAssinatura.objects.filter(
                status__in=EM_ABERTO,
                tentativas_cartao__lt=TENTATIVAS_DO_CARTAO,
                empresa__forma_pagamento__forma=FormaAssinatura.CARTAO,
                empresa__forma_pagamento__cartao_final__gt="",
            )
            .filter(Q(vencimento__lte=dia) | Q(tipo=TipoFatura.DIFERENCA_PLANO))
            .order_by("vencimento", "pk")
            .values_list("pk", flat=True)
        )
        cartoes: dict[str, int] = {}
        for pk in no_cartao:
            _contar(
                cartoes,
                _cada_uma(f"Cartão da fatura {pk}", partial(cobrar_cartao_da_fatura, pk, dia)),
            )
    return Geracao(geradas, emitidas, cartoes)


# --- Régua da assinatura (AUT-13, PLT-02; T-186 parte 3, assinatura.md) ---

# PLT-02: dias a partir do vencimento e o marco de cada um. O D+15 (suspensão) é da virada.
MARCOS_DA_REGUA = {-3: "D-3", 0: "D0", 3: "D+3", 7: "D+7"}
MARCOS_COM_WHATSAPP = frozenset({"D0", "D+3"})
# PLT-02, decisão B de 16 out 2026 (CA-ASS-68): só o D+7 perdido sai depois, uma vez, até o D+14.
ULTIMO_DIA_DO_D7 = 14
FUNCOES_QUE_LIGAM = ("dono", "financeiro")  # PLT-09: o Financeiro cuida da cobrança
# Textos fixados pelo produto na T-299 (docs/qa/criterios/assinatura.md).
SUSPENSA = (
    "a empresa fica suspensa: só ver e exportar os dados, sem criar locação, venda nem cobrança"
)
SE_JA_PAGOU = "Se você já pagou, desconsidere esta mensagem."
NADA_A_FAZER = "Não é preciso fazer nada."


@dataclass(frozen=True)
class MensagemDaRegua:
    assunto: str
    texto: str
    whatsapp: str


@dataclass(frozen=True)
class Email:
    destinatarios: list[str]
    assunto: str
    texto: str


def enviar_a_cada_um(destinatarios: list[str], assunto: str, texto: str) -> int:
    """PLT-15, LGPD (M-01 da T-304): um e-mail por endereço, só ele no "Para" (sem Bcc), numa
    conexão só. O e-mail de cobrança (às vezes de fora, como o contador) e os administradores
    não veem o endereço uns dos outros. Devolve quantos saíram."""
    from django.core.mail import EmailMessage, get_connection

    mensagens = [
        EmailMessage(assunto, texto, settings.DEFAULT_FROM_EMAIL, [email])
        for email in destinatarios
    ]
    if mensagens:
        get_connection().send_messages(mensagens)
    return len(mensagens)


def _ja_avisada(fatura: FaturaAssinatura, marco: str) -> bool:
    from apps.auditoria.models import EventoAuditoria

    return EventoAuditoria.objects.filter(
        objeto_tipo=FaturaAssinatura._meta.model_name,
        objeto_id=fatura.pk,
        acao="fatura_assinatura.regua",
        depois__marco=marco,
    ).exists()


def _marco_do_dia(vencimento: date, hoje: date) -> str | None:
    """O marco exato do dia ou, do D+8 ao D+14, o D+7 que não saiu (CA-ASS-68). O D-3, o D0 e o
    D+3 perdidos não são recuperados."""
    dias = (hoje - vencimento).days
    if dias in MARCOS_DA_REGUA:
        return MARCOS_DA_REGUA[dias]
    if 7 < dias <= ULTIMO_DIA_DO_D7:
        return "D+7"
    return None


def _no_cartao_guardado(fatura: FaturaAssinatura, forma: FormaPagamentoAssinatura | None) -> bool:
    return forma is not None and (
        fatura.cobranca_tipo == COBRANCA_NO_CARTAO_GUARDADO
        or (_cartao_guardado(forma) and fatura.status == StatusFatura.ABERTA)
    )


def _automatica_sem_falha(fatura: FaturaAssinatura, forma: FormaPagamentoAssinatura | None) -> bool:
    """Cartão guardado ainda não recusado ou Pix automático autorizado: a empresa não precisa
    fazer nada (CA-ASS-65)."""
    if fatura.cobranca_tipo == COBRANCA_PELA_AUTORIZACAO:
        return True
    return fatura.cartao_recusado_em is None and _no_cartao_guardado(fatura, forma)


def _como_pagar(
    fatura: FaturaAssinatura, forma: FormaPagamentoAssinatura | None, *, whatsapp: bool = False
) -> str:
    """O caminho de pagar desta fatura, pela cobrança viva ou pela forma cadastrada. Com o
    cartão recusado, o mesmo que a tela diz (PLT-02, CA-ASS-12). No WhatsApp, o boleto vai só
    com o link."""
    if _cartao_guardado(forma) and fatura.cartao_recusado_em is not None:
        if fatura.tentativas_cartao >= TENTATIVAS_DO_CARTAO:
            return (
                "O cartão foi recusado de novo. "
                "Pague por Pix ou boleto pelo botão Pagar, em Assinatura."
            )
        return "O cartão foi recusado. Tentamos de novo amanhã."
    if forma is not None and _no_cartao_guardado(fatura, forma):
        bandeira = forma.cartao_bandeira.capitalize() or "Cartão"
        return f"A cobrança é automática no cartão {bandeira} final {forma.cartao_final}."
    if fatura.cobranca_tipo == COBRANCA_PELA_AUTORIZACAO:
        return "O pagamento sai pelo Pix automático no dia do vencimento."
    if fatura.cobranca_tipo == "cartao_link" and fatura.cobranca_url_pagina:
        return f"Cadastre o cartão e pague por este link: {fatura.cobranca_url_pagina}"
    if fatura.cobranca_tipo == "boleto" and fatura.cobranca_boleto_url:
        if whatsapp:
            return f"Boleto: {fatura.cobranca_boleto_url}"
        return (
            f"Boleto: {fatura.cobranca_boleto_url}\n"
            f"Linha digitável: {fatura.cobranca_linha_digitavel}"
        )
    if fatura.cobranca_tipo == "pix" and fatura.cobranca_pix_copia_e_cola:
        return f"Pix copia e cola: {fatura.cobranca_pix_copia_e_cola}"
    if forma is None or not forma.forma:
        return "Escolha a forma de pagamento em Assinatura e pague pelo botão Pagar."
    return "Pague pelo botão Pagar, em Assinatura."


def endereco_da_assinatura(empresa: Empresa) -> str:
    """A página `Admin-Assinatura` no domínio principal da empresa, para quem lê o e-mail não
    ter de procurar onde fica "Assinatura" (T-299)."""
    with no_publico():
        dominio = (
            Dominio.objects.filter(tenant_id=empresa.pk, is_primary=True)
            .values_list("domain", flat=True)
            .first()
        )
    return f"https://{dominio or endereco_de_acesso(empresa.subdominio or '')}/admin/assinatura"


def mensagem_da_regua(
    fatura: FaturaAssinatura, marco: str, forma: FormaPagamentoAssinatura | None
) -> MensagemDaRegua:
    """Os textos de cada marco da PLT-02, com a marca Giro (a assinatura é do Giro com a
    empresa), fixados pelo produto na T-299. Sempre "da empresa {nome}", porque o nome pode ser
    masculino. Português, frases curtas, sem exclamação."""
    empresa = fatura.empresa
    nome = empresa.nome_exibicao
    valor = formatar_reais(int(fatura.valor_centavos))
    vence = dia_e_mes(fatura.vencimento)
    suspende = dia_e_mes(fatura.vencimento + timedelta(days=DIAS_ATE_SUSPENDER))
    resumo = f"A fatura {fatura.codigo} da empresa {nome}, de {valor}"
    if marco == "D-3":
        assunto = f"Giro: a fatura {fatura.codigo} vence em {vence}"
        inicio = f"{resumo}, vence em {vence}."
    elif marco == "D0":
        assunto = f"Giro: a fatura {fatura.codigo} vence hoje"
        inicio = f"{resumo}, vence hoje."
    elif marco == "D+3":
        assunto = f"Giro: a fatura {fatura.codigo} está em atraso"
        inicio = (
            f"{resumo}, venceu em {vence} e ainda não foi paga. "
            f"Sem o pagamento, em {suspende} {SUSPENSA}."
        )
    else:
        assunto = f"Giro: a empresa {nome} fica suspensa em {suspende}"
        inicio = (
            f"{resumo}, venceu em {vence} e ainda não foi paga. "
            f"Em {suspende}, {SUSPENSA}. Pagando, o acesso volta na hora."
        )
        if empresa.responsavel_telefone:  # sem telefone, ninguém vai ligar
            inicio += " A equipe Giro vai ligar para o responsável pela assinatura."
    automatica = marco in ("D-3", "D0") and _automatica_sem_falha(fatura, forma)
    rodape = NADA_A_FAZER if automatica else SE_JA_PAGOU
    texto = (
        f"{inicio}\n{_como_pagar(fatura, forma)}\n"
        f"Assinatura: {endereco_da_assinatura(empresa)}\n{rodape}"
    )
    whatsapp = (
        f"Giro: {inicio[0].lower()}{inicio[1:]} "
        f"{_como_pagar(fatura, forma, whatsapp=True)} {rodape}"
    )
    return MensagemDaRegua(assunto, texto, whatsapp)


def _pedir_ligacao(fatura: FaturaAssinatura) -> Email:
    """D+7 (PLT-02): a tarefa de ligação para a equipe Giro. Sem a tela (fase 2,
    `Plat-Cobranca`), vai por e-mail ao Dono e ao Financeiro da plataforma e fica na auditoria
    do public. Grava o evento e devolve o e-mail, que sai depois do commit."""
    from django.contrib.auth import get_user_model

    empresa = fatura.empresa
    registrar_evento(
        "fatura_assinatura.pedir_ligacao",
        Categoria.FINANCEIRO,
        objeto=fatura,
        depois={"empresa": empresa.pk},
        regra="PLT-02",
    )
    equipe = list(
        get_user_model()
        .objects.filter(funcao_plataforma__in=FUNCOES_QUE_LIGAM, status="ativo")
        .order_by("pk")
        .values_list("email", flat=True)
    )
    suspende = dia_e_mes(fatura.vencimento + timedelta(days=DIAS_ATE_SUSPENDER))
    return Email(
        equipe,
        f"Ligação de cobrança: {empresa.nome_exibicao}, {fatura.codigo} com 7 dias de atraso",
        f"A fatura {fatura.codigo} da empresa {empresa.nome_exibicao}, de "
        f"{formatar_reais(int(fatura.valor_centavos))}, venceu em "
        f"{dia_e_mes(fatura.vencimento)} e ainda não foi paga. A suspensão é em {suspende}.\n"
        f"Responsável: {empresa.responsavel_nome or 'nome não cadastrado'}, "
        f"{empresa.responsavel_telefone or 'celular não cadastrado'}.\n"
        f"E-mail de cobrança: {empresa.email_cobranca or 'não cadastrado'}.",
    )


def _enviar_sem_parar(fatura_id: int, canal: str, envio: Callable[[], Any]) -> None:
    """Uma falha num canal não para os outros. O log leva só a fatura, o canal e o tipo do
    erro, nunca o corpo da mensagem (M-02 da T-304)."""
    try:
        envio()
    except Exception as erro:  # o envio de um canal não derruba o resto
        logger.warning(
            "Régua da fatura %s: o envio por %s falhou (%s)",
            fatura_id,
            canal,
            type(erro).__name__,
        )


def avisar_pela_regua(fatura_id: int, hoje: date) -> str | None:
    """O marco de hoje desta fatura, uma vez só (o evento `fatura_assinatura.regua` é a marca).
    Um e-mail para o `email_cobranca` e um para cada administrador; no D0 e no D+3, também
    WhatsApp ao responsável; no D+7, a tarefa de ligação. Fatura paga ou cancelada, ou empresa
    `cancelada`: nada (PLT-06). Devolve o marco avisado.

    As mensagens saem depois do commit do evento, fora da transação com a fatura travada: uma
    falha no envio não desfaz o aviso, e uma nova execução não repete o e-mail (M-02 da T-304)."""
    from integracoes.whatsapp import enviar_whatsapp

    with schema_context(get_public_schema_name()):
        with transaction.atomic():
            fatura = (
                FaturaAssinatura.objects.select_for_update(of=("self",))
                .select_related("empresa")
                .get(pk=fatura_id)
            )
            marco = _marco_do_dia(fatura.vencimento, hoje)
            if (
                marco is None
                or fatura.status not in EM_ABERTO
                or fatura.empresa.status == Empresa.Status.CANCELADA
                or _ja_avisada(fatura, marco)
            ):
                return None
            forma = FormaPagamentoAssinatura.objects.filter(empresa_id=fatura.empresa_id).first()
            mensagem = mensagem_da_regua(fatura, marco, forma)
            aviso = Email(
                destinatarios_da_cobranca(fatura.empresa), mensagem.assunto, mensagem.texto
            )
            celular = fatura.empresa.responsavel_telefone if marco in MARCOS_COM_WHATSAPP else ""
            with usar_ator(ATOR_SISTEMA):
                registrar_evento(
                    "fatura_assinatura.regua",
                    Categoria.FINANCEIRO,
                    objeto=fatura,
                    depois={"marco": marco, "whatsapp": bool(celular)},
                    regra="AUT-13",
                )
                ligacao = _pedir_ligacao(fatura) if marco == "D+7" else None
        _enviar_sem_parar(
            fatura_id,
            "e-mail",
            partial(enviar_a_cada_um, aviso.destinatarios, aviso.assunto, aviso.texto),
        )
        if celular:
            _enviar_sem_parar(
                fatura_id, "WhatsApp", partial(enviar_whatsapp, celular, mensagem.whatsapp)
            )
        if ligacao is not None:
            _enviar_sem_parar(
                fatura_id,
                "e-mail da ligação",
                partial(enviar_a_cada_um, ligacao.destinatarios, ligacao.assunto, ligacao.texto),
            )
    return marco


def regua_da_assinatura(hoje: date | None = None) -> dict[str, int]:
    """AUT-13, às 09:00 (PLT-02): D-3 lembrete por e-mail; D0 e D+3 e-mail e WhatsApp; D+7 aviso
    de suspensão por e-mail e a tarefa de ligação. No dia exato de cada marco, como a AUT-03;
    só o D+7 perdido sai depois, até o D+14 (CA-ASS-68). Idempotente no mesmo dia. Cada fatura
    isolada: a falha de uma vai ao log, sem o corpo, e as outras seguem (M-02 da T-304).
    Devolve quantas faturas por marco."""
    dia = hoje or relogio.hoje()
    vencimentos = [dia - timedelta(days=dias) for dias in MARCOS_DA_REGUA]
    d7_perdido = (dia - timedelta(days=ULTIMO_DIA_DO_D7), dia - timedelta(days=8))
    with schema_context(get_public_schema_name()):
        faturas = list(
            FaturaAssinatura.objects.filter(status__in=EM_ABERTO)
            .filter(Q(vencimento__in=vencimentos) | Q(vencimento__range=d7_perdido))
            .exclude(empresa__status=Empresa.Status.CANCELADA)
            .order_by("vencimento", "pk")
            .values_list("pk", flat=True)
        )
        avisos: dict[str, int] = {}
        for pk in faturas:
            try:
                marco = avisar_pela_regua(pk, dia)
            except Exception as erro:  # uma fatura não para a régua do dia
                logger.warning(
                    "Régua da fatura %s: fica sem aviso nesta rodada (%s)", pk, type(erro).__name__
                )
                continue
            _contar(avisos, marco)
    return avisos


# --- Cancelar e pausar (PLT-06; T-195, cancelamento.md) ---

JA_CANCELADA = "A assinatura já está cancelada. Você tem acesso até {}."
SEM_CANCELAMENTO = ("transicao_empresa", "Não há cancelamento para desfazer.")
NOME_NAO_CONFERE = ("nome_nao_confere", "O nome digitado não confere com o nome da empresa.")
# T-199, M-01: o 403 de `auditoria.md`, com o texto do cancelamento.
CANCELAR_PEDE_2_ETAPAS = (
    "2fa_recente",
    "Confirme o código do autenticador para cancelar a assinatura.",
)
PAUSA_SO_NA_ATIVA = (
    "transicao_empresa",
    "A pausa só vale para a assinatura ativa. No teste, você pode cancelar ou mudar de plano.",
)
PAGUE_ANTES_DE_PAUSAR = ("transicao_empresa", "Pague a fatura em atraso antes de pausar.")
DESFACA_ANTES_DE_PAUSAR = ("transicao_empresa", "Desfaça o cancelamento antes de pausar.")
SEM_PAUSA = ("transicao_empresa", "Não há pausa para encerrar.")
POR_SISTEMA = "sistema"  # a virada do dia
STATUS_QUE_CANCELAM = frozenset(
    {
        Empresa.Status.EM_TESTE,
        Empresa.Status.ATIVA,
        Empresa.Status.INADIMPLENTE,
        Empresa.Status.SUSPENSA,
        Empresa.Status.PAUSADA,
    }
)
# A pausa agendada vira `pausada` na `ativa` e na `inadimplente` pela diferença do upgrade.
STATUS_QUE_COMECAM_A_PAUSA = frozenset({Empresa.Status.ATIVA, Empresa.Status.INADIMPLENTE})


def pausa_marcada(empresa: Empresa) -> bool:
    """Agendada enquanto `ativa`, em andamento quando `pausada` (`cancelamento.md`)."""
    return empresa.pausa_inicio is not None


def fim_do_periodo_pago(empresa: Empresa) -> date | None:
    """O maior `periodo_fim` das mensalidades pagas (a véspera do próximo vencimento), ou nulo."""
    fim: date | None = (
        _mensalidades(empresa)
        .filter(status=StatusFatura.PAGA)
        .aggregate(fim=models.Max("periodo_fim"))["fim"]
    )
    return fim


def datas_de_cancelar(empresa: Empresa, hoje: date) -> DatasDoCancelamento:
    """As datas se a empresa cancelar hoje: a mesma conta da tela e do `POST` (PLT-06)."""
    return datas_do_cancelamento(
        hoje, empresa.status, empresa.teste_fim, fim_do_periodo_pago(empresa)
    )


def dia_do_acesso(empresa: Empresa, acesso_ate: date) -> str:
    """ "21 nov"; no anual pago, com o ano ("21 out 2027", PLT-14). No fim do teste, sem ano."""
    anual_pago = empresa.ciclo == Empresa.Ciclo.ANUAL and acesso_ate != empresa.teste_fim
    return dia_mes_e_ano(acesso_ate) if anual_pago else dia_e_mes(acesso_ate)


def ja_cancelada(empresa: Empresa) -> Conflito:
    """409 do cancelamento marcado: "A assinatura já está cancelada. Você tem acesso até ..."."""
    acesso = dia_do_acesso(empresa, empresa.acesso_ate) if empresa.acesso_ate else ""
    return Conflito("transicao_empresa", JA_CANCELADA.format(acesso))


def nome_confere(digitado: str, nome: str) -> bool:
    """PLT-06, CA-ASS-31: sem espaços nas pontas nem repetidos, sem diferença de maiúsculas e
    minúsculas; os acentos contam ("Moto Rapida" não confere com "Moto Rápida")."""

    def normalizar(texto: str) -> str:
        return " ".join(texto.split()).casefold()

    return bool(normalizar(nome)) and normalizar(digitado) == normalizar(nome)


def _cancelar_fatura(fatura: FaturaAssinatura, motivo: str, agora: Any) -> bool:
    """A fatura em aberto vira `cancelada`, com a cobrança cancelada no parceiro. Se o parceiro diz
    que ela já foi paga, fica como está (a baixa segue pelo webhook) e devolve `False`."""
    if not _cancelar_cobranca_viva(fatura):
        return False
    fatura.motivo_cancelamento = motivo
    fatura.cancelada_em = agora
    transicionar(
        fatura,
        StatusFatura.CANCELADA,
        acao="fatura_assinatura.cancelar",
        regra="PLT-06",
        mais_campos=("motivo_cancelamento", "cancelada_em"),
    )
    return True


def _cancelar_mensalidades(
    empresa: Empresa, motivo: str, agora: Any, desde: date | None = None
) -> list[str]:
    """As mensalidades `aberta` (cujo período começa em `desde` ou depois) viram `cancelada`.
    As `atrasada` e as diferenças do upgrade continuam devidas (PLT-06). Devolve os códigos."""
    abertas = _abertas_a_partir_de(empresa, desde or date.min)
    return [f.codigo for f in abertas if _cancelar_fatura(f, motivo, agora)]


def _renascer(fatura: FaturaAssinatura, hoje: date) -> FaturaAssinatura:
    """A fatura cancelada pelo cancelamento ou pela pausa nasce de novo, igual, `aberta`, com o
    próximo código; a cancelada aponta para ela. A cobrança sai como na emissão (PLT-02): com
    vencimento em até 5 dias, na hora; mais longe, a `gerar_faturas` emite 5 dias antes."""
    nova = criar_fatura(
        fatura.empresa,
        tipo=fatura.tipo,
        vencimento=fatura.vencimento,
        periodo=Periodo(fatura.periodo_inicio, fatura.periodo_fim),
        plano=fatura.plano,
        ciclo=fatura.ciclo,
        valor_centavos=int(fatura.valor_centavos),
        regra="PLT-06",
    )
    with auditar(fatura, "fatura_assinatura.substituir", Categoria.FINANCEIRO, regra="PLT-06"):
        fatura.substituida_por = nova
        fatura.save(update_fields=["substituida_por", "atualizado_em"])
    if nova.vencimento <= hoje + timedelta(days=DIAS_DE_ANTECEDENCIA):
        emitir_cobranca_da_fatura(nova.pk, hoje)
    return nova


def _renascer_canceladas(
    empresa: Empresa, motivo: str, hoje: date, **filtros: Any
) -> list[FaturaAssinatura]:
    canceladas = (
        FaturaAssinatura.objects.select_for_update(of=("self",))
        .select_related("empresa", "plano")
        .filter(
            empresa_id=empresa.pk,
            status=StatusFatura.CANCELADA,
            motivo_cancelamento=motivo,
            substituida_por__isnull=True,
            **filtros,
        )
        .order_by("vencimento", "numero")
    )
    return [_renascer(fatura, hoje) for fatura in canceladas]


def _tornar_cancelada(empresa: Empresa, agora: Any, hoje: date) -> list[str]:
    """`status` → `cancelada` (AUD-08: apagamento em hoje + 90 dias). As mensalidades ainda
    `aberta` viram `cancelada`; a pausa acaba. Depois do commit, a forma de pagamento sai do
    parceiro (ADR 0023). A `Empresa` vem travada."""
    canceladas = _cancelar_mensalidades(
        empresa, MotivoCancelamentoFatura.CANCELAMENTO_ASSINATURA, agora
    )
    empresa.cancelada_em = agora
    empresa.apagar_em = hoje + timedelta(days=DIAS_ATE_APAGAR)
    empresa.pausa_inicio = None
    empresa.pausada_ate = None
    empresa.save(
        update_fields=["cancelada_em", "apagar_em", "pausa_inicio", "pausada_ate", "atualizado_em"]
    )
    transicionar_empresa(empresa, Empresa.Status.CANCELADA, regra="PLT-06")
    from .tasks import plataforma_encerrar_forma_pagamento

    empresa_id = empresa.pk
    transaction.on_commit(lambda: plataforma_encerrar_forma_pagamento.delay(empresa_id))
    return canceladas


def _iso(valor: date | None) -> str | None:
    return valor.isoformat() if valor is not None else None


def cancelar_assinatura(
    empresa: Empresa,
    motivo: str,
    por: str = POR_ADMINISTRADOR,
    *,
    nome_confirmacao: str | None = None,
) -> Empresa:
    """PLT-06 (`cancelamento.md`, "O que acontece em cada estado"):

    - `em_teste` e `ativa`: cancelamento marcado, com acesso até o fim do teste ou do período
      pago; a mensalidade do período seguinte, se já gerada e não paga, vira `cancelada`. O
      `status` não muda até a virada do dia seguinte a `acesso_ate` (`virar_cancelada`).
    - `inadimplente`, `suspensa` e `pausada`: `cancelada` na hora; as `atrasada` continuam
      devidas, as mensalidades `aberta` viram `cancelada` e a régua para.

    A pausa marcada acaba. Os contratos com clientes finais não mudam (CA-ASS-39). Com a
    `Empresa` travada; `nome_confirmacao` diferente do nome: 422, e nada muda."""
    if motivo not in MotivoCancelamento.values:
        raise ErroDeValidacao({"motivo": ["Escolha o motivo."]})
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        if cancelamento_marcado(empresa):
            raise ja_cancelada(empresa)
        if empresa.status not in STATUS_QUE_CANCELAM:
            raise Conflito("transicao_empresa", "Esta assinatura já foi cancelada.")
        if nome_confirmacao is not None and not nome_confere(
            nome_confirmacao, empresa.nome_exibicao
        ):
            raise ErroDeRegra(*NOME_NAO_CONFERE)
        hoje, agora = relogio.hoje(), relogio.agora()
        datas = datas_de_cancelar(empresa, hoje)
        antes = {
            "status": empresa.status,
            "pausa_inicio": _iso(empresa.pausa_inicio),
            "pausada_ate": _iso(empresa.pausada_ate),
        }
        empresa.cancelamento_pedido_em = agora
        empresa.motivo_cancelamento = motivo
        empresa.acesso_ate = datas.acesso_ate
        empresa.apagar_em = datas.apagar_em
        empresa.pausa_inicio = None
        empresa.pausada_ate = None
        empresa.save(
            update_fields=[
                "cancelamento_pedido_em",
                "motivo_cancelamento",
                "acesso_ate",
                "apagar_em",
                "pausa_inicio",
                "pausada_ate",
                "atualizado_em",
            ]
        )
        if datas.acesso_ate is None:
            canceladas = _tornar_cancelada(empresa, agora, hoje)
        else:
            canceladas = _cancelar_mensalidades(
                empresa,
                MotivoCancelamentoFatura.CANCELAMENTO_ASSINATURA,
                agora,
                desde=datas.acesso_ate + timedelta(days=1),
            )
        _registrar_nos_dois(
            empresa,
            "empresa.cancelar",
            antes=antes,
            depois={
                "motivo": motivo,
                "acesso_ate": _iso(datas.acesso_ate),
                "apagar_em": _iso(datas.apagar_em),
                "faturas_canceladas": canceladas,
                "por": por,
            },
            categoria_publica=Categoria.FINANCEIRO,
            regra="PLT-06",
        )
    return empresa


def desfazer_cancelamento(empresa: Empresa, por: str = POR_ADMINISTRADOR) -> Empresa:
    """PLT-06 (CA-ASS-43 a 45): só com cancelamento marcado e até o último dia de acesso. Limpa o
    cancelamento; `status`, `dia_vencimento`, plano e forma não mudam. Cada fatura que este
    cancelamento cancelou nasce de novo (`_renascer`); se não cancelou nada, a `gerar_faturas`
    gera no dia certo."""
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        hoje = relogio.hoje()
        if (
            not cancelamento_marcado(empresa)
            or empresa.acesso_ate is None
            or hoje > empresa.acesso_ate
        ):
            raise Conflito(*SEM_CANCELAMENTO)
        pedido_em = empresa.cancelamento_pedido_em
        antes = {
            "motivo": empresa.motivo_cancelamento,
            "acesso_ate": _iso(empresa.acesso_ate),
            "apagar_em": _iso(empresa.apagar_em),
        }
        empresa.cancelamento_pedido_em = None
        empresa.motivo_cancelamento = ""
        empresa.acesso_ate = None
        empresa.apagar_em = None
        empresa.save(
            update_fields=[
                "cancelamento_pedido_em",
                "motivo_cancelamento",
                "acesso_ate",
                "apagar_em",
                "atualizado_em",
            ]
        )
        filtros = {"cancelada_em__gte": pedido_em} if pedido_em else {}
        novas = _renascer_canceladas(
            empresa, MotivoCancelamentoFatura.CANCELAMENTO_ASSINATURA, hoje, **filtros
        )
        _registrar_nos_dois(
            empresa,
            "empresa.desfazer_cancelamento",
            antes=antes,
            depois={"faturas_novas": [f.codigo for f in novas], "por": por},
            categoria_publica=Categoria.FINANCEIRO,
            regra="PLT-06",
        )
    return empresa


def _conferir_pausa(empresa: Empresa) -> None:
    """Só a `ativa`, sem cancelamento nem pausa marcados (PLT-06, CA-ASS-37, CA-ASS-56)."""
    if empresa.status == Empresa.Status.EM_TESTE:
        raise Conflito(*PAUSA_SO_NA_ATIVA)
    if empresa.status in (Empresa.Status.INADIMPLENTE, Empresa.Status.SUSPENSA):
        raise Conflito(*PAGUE_ANTES_DE_PAUSAR)
    if cancelamento_marcado(empresa):
        raise Conflito(*DESFACA_ANTES_DE_PAUSAR)
    if pausa_marcada(empresa):
        ate = dia_e_mes(empresa.pausada_ate) if empresa.pausada_ate else ""
        raise Conflito("transicao_empresa", f"Já existe uma pausa marcada até {ate}.")
    if empresa.status != Empresa.Status.ATIVA:
        raise Conflito(*PAUSA_SO_NA_ATIVA)


def pausar_assinatura(empresa: Empresa, meses: int, por: str = POR_ADMINISTRADOR) -> Empresa:
    """PLT-06 (CA-ASS-35, 37, 42): a pausa começa no fim do período pago (decisão de 14 out 2026)
    e dura de 1 a 3 meses. Até `pausa_inicio`, a empresa segue `ativa`. A mensalidade do período
    da pausa, se já gerada e não paga, vira `cancelada` (motivo `pausa`)."""
    if meses not in MESES_DE_PAUSA:
        raise ErroDeValidacao({"meses": ["Escolha de 1 a 3 meses."]})
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        _conferir_pausa(empresa)
        fim = fim_do_periodo_pago(empresa)
        if fim is None:
            raise Conflito(*PAUSA_SO_NA_ATIVA)
        periodo = periodo_da_pausa(fim + timedelta(days=1), meses)
        empresa.pausa_inicio = periodo.inicio
        empresa.pausada_ate = periodo.fim
        empresa.save(update_fields=["pausa_inicio", "pausada_ate", "atualizado_em"])
        canceladas = _cancelar_mensalidades(
            empresa, MotivoCancelamentoFatura.PAUSA, relogio.agora(), desde=periodo.inicio
        )
        _registrar_nos_dois(
            empresa,
            "empresa.pausar",
            antes={"pausa_inicio": None, "pausada_ate": None},
            depois={
                "meses": meses,
                "pausa_inicio": _iso(periodo.inicio),
                "pausada_ate": _iso(periodo.fim),
                "faturas_canceladas": canceladas,
                "por": por,
            },
            categoria_publica=Categoria.FINANCEIRO,
            regra="PLT-06",
        )
    return empresa


def desistir_da_pausa(empresa: Empresa, por: str = POR_ADMINISTRADOR) -> Empresa:
    """PLT-06 (CA-ASS-55): a pausa agendada é desfeita até o último dia do período pago (a véspera
    de `pausa_inicio`). A fatura que a pausa cancelou nasce de novo, como no desfazer do
    cancelamento. `status`, plano, `plano_proximo` e `dia_vencimento` não mudam."""
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        hoje = relogio.hoje()
        inicio = empresa.pausa_inicio
        if empresa.status == Empresa.Status.PAUSADA or inicio is None or hoje >= inicio:
            raise Conflito(*SEM_PAUSA)
        antes = {"pausa_inicio": _iso(inicio), "pausada_ate": _iso(empresa.pausada_ate)}
        empresa.pausa_inicio = None
        empresa.pausada_ate = None
        empresa.save(update_fields=["pausa_inicio", "pausada_ate", "atualizado_em"])
        novas = _renascer_canceladas(
            empresa, MotivoCancelamentoFatura.PAUSA, hoje, periodo_inicio__gte=inicio
        )
        _registrar_nos_dois(
            empresa,
            "empresa.desistir_pausa",
            antes=antes,
            depois={
                "pausa_inicio": None,
                "pausada_ate": None,
                "faturas_novas": [f.codigo for f in novas],
                "por": por,
            },
            categoria_publica=Categoria.FINANCEIRO,
            regra="PLT-06",
        )
    return empresa


def _fatura_da_volta(empresa: Empresa, hoje: date) -> FaturaAssinatura:
    """A mensalidade da volta, vencendo hoje, pelo que vale na virada. Com o downgrade agendado,
    é a "próxima fatura" dele: passa pela conferência e, cabendo, sai pelo plano menor (PLT-04)."""
    agendado = empresa.plano_proximo
    if agendado is not None and agendado.pk != empresa.plano_id:
        uso = UsoEmpresa.objects.select_for_update().filter(empresa_id=empresa.pk).first()
        excede = excede_no_plano(empresa, agendado, uso or UsoEmpresa(empresa=empresa))
        if excede:
            _recusar_downgrade_agendado(empresa, agendado, excede, hoje)
    plano, ciclo, valor = _o_que_vale_na_virada(empresa)
    return criar_fatura(
        empresa,
        tipo=TipoFatura.MENSALIDADE,
        vencimento=hoje,
        periodo=proximo_periodo(hoje.day, ciclo, hoje),
        plano=plano,
        ciclo=ciclo,
        valor_centavos=valor,
        regra="PLT-06",
    )


def voltar_da_pausa(empresa: Empresa, por: str = POR_ADMINISTRADOR) -> Empresa:
    """PLT-06 (CA-ASS-36, CA-ASS-57): a `pausada` volta na hora (pelo administrador) ou no dia
    seguinte a `pausada_ate` (pela virada, `por=POR_SISTEMA`). `ativa`, ou `inadimplente` se a
    diferença do upgrade ainda estiver atrasada; a mensalidade nova vence hoje, e o dia de
    vencimento passa a ser o de hoje (PLT-01). A cobrança sai na hora, pela forma cadastrada."""
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        if empresa.status != Empresa.Status.PAUSADA:
            raise Conflito(*SEM_PAUSA)
        hoje = relogio.hoje()
        antes = {
            "pausa_inicio": _iso(empresa.pausa_inicio),
            "pausada_ate": _iso(empresa.pausada_ate),
            "dia_vencimento": empresa.dia_vencimento,
        }
        empresa.pausa_inicio = None
        empresa.pausada_ate = None
        empresa.dia_vencimento = hoje.day
        empresa.save(
            update_fields=["pausa_inicio", "pausada_ate", "dia_vencimento", "atualizado_em"]
        )
        atrasada = _atrasada_mais_antiga(empresa)
        novo = Empresa.Status.INADIMPLENTE if atrasada else Empresa.Status.ATIVA
        transicionar_empresa(empresa, novo, regra="PLT-06")
        fatura = _fatura_da_volta(empresa, hoje)
        _registrar_nos_dois(
            empresa,
            "empresa.voltar_pausa",
            antes=antes,
            depois={
                "pausa_inicio": None,
                "pausada_ate": None,
                "dia_vencimento": hoje.day,
                "fatura": fatura.codigo,
                "por": por,
            },
            categoria_publica=Categoria.FINANCEIRO,
            regra="PLT-06",
        )
        if empresa.plano_proximo_id is not None:
            aplicar_mudanca_agendada(empresa.pk, hoje)  # o downgrade vale já na volta
        if emitir_cobranca_da_fatura(fatura.pk, hoje) == "cartao_guardado":
            from .tasks import plataforma_cobrar_cartao

            fatura_id = fatura.pk
            transaction.on_commit(lambda: plataforma_cobrar_cartao.delay(fatura_id))
    return empresa


# --- Reativar a cancelada (PLT-06, AUD-08; assinatura.md, "Mudança de ciclo e reativação") ---

SO_A_CANCELADA = ("transicao_empresa", "Só a empresa cancelada pode ser reativada.")
APAGAMENTO_COMECOU = (
    "transicao_empresa",
    "O apagamento dos dados desta empresa já começou. Não dá para reativar.",
)
DADOS_JA_APAGADOS = ("transicao_empresa", "Os dados desta empresa já foram apagados.")
RECEBA_A_ATRASADA = ("fatura_em_atraso", "Receba a fatura em atraso antes de reativar.")


def reativar_empresa(empresa: Empresa, por: str = POR_EQUIPE, motivo: str = "") -> Empresa:
    """PLT-06 (CA-ASS-46, CA-ASS-49): a equipe Giro reativa a `cancelada` nos 90 dias, e ela
    volta a `ativa` na hora, sem o cancelamento, o apagamento marcado e o aviso dele.

    - Recusada: sem motivo (400); fora da `cancelada`; no dia do apagamento ou depois, já que a
      `aud_08_apagar_empresas` pode ter começado (T-199, B-02, `apagar_empresa` trava a
      `Empresa` antes dos arquivos); com fatura `atrasada` de antes do cancelamento (409
      `fatura_em_atraso`, opção A de 14 out 2026). Nada muda.
    - A mensalidade nova, pelo plano, ciclo e preço contratado atuais, vence no dia seguinte ao
      fim do período pago, se ele ainda corre (o dia de vencimento não muda), ou hoje (o dia
      passa a ser o de hoje): `vencimento_da_reativacao`. A forma de pagamento saiu com o
      cancelamento, então a fatura nasce sem forma, e o administrador escolhe ao entrar (PLT-13).
    - Auditoria `empresa.reativar` nos dois lugares, com o motivo e quem fez."""
    motivo = motivo.strip()
    if not motivo:
        raise ErroDeValidacao({"motivo": ["Informe o motivo."]})
    with no_publico(), transaction.atomic():
        empresa = _empresa_travada(empresa)
        hoje = relogio.hoje()
        if empresa.status != Empresa.Status.CANCELADA:
            raise Conflito(*SO_A_CANCELADA)
        if empresa.apagada_em is not None:
            raise Conflito(*DADOS_JA_APAGADOS)
        if empresa.apagar_em is None or empresa.apagar_em <= hoje:
            raise Conflito(*APAGAMENTO_COMECOU)
        if _atrasada_mais_antiga(empresa) is not None:
            raise Conflito(*RECEBA_A_ATRASADA)
        if empresa.plano is None:
            raise ValueError("Empresa sem plano.")
        vencimento, dia = vencimento_da_reativacao(
            hoje, fim_do_periodo_pago(empresa), empresa.dia_vencimento or hoje.day
        )
        antes = {
            "status": empresa.status,
            "cancelada_em": _iso(empresa.cancelada_em.date() if empresa.cancelada_em else None),
            "apagar_em": _iso(empresa.apagar_em),
            "dia_vencimento": empresa.dia_vencimento,
        }
        empresa.cancelamento_pedido_em = None
        empresa.motivo_cancelamento = ""
        empresa.acesso_ate = None
        empresa.cancelada_em = None
        empresa.apagar_em = None
        empresa.aviso_apagamento_enviado_em = None
        empresa.dia_vencimento = dia
        empresa.save(
            update_fields=[
                "cancelamento_pedido_em",
                "motivo_cancelamento",
                "acesso_ate",
                "cancelada_em",
                "apagar_em",
                "aviso_apagamento_enviado_em",
                "dia_vencimento",
                "atualizado_em",
            ]
        )
        transicionar_empresa(empresa, Empresa.Status.ATIVA, regra="PLT-06", motivo=motivo)
        fatura = criar_fatura(
            empresa,
            tipo=TipoFatura.MENSALIDADE,
            vencimento=vencimento,
            periodo=proximo_periodo(dia, empresa.ciclo, vencimento),
            plano=empresa.plano,
            ciclo=empresa.ciclo,
            valor_centavos=int(empresa.preco_contratado_centavos),
            regra="PLT-06",
        )
        _registrar_nos_dois(
            empresa,
            "empresa.reativar",
            antes=antes,
            depois={"dia_vencimento": dia, "fatura": fatura.codigo, "por": por},
            categoria_publica=Categoria.FINANCEIRO,
            motivo=motivo,
            regra="PLT-06",
        )
        if vencimento <= hoje + timedelta(days=DIAS_DE_ANTECEDENCIA):
            emitir_cobranca_da_fatura(fatura.pk, hoje)  # sem forma, fica para o "Pagar"
    return empresa


def _autorizacao_ja_encerrada(autorizacao: str) -> bool:
    """Depois de uma recusa: a autorização inexistente ou já cancelada conta como encerrada
    (T-199, M-03). O 404 a interface já devolve como `cancelada`."""
    try:
        consulta = provedor().consultar_autorizacao(conta_principal(), autorizacao)
    except (ParceiroIndisponivel, ParceiroRecusou):
        return False
    return consulta.status == "cancelada"


def encerrar_forma_pagamento(empresa_id: int) -> str:
    """ADR 0023 (`cancelamento.md`, `virar_cancelada`): o Giro não guarda meio de pagamento de quem
    saiu. A autorização do Pix automático é cancelada no parceiro, o token do cartão é esquecido
    e a `forma` fica nula. Idempotente.

    T-199, M-03: o cartão sai sempre, mesmo com o parceiro fora do ar ou recusando. A autorização
    inexistente ou já cancelada conta como encerrada. Outra recusa fica no log de erro, com a
    autorização guardada (`parceiro_recusou`). Fora do ar: grava o resto e levanta
    `ParceiroForaDoAr` depois do commit, para a tarefa tentar de novo. A empresa reativada antes
    de a tarefa terminar fica com a forma que tiver (T-365)."""
    fora_do_ar = False
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = _empresa_travada(Empresa(pk=empresa_id))
        if empresa.status != Empresa.Status.CANCELADA:
            return "reativada"
        forma = (
            FormaPagamentoAssinatura.objects.select_for_update()
            .filter(empresa_id=empresa_id)
            .first()
        )
        if forma is None or (
            not forma.forma and not forma.autorizacao_externa_id and not forma.cartao_final
        ):
            return "sem_forma"
        autorizacao = forma.autorizacao_externa_id
        encerrou = True
        if autorizacao:
            try:
                provedor().cancelar_autorizacao(conta_principal(), autorizacao)
            except ParceiroIndisponivel:
                fora_do_ar, encerrou = True, False
            except ParceiroRecusou:
                encerrou = _autorizacao_ja_encerrada(autorizacao)
                if not encerrou:
                    logger.error(
                        "Fim da forma da empresa %s: o parceiro recusou cancelar a autorização",
                        empresa_id,
                    )
        with (
            usar_ator(ATOR_SISTEMA),
            auditar(forma, "assinatura.forma_encerrada", Categoria.FINANCEIRO, regra="PLT-06"),
        ):
            campos = ["forma", *_esquecer_cartao(forma)]
            forma.forma = ""
            if encerrou:
                forma.autorizacao_externa_id = ""
                campos.append("autorizacao_externa_id")
            forma.save(update_fields=[*campos, "atualizado_em"])
    if fora_do_ar:
        raise ParceiroForaDoAr(*PARCEIRO_FORA_DO_AR)
    return "encerrada" if encerrou else "parceiro_recusou"


# Virada do dia (cancelamento.md, "Tarefas e estados")


def virar_cancelada(empresa_id: int, hoje: date) -> bool:
    """O cancelamento marcado vira `cancelada` no dia seguinte a `acesso_ate` (PLT-06; AUD-08:
    apagamento em hoje + 90 dias). Idempotente."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = _empresa_travada(Empresa(pk=empresa_id))
        if not cancelamento_marcado(empresa) or empresa.acesso_ate is None:
            return False
        if hoje <= empresa.acesso_ate:
            return False
        with usar_ator(ATOR_SISTEMA):
            canceladas = _tornar_cancelada(empresa, relogio.agora(), hoje)
            _registrar_nos_dois(
                empresa,
                "empresa.virar_cancelada",
                antes={"acesso_ate": _iso(empresa.acesso_ate)},
                depois={
                    "cancelada_em": hoje.isoformat(),
                    "apagar_em": _iso(empresa.apagar_em),
                    "faturas_canceladas": canceladas,
                },
                categoria_publica=Categoria.FINANCEIRO,
                regra="PLT-06",
            )
    return True


def iniciar_pausa(empresa_id: int, hoje: date) -> bool:
    """A pausa agendada começa em `pausa_inicio`: a empresa fica `pausada` (somente leitura) até
    `pausada_ate`. Uma mensalidade do período da pausa que ainda esteja `aberta` vira
    `cancelada`. Idempotente."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = _empresa_travada(Empresa(pk=empresa_id))
        inicio = empresa.pausa_inicio
        if empresa.status not in STATUS_QUE_COMECAM_A_PAUSA or inicio is None or hoje < inicio:
            return False
        with usar_ator(ATOR_SISTEMA):
            _cancelar_mensalidades(empresa, MotivoCancelamentoFatura.PAUSA, relogio.agora(), inicio)
            transicionar_empresa(empresa, Empresa.Status.PAUSADA, regra="PLT-06")
    return True


def _virar_cancelamentos_e_pausas(hoje: date, estados: dict[str, int]) -> None:
    """Antes das transições de `assinatura.md`: o cancelamento primeiro, para a `em_teste`
    cancelada não ir a `suspensa`; depois o começo e a volta das pausas."""
    marcados = list(
        Empresa.objects.filter(acesso_ate__lt=hoje)
        .exclude(status=Empresa.Status.CANCELADA)
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    for pk in marcados:
        if _cada_uma(f"Cancelamento da empresa {pk}", partial(virar_cancelada, pk, hoje)):
            _contar(estados, Empresa.Status.CANCELADA)
    agendadas = list(
        Empresa.objects.filter(pausa_inicio__lte=hoje, status__in=STATUS_QUE_COMECAM_A_PAUSA)
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    for pk in agendadas:
        if _cada_uma(f"Pausa da empresa {pk}", partial(iniciar_pausa, pk, hoje)):
            _contar(estados, Empresa.Status.PAUSADA)
    voltam = list(
        Empresa.objects.filter(status=Empresa.Status.PAUSADA, pausada_ate__lt=hoje)
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    for pk in voltam:
        with usar_ator(ATOR_SISTEMA):
            voltou = _cada_uma(
                f"Volta da pausa da empresa {pk}",
                partial(voltar_da_pausa, Empresa(pk=pk), POR_SISTEMA),
            )
        if voltou is not None:
            _contar(estados, str(voltou.status))


# --- Aviso e apagamento da empresa cancelada (AUD-08; ADR 0025, cancelamento.md) ---


def _administradores_ativos(empresa: Empresa) -> list[str]:
    from django.contrib.auth import get_user_model

    with no_schema_da_empresa(empresa):
        return list(
            get_user_model()
            .objects.filter(perfil="administrador", status="ativo")
            .order_by("pk")
            .values_list("email", flat=True)
        )


def avisar_apagamento(empresa_id: int, hoje: date) -> bool:
    """AUD-08: 7 dias antes de `apagar_em`, um e-mail aos administradores ativos da empresa
    `cancelada`, uma vez só (`aviso_apagamento_enviado_em`). O e-mail sai depois do commit."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = _empresa_travada(Empresa(pk=empresa_id))
        if (
            empresa.status != Empresa.Status.CANCELADA
            or empresa.apagada_em is not None
            or empresa.aviso_apagamento_enviado_em is not None
            or empresa.apagar_em is None
            or empresa.apagar_em - timedelta(days=DIAS_DO_AVISO_DO_APAGAMENTO) > hoje
        ):
            return False
        empresa.aviso_apagamento_enviado_em = relogio.agora()
        empresa.save(update_fields=["aviso_apagamento_enviado_em", "atualizado_em"])
        with usar_ator(ATOR_SISTEMA):
            registrar_evento(
                "empresa.avisar_apagamento",
                Categoria.SEGURANCA,
                objeto=empresa,
                depois={"apagar_em": empresa.apagar_em.isoformat()},
                regra="AUD-08",
            )
        quando = dia_mes_e_ano(empresa.apagar_em)
        aviso = Email(
            _administradores_ativos(empresa),
            f"Giro: os dados da {empresa.nome_exibicao} serão apagados em {quando}",
            f"Os dados da {empresa.nome_exibicao} serão apagados em {quando}. Para pedir uma "
            "cópia ou reativar a assinatura, fale com a equipe Giro.",
        )
    try:
        enviar_a_cada_um(aviso.destinatarios, aviso.assunto, aviso.texto)
    except Exception as erro:  # o aviso fica marcado; o log leva só a empresa e o tipo do erro
        logger.warning(
            "Aviso do apagamento da empresa %s: o e-mail falhou (%s)",
            empresa_id,
            type(erro).__name__,
        )
    return True


def avisar_apagamentos(hoje: date | None = None) -> int:
    """`aud_08_avisar_apagamento`, às 09:00. Idempotente."""
    dia = hoje or relogio.hoje()
    with schema_context(get_public_schema_name()):
        empresas = list(
            Empresa.objects.filter(
                status=Empresa.Status.CANCELADA,
                apagada_em__isnull=True,
                aviso_apagamento_enviado_em__isnull=True,
                apagar_em__lte=dia + timedelta(days=DIAS_DO_AVISO_DO_APAGAMENTO),
            )
            .order_by("pk")
            .values_list("pk", flat=True)
        )
    return sum(avisar_apagamento(pk, dia) for pk in empresas)


def _limpar_publico(empresa: Empresa) -> bool | None:
    """O passo (c) do apagamento (`cancelamento.md`, "O que fica no `public`"), nesta ordem, cada
    parte podendo rodar de novo. A `Empresa` vem travada. Devolve se o pagador foi anonimizado
    no parceiro (`None` sem pagador)."""
    # 1. Faturas: o tomador como a empresa ainda está; a `atrasada` guarda o e-mail de cobrança.
    faturas = FaturaAssinatura.objects.filter(empresa_id=empresa.pk).exclude(
        status=StatusFatura.CANCELADA
    )
    for fatura in faturas.filter(tomador_gravado_em__isnull=True):
        gravar_tomador(fatura)
    faturas.filter(status=StatusFatura.ATRASADA, email_cobranca="").update(
        email_cobranca=empresa.email_cobranca, atualizado_em=relogio.agora()
    )
    # 2. O pagador na conta principal perde e-mail e telefone (B-01). A recusa do parceiro não
    # segura o resto (T-199, M-03): fica no evento e no log. Fora do ar, tenta amanhã.
    anonimizado: bool | None = None
    forma = FormaPagamentoAssinatura.objects.filter(empresa_id=empresa.pk).first()
    if forma is not None and forma.cliente_externo_id:
        cliente = forma.cliente_externo_id
        try:
            _no_parceiro(lambda: provedor().anonimizar_pagador(conta_principal(), cliente))
            anonimizado = True
        except ErroDeRegra:
            logger.error(
                "Apagamento da empresa %s: o parceiro recusou anonimizar o pagador", empresa.pk
            )
            anonimizado = False
    # 3. Linhas de apoio (a forma depois do item 2, que lê o pagador dela).
    Dominio.objects.filter(tenant_id=empresa.pk).delete()
    UsoEmpresa.objects.filter(empresa_id=empresa.pk).delete()
    ContaPagamento.objects.filter(empresa_id=empresa.pk).delete()
    FormaPagamentoAssinatura.objects.filter(empresa_id=empresa.pk).delete()
    # 4. A linha da `Empresa` fica só com o CNPJ, o plano, as datas, a cidade e a UF.
    for campo in DADOS_APAGADOS_DA_EMPRESA:
        setattr(empresa, campo, "")
    empresa.save(update_fields=[*DADOS_APAGADOS_DA_EMPRESA, "atualizado_em"])
    return anonimizado


def apagar_empresa(empresa_id: int) -> dict[str, Any]:
    """AUD-08, ADR 0025: (a) os arquivos do prefixo `<schema>/`; (b) o schema, pela conexão de
    migração (`banco.apagar_schema`, que confere de novo com a `Empresa` travada); (c) o `public`;
    (d) `apagada_em` e o evento `empresa.apagar`, sem dado pessoal. Cada passo pode rodar de novo;
    `apagada_em` só é gravado no fim. Recusada: `banco.ApagamentoRecusado`."""
    from comum.arquivos import apagar_arquivos_da_empresa

    from . import banco

    with schema_context(get_public_schema_name()):
        # T-199, B-02: os arquivos saem com a `Empresa` travada e conferida. A reativação, que
        # trava a mesma linha, espera, e depois recusa: `apagar_em` já chegou.
        with transaction.atomic():
            empresa = _empresa_travada(Empresa(pk=empresa_id))
            banco.conferir_para_apagar(empresa)
            schema = str(empresa.schema_name)
            arquivos = apagar_arquivos_da_empresa(schema)  # (a)
        banco.apagar_schema(empresa_id)  # (b)
        with transaction.atomic():
            empresa = _empresa_travada(empresa)
            banco.conferir_para_apagar(empresa)
            anonimizado = _limpar_publico(empresa)  # (c)
            hoje = relogio.hoje()
            empresa.apagada_em = relogio.agora()  # (d)
            empresa.save(update_fields=["apagada_em", "atualizado_em"])
            with usar_ator(ATOR_SISTEMA):
                registrar_evento(
                    "empresa.apagar",
                    Categoria.SEGURANCA,
                    objeto=empresa,
                    depois={
                        "schema": schema,
                        "arquivos": arquivos,
                        "data": hoje.isoformat(),
                        "pagador_anonimizado": anonimizado,
                    },
                    regra="AUD-08",
                )
    return {"schema": schema, "arquivos": arquivos, "pagador_anonimizado": anonimizado}


def apagar_empresas(hoje: date | None = None) -> int:
    """`aud_08_apagar_empresas`, às 03:30: as `cancelada` com `apagar_em` ≤ hoje e `apagada_em`
    nulo, uma por vez. A que falhar fica para o dia seguinte e vai ao Sentry (log de erro)."""
    dia = hoje or relogio.hoje()
    with schema_context(get_public_schema_name()):
        empresas = list(
            Empresa.objects.filter(
                status=Empresa.Status.CANCELADA, apagar_em__lte=dia, apagada_em__isnull=True
            )
            .order_by("pk")
            .values_list("pk", flat=True)
        )
    if empresas and not getattr(settings, "DATABASE_URL_MIGRACAO", ""):
        # T-199, B-01: sem ela, o DROP vai pela conexão da aplicação, que em produção não tem
        # permissão de DDL (ADR 0016, 0025), e falha todo dia.
        logger.error(
            "aud_08_apagar_empresas sem DATABASE_URL_MIGRACAO: o DROP SCHEMA vai pela conexão da "
            "aplicação (ADR 0025). Configure a variável só no worker desta tarefa."
        )
    apagadas = 0
    for pk in empresas:
        try:
            apagar_empresa(pk)
        except Exception:  # uma empresa não para as outras; tenta de novo amanhã
            logger.error("Apagamento da empresa %s: fica para amanhã", pk, exc_info=True)
            continue
        apagadas += 1
    return apagadas
