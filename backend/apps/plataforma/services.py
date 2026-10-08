"""Regras da plataforma (PLT-01, PLT-03, IMP-05). Único lugar que cria empresa e mexe no uso.

Os apps da empresa usam só `exigir_limite`, `atualizar_uso`, `registrar_passo_implantacao`,
`registrar_acesso` e `registrar_contador` (contrato da plataforma, "Interface interna").
"""

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django_tenants.utils import get_public_schema_name, schema_context, tenant_context

from comum import relogio
from comum.auditoria import Categoria, registrar_evento, retrato
from comum.conexao import conexao
from comum.documentos import cnpj_valido, so_digitos
from comum.erros import Conflito, ErroDeValidacao, LimiteDoPlano
from comum.eventos import publicar

from .models import DIAS_DE_TESTE, Dominio, Empresa, Item, Plano, UsoEmpresa

SUBDOMINIOS_RESERVADOS = frozenset({"admin", "www", "api", "app", "suporte", "status"})
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
    elif subdominio in SUBDOMINIOS_RESERVADOS | {settings.SUBDOMINIO_PLATAFORMA}:
        erros["subdominio"] = ["Este endereço é reservado. Escolha outro."]
    if not cnpj_valido(cnpj):
        erros["cnpj"] = ["CNPJ inválido"]
    if not administrador.nome.strip():
        erros["administrador.nome"] = ["Informe o nome."]
    if "@" not in administrador.email:
        erros["administrador.email"] = ["Informe um e-mail válido."]
    return erros


def validar_criacao(subdominio: str, cnpj: str, administrador: Administrador) -> None:
    """400 `validacao` para formato; 409 `subdominio_em_uso` ou `cnpj_em_uso` (PLT-01)."""
    erros = _validar(subdominio, cnpj, administrador)
    if erros:
        raise ErroDeValidacao(erros)
    with schema_context(get_public_schema_name()):
        if (
            Empresa.objects.filter(subdominio=subdominio).exists()
            or Empresa.objects.filter(schema_name=schema_do_subdominio(subdominio)).exists()
        ):
            raise Conflito("subdominio_em_uso", "Este endereço já está em uso. Escolha outro.")
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
        try:
            with transaction.atomic():
                empresa.save()  # cria o schema e aplica as migrações (auto_create_schema)
        except IntegrityError as erro:  # outra criação ganhou a corrida
            raise Conflito("subdominio_em_uso", "Este endereço já está em uso.") from erro
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
