"""Relógio do seed: congela `comum.relogio.agora` na data de referência e anda sob comando.

Os serviços leem o "agora" só de `comum.relogio` (o mesmo ponto que os testes trocam), então o
seed monta a história de 07 out 2026 pelos serviços de domínio. Ao sair, o relógio volta ao real.
"""

from datetime import datetime
from types import TracebackType
from typing import Any
from zoneinfo import ZoneInfo

from apps.auditoria.models import EventoAuditoria
from comum import relogio

FUSO = ZoneInfo("America/Sao_Paulo")


class RelogioDoSeed:
    def __init__(self, inicio: str) -> None:
        self._agora = datetime.fromisoformat(inicio).replace(tzinfo=FUSO)
        self._original = relogio.agora

    def __enter__(self) -> "RelogioDoSeed":
        relogio.agora = lambda: self._agora
        # O histórico da locação sai dos eventos de auditoria, e `ocorrido_em` é `auto_now_add`
        # (hora de verdade). Só enquanto o seed roda, o evento leva o momento do relógio do seed
        # (D-13 da T-138); fora dele nada muda.
        campo = EventoAuditoria._meta.get_field("ocorrido_em")

        def pre_save(instancia: Any, add: bool) -> datetime:
            instancia.ocorrido_em = self._agora
            return self._agora

        campo.pre_save = pre_save  # type: ignore[method-assign,assignment]
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        pilha: TracebackType | None,
    ) -> None:
        relogio.agora = self._original
        # Tira o atributo da instância: volta o `pre_save` da classe.
        del EventoAuditoria._meta.get_field("ocorrido_em").__dict__["pre_save"]

    def em(self, texto: str) -> datetime:
        self._agora = datetime.fromisoformat(texto).replace(tzinfo=FUSO)
        return self._agora

    @property
    def agora(self) -> datetime:
        return self._agora
