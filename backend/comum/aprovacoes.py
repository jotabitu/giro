"""Porta dos pedidos de aprovação (ADR 0019): o único jeito de outro app abrir, consultar e
cancelar pedidos sem importar `aprovacoes`.

`comum` declara as funções e o app `aprovacoes` registra a implementação no `ready()`, como em
`comum.permissoes.registrar_pode`. Sem implementação registrada, as funções falham na hora: um
pedido perdido em silêncio liberaria uma ação que precisava de aprovação.

Uso: `ref = aprovacoes.pedir(tipo="APR-06", origem_tipo="veiculo", origem_id=..., ...)`, dentro
da transação de quem chama. A volta é o evento `aprovacoes.pedido_decidido` (ADR 0011).
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from comum.erros import Conflito


@dataclass(frozen=True)
class PedidoRef:
    id: int
    tipo: str  # "APR-01" a "APR-06"
    status: str  # "pendente" na criação

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Resumo:
    """As células prontas do cartão do pedido e a nota (T-201, `aprovacoes.md`, "Resumo por
    tipo"). Montado pela origem, que já tem os números; `aprovacoes` só guarda e devolve."""

    celulas: list[tuple[str, str]]
    nota: str | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "celulas": [
                {"rotulo": rotulo, "valor": valor} for rotulo, valor in self.celulas if valor
            ],
            "nota": self.nota,
        }


MESES_CURTOS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def dia_curto(dia: date) -> str:
    """A data curta das células do `resumo`: "07 out"."""
    return f"{dia.day:02d} {MESES_CURTOS[dia.month - 1]}"


class PedidoPendente(Conflito):
    """Já existe um pedido igual aguardando decisão. HTTP 409."""

    def __init__(self, pedido_id: int) -> None:
        super().__init__(
            "pedido_pendente",
            "Já existe um pedido aguardando o gerente",
            {"pedido_id": pedido_id},
        )


_pedir: Callable[..., PedidoRef] | None = None
_pendente: Callable[..., PedidoRef | None] | None = None
_cancelar_pendentes: Callable[..., int] | None = None


def registrar(
    *,
    pedir: Callable[..., PedidoRef],
    pendente: Callable[..., PedidoRef | None],
    cancelar_pendentes: Callable[..., int],
) -> None:
    """Chamado pelo `ready()` do app `aprovacoes`."""
    global _pedir, _pendente, _cancelar_pendentes
    _pedir, _pendente, _cancelar_pendentes = pedir, pendente, cancelar_pendentes


def _sem_implementacao() -> RuntimeError:
    return RuntimeError("Nenhuma implementação de pedidos de aprovação registrada (ADR 0019).")


def pedir(
    *,
    tipo: str,
    origem_tipo: str,
    origem_id: int,
    origem_codigo: str | None,
    filial_id: int,
    solicitante: Any,
    titulo: str,
    detalhe: str,
    motivo: str | None = None,
    valor_centavos: int | None = None,
    pct: Any = None,
    dados: dict[str, Any] | None = None,
    resumo: Resumo | None = None,
) -> PedidoRef:
    """Abre o pedido (APR-10 na auditoria). Pedido igual pendente: `PedidoPendente` (409)."""
    if _pedir is None:
        raise _sem_implementacao()
    return _pedir(
        tipo=tipo,
        origem_tipo=origem_tipo,
        origem_id=origem_id,
        origem_codigo=origem_codigo,
        filial_id=filial_id,
        solicitante=solicitante,
        titulo=titulo,
        detalhe=detalhe,
        motivo=motivo,
        valor_centavos=valor_centavos,
        pct=pct,
        dados=dados,
        resumo=resumo,
    )


def pendente(*, tipo: str, origem_tipo: str, origem_id: int) -> PedidoRef | None:
    if _pendente is None:
        raise _sem_implementacao()
    return _pendente(tipo=tipo, origem_tipo=origem_tipo, origem_id=origem_id)


def cancelar_pendentes(*, origem_tipo: str, origem_id: int, motivo: str) -> int:
    if _cancelar_pendentes is None:
        raise _sem_implementacao()
    return _cancelar_pendentes(origem_tipo=origem_tipo, origem_id=origem_id, motivo=motivo)
