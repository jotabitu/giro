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
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.db import IntegrityError, ProgrammingError, models, transaction
from django.db.models import Q
from django_tenants.utils import (
    get_public_schema_name,
    schema_context,
    schema_exists,
    tenant_context,
)

from comum import relogio
from comum.auditoria import (
    ATOR_SISTEMA,
    Ator,
    Categoria,
    TipoAtor,
    ator_atual,
    auditar,
    registrar_evento,
    retrato,
    usar_ator,
)
from comum.autenticacao import SUPORTE_TERMINOU, AtorSuporte, emitir_token_suporte
from comum.conexao import conexao
from comum.documentos import cnpj_valido, so_digitos
from comum.erros import (
    Conflito,
    ErroDeRegra,
    ErroDeValidacao,
    LimiteDoPlano,
    NaoAutenticado,
    ParceiroForaDoAr,
)
from comum.estados import transicionar
from comum.eventos import publicar
from comum.models import WebhookRecebido
from integracoes.pagamentos import conta_principal, hash_do_token, provedor, referencia
from integracoes.pagamentos.base import (
    CartaoGuardado,
    DadosEmpresa,
    Endereco,
    EventoWebhook,
    Pagador,
    ParceiroIndisponivel,
    ParceiroRecusou,
    StatusDesconhecido,
)

from .calendario import Periodo, proximo_periodo
from .models import (
    CAMPOS_DO_ENDERECO,
    DIAS_DE_TESTE,
    DURACOES_DO_SUPORTE,
    AcessoSuporte,
    ContaPagamento,
    Dominio,
    Empresa,
    FaturaAssinatura,
    FormaAssinatura,
    FormaPagaFatura,
    FormaPagamentoAssinatura,
    Item,
    PermissaoSuporte,
    Plano,
    StatusAcessoSuporte,
    StatusContaPagamento,
    StatusFatura,
    StatusFormaPagamento,
    TipoFatura,
    UsoEmpresa,
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
        with tenant_context(empresa):
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
    with tenant_context(empresa):
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


def no_publico() -> Any:
    return schema_context(get_public_schema_name())


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
    with schema_context(acesso.empresa.schema_name), usar_ator(ator):
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
            for schema in (get_public_schema_name(), empresa.schema_name):
                with schema_context(schema):
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
        with (
            usar_ator(ATOR_SISTEMA),
            auditar(
                atual,
                "empresa.dados_fiscais",
                Categoria.CONFIGURACOES,
                motivo=motivo,
                regra="PLT-15",
            ),
        ):
            for campo in CAMPOS_DO_ENDERECO:
                setattr(atual, f"endereco_{campo}", endereco.get(campo) or "")
            atual.save(update_fields=[f"endereco_{c}" for c in CAMPOS_DO_ENDERECO])
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
                        },
                        "conta": "principal",
                        "bruto": corpo,
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
    if resultado != "baixada":
        logger.warning("Aviso %s da conta principal: %s", webhook.pk, resultado)
    return resultado


def _processar_fatura(webhook: WebhookRecebido) -> str:
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
    with usar_ator(ATOR_SISTEMA):
        transicionar(
            fatura,
            StatusFatura.PAGA,
            acao="fatura_assinatura.pagar",
            regra="PLT-14",
            mais_campos=("pago_em", "forma"),
        )
        if situacao.cartao is not None:
            _guardar_cartao(fatura.empresa, situacao.cartao)
    return "baixada"


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
