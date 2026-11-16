"""Demonstração da Moto Rápida numa empresa que já existe, também em produção (T-476).

Carrega só os dados de negócio do seed (`moto_rapida.carregar_negocio`: filial, frota, clientes,
locações, financeiro, fotos) no schema de uma empresa criada pela `criar_empresa`. Não cria conta:
onde o seed amarra um registro a uma pessoa (vendedor, gerente, vistoriador, financeiro, autor do
evento), entra o administrador da empresa, o único usuário dela.

Datas: a história é montada no relógio do seed (07 out 2026), e os valores em centavos saem
exatamente os de `docs/regras/dados-de-teste.md`. Depois, toda data e data e hora do schema da
empresa anda o mesmo número de dias, de 07 out 2026 até hoje: o "hoje" da demonstração vira o dia
em que o comando roda, e atrasos, vencimentos e reservas ficam na mesma distância de hoje que têm
na referência. Textos já gravados (contrato em PDF, `antes`/`depois` da auditoria) mantêm as datas
originais.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from django.apps import apps
from django.db import connection, models, transaction
from django_tenants.utils import tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.clientes.models import Cliente
from apps.contas.models import Usuario
from apps.filiais import services as filiais_services
from apps.filiais.models import Filial
from apps.financeiro.models import Caixa, ContaReceber, Despesa
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from apps.veiculos.models import Veiculo
from comum import relogio as relogio_do_giro
from comum.auditoria import registrar_evento
from comum.erros import ErroDeNegocio

from . import moto_rapida
from .ator import como
from .relogio import FUSO, RelogioDoSeed

ACAO_MARCA = "demo.carregada"
REFERENCIA = date(2026, 10, 7)
# O que, se já existir sem a marca, mostra que a empresa tem dados de verdade.
DADOS_DE_NEGOCIO: tuple[type[models.Model], ...] = (
    Filial,
    Veiculo,
    Cliente,
    Locacao,
    ContaReceber,
    Caixa,
    Despesa,
)


@dataclass
class ResultadoDemo:
    empresa: Empresa
    dias: int
    criado: list[str] = field(default_factory=list)
    ja_carregada: bool = False


def _recusar(mensagem: str) -> ErroDeNegocio:
    return ErroDeNegocio("demo_recusada", mensagem)


def carregar(subdominio: str, confirmar: str) -> ResultadoDemo:
    if confirmar != subdominio:
        raise _recusar(f"Confirme com --confirmar {subdominio}.")
    empresa = Empresa.objects.filter(subdominio=subdominio).first()
    if empresa is None:
        raise _recusar(f"Empresa {subdominio} não encontrada.")
    hoje = relogio_do_giro.agora().astimezone(FUSO).date()
    with tenant_context(empresa):
        if EventoAuditoria.objects.filter(acao=ACAO_MARCA).exists():
            return ResultadoDemo(empresa, 0, ja_carregada=True)
        usuarios = list(Usuario.objects.all()[:2])
        if len(usuarios) != 1:
            raise _recusar("A empresa de demonstração tem de ter um único usuário.")
        for modelo in DADOS_DE_NEGOCIO:
            if modelo._default_manager.exists():
                raise _recusar(
                    f"A empresa já tem dados ({modelo._meta.verbose_name}) que não vieram da "
                    "demonstração."
                )
        administrador = usuarios[0]
        resultado = ResultadoDemo(empresa, (hoje - REFERENCIA).days)
        with transaction.atomic():
            antes = retrato_antes()
            with (
                _RelogioDeslocado(moto_rapida.INICIO, resultado.dias) as relogio,
                como(administrador),
            ):
                centro = filiais_services.criar_filial(moto_rapida.CENTRO, administrador)
                pessoas = {nome: administrador for nome in moto_rapida.PESSOAS}
                moto_rapida.carregar_negocio(
                    empresa, centro, pessoas, relogio, resultado.criado, []
                )
            deslocar_datas(resultado.dias, antes)
            with como(administrador):
                registrar_evento(
                    ACAO_MARCA,
                    "configuracoes",
                    motivo=(
                        "Dados de demonstração da Moto Rápida (T-476): 07 out 2026 andou "
                        f"{resultado.dias} dias"
                    ),
                )
    return resultado


class _RelogioDeslocado(RelogioDoSeed):
    """O evento de auditoria é imutável (AUD-01): já nasce no dia deslocado, em vez de andar
    depois com o resto."""

    def __init__(self, inicio: str, dias: int) -> None:
        super().__init__(inicio)
        self._dias = timedelta(days=dias)

    def _carimbar(self, campo: Any, nome: str) -> None:
        if campo.model is not EventoAuditoria:
            super()._carimbar(campo, nome)
            return

        def pre_save(instancia: Any, add: bool) -> datetime:
            if add:
                setattr(instancia, nome, self._agora + self._dias)
            return getattr(instancia, nome)  # type: ignore[no-any-return]

        campo.pre_save = pre_save


def _modelos_da_empresa() -> list[type[models.Model]]:
    """Os models com tabela no schema da empresa (não os do public, que o search_path também vê)."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            [connection.schema_name],  # type: ignore[attr-defined]
        )
        tabelas = {linha[0] for linha in cursor.fetchall()}
    return [
        modelo
        for modelo in apps.get_models(include_auto_created=True)
        if not modelo._meta.proxy
        and modelo._meta.managed
        and modelo._meta.db_table in tabelas
        and modelo is not EventoAuditoria  # nasce deslocado (`_RelogioDeslocado`)
    ]


Retrato = dict[str, int | None]  # tabela → maior pk inteira antes da carga (None: tabela vazia)


def retrato_antes() -> Retrato:
    """O que já existia antes da carga (administrador, convite, configuração da empresa): essas
    linhas não andam no tempo, só as que a demonstração criou."""
    retrato: Retrato = {}
    for modelo in _modelos_da_empresa():
        if isinstance(modelo._meta.pk, models.AutoField | models.BigAutoField):
            maior = modelo._default_manager.aggregate(maior=models.Max("pk"))["maior"]
            retrato[modelo._meta.db_table] = maior
        elif modelo._default_manager.exists():
            retrato[modelo._meta.db_table] = -1  # pk não inteira e já com linhas: não mexe
    return retrato


def deslocar_datas(dias: int, antes: Retrato) -> None:
    """Anda `dias` em toda data e data e hora que a demonstração gravou no schema da empresa."""
    if dias == 0:
        return
    with connection.cursor() as cursor:
        for modelo in _modelos_da_empresa():
            meta = modelo._meta
            maior = antes.get(meta.db_table)
            if maior == -1:
                continue
            filtro, parametros = "", []
            if maior is not None:
                filtro = f" AND {connection.ops.quote_name(meta.pk.column)} > %s"
                parametros = [maior]
            tabela = connection.ops.quote_name(meta.db_table)
            somas = []
            for campo in meta.concrete_fields:
                if not isinstance(campo, models.DateField):
                    continue
                if getattr(campo, "auto_now", False) or getattr(campo, "auto_now_add", False):
                    continue  # hora de verdade da gravação, não da história
                coluna = connection.ops.quote_name(campo.column)
                if isinstance(campo, models.DateTimeField):
                    somas.append(f"{coluna} = {coluna} + make_interval(days => %s)")
                else:
                    somas.append(f"{coluna} = {coluna} + %s")
            if not somas:
                continue
            # Uma só UPDATE por tabela: as checagens entre colunas (fim depois do início) valem
            # para a linha inteira.
            cursor.execute(
                f"UPDATE {tabela} SET {', '.join(somas)} WHERE TRUE{filtro}",  # noqa: S608
                [*([dias] * len(somas)), *parametros],
            )
