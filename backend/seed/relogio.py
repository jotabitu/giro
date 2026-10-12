"""Relógio do seed: congela `comum.relogio.agora` na data de referência e anda sob comando.

Os serviços leem o "agora" só de `comum.relogio` (o mesmo ponto que os testes trocam), então o
seed monta a história de 07 out 2026 pelos serviços de domínio. Ao sair, o relógio volta ao real.
"""

from datetime import datetime
from types import TracebackType
from zoneinfo import ZoneInfo

from comum import relogio

FUSO = ZoneInfo("America/Sao_Paulo")


class RelogioDoSeed:
    def __init__(self, inicio: str) -> None:
        self._agora = datetime.fromisoformat(inicio).replace(tzinfo=FUSO)
        self._original = relogio.agora

    def __enter__(self) -> "RelogioDoSeed":
        relogio.agora = lambda: self._agora
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        pilha: TracebackType | None,
    ) -> None:
        relogio.agora = self._original

    def em(self, texto: str) -> datetime:
        self._agora = datetime.fromisoformat(texto).replace(tzinfo=FUSO)
        return self._agora

    @property
    def agora(self) -> datetime:
        return self._agora
