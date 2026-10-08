"""Regras da plataforma (PLT-01, PLT-03, PLT-07, IMP-05). Único lugar que cria empresa, mexe no
uso e abre ou encerra o acesso de suporte.

Os apps da empresa usam só `exigir_limite`, `atualizar_uso`, `registrar_passo_implantacao`,
`registrar_acesso` e `registrar_contador` (contrato da plataforma, "Interface interna").
"""

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import IntegrityError, ProgrammingError, transaction
from django.db.models import Q
from django_tenants.utils import (
    get_public_schema_name,
    schema_context,
    schema_exists,
    tenant_context,
)

from comum import relogio
from comum.auditoria import (
    Ator,
    Categoria,
    TipoAtor,
    ator_atual,
    registrar_evento,
    retrato,
    usar_ator,
)
from comum.autenticacao import SUPORTE_TERMINOU, AtorSuporte, emitir_token_suporte
from comum.conexao import conexao
from comum.documentos import cnpj_valido, so_digitos
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao, LimiteDoPlano, NaoAutenticado
from comum.estados import transicionar
from comum.eventos import publicar

from .models import (
    DIAS_DE_TESTE,
    DURACOES_DO_SUPORTE,
    AcessoSuporte,
    Dominio,
    Empresa,
    Item,
    PermissaoSuporte,
    Plano,
    StatusAcessoSuporte,
    UsoEmpresa,
)

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
    """Empresa em teste, domínio, schema, uso e administrador convidado, numa transação.

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
            plano=plano,
            ciclo=ciclo,
            preco_contratado_centavos=plano.preco_mensal_centavos,
            status=Empresa.Status.EM_TESTE,
            teste_inicio=hoje,
            teste_fim=hoje + timedelta(days=DIAS_DE_TESTE),
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
        registrar_evento(
            "empresa.criar",
            Categoria.CONFIGURACOES,
            objeto=empresa,
            depois=retrato(empresa),
            regra="PLT-01",
        )
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


def registrar_passo_implantacao(passo: str, empresa: Empresa | None = None) -> None:
    """Marca o passo como concluído hoje e move a etapa do funil quando ela muda."""
    if passo not in dict(PASSOS_IMPLANTACAO):
        raise ValueError(f"Passo desconhecido: {passo}")
    empresa = _empresa(empresa)
    with schema_context(get_public_schema_name()), transaction.atomic():
        uso = _uso_travado(empresa)
        if passo not in uso.passos_implantacao:
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
