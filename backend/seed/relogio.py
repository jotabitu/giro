"""Relógio do seed: congela `comum.relogio.agora` na data de referência e anda sob comando.

Os serviços leem o "agora" só de `comum.relogio` (o mesmo ponto que os testes trocam), então o
seed monta a história de 07 out 2026 pelos serviços de domínio. Ao sair, o relógio volta ao real.
"""

from datetime import datetime
from types import TracebackType
from typing import Any
from zoneinfo import ZoneInfo

from apps.aprovacoes.models import PedidoAprovacao
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
        # O mesmo vale para a hora do pedido de aprovação (`criado_em`): o tempo médio de
        # resposta da `APR-12` sai de `decidido_em - criado_em`.
        for modelo, nome in ((EventoAuditoria, "ocorrido_em"), (PedidoAprovacao, "criado_em")):
            self._carimbar(modelo._meta.get_field(nome), nome)
        return self

    def _carimbar(self, campo: Any, nome: str) -> None:
        def pre_save(instancia: Any, add: bool) -> datetime:
            if add:  # só na criação: o pedido é salvo de novo ao ser decidido
                setattr(instancia, nome, self._agora)
            return getattr(instancia, nome)  # type: ignore[no-any-return]

        campo.pre_save = pre_save

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        pilha: TracebackType | None,
    ) -> None:
        relogio.agora = self._original
        # Tira o atributo da instância: volta o `pre_save` da classe.
        del EventoAuditoria._meta.get_field("ocorrido_em").__dict__["pre_save"]
        del PedidoAprovacao._meta.get_field("criado_em").__dict__["pre_save"]

    def em(self, texto: str) -> datetime:
        self._agora = datetime.fromisoformat(texto).replace(tzinfo=FUSO)
        return self._agora

    @property
    def agora(self) -> datetime:
        return self._agora
