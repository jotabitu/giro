"""Interface de pagamentos (contrato de financeiro, "Interface de pagamentos"; ADR 0007).

Só `financeiro` e `plataforma` chamam esta interface. Valores sempre em centavos e datas como
`date`; nenhum tipo do SDK do parceiro sai daqui. `falso.py` é a implementação padrão em
desenvolvimento e testes; `asaas.py` (a real) entra com a T-029, que também traz a subconta, a
cobrança recorrente (AUT-04) e a chave da API cifrada (S-05).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class ContaPagamentoRef:
    """A conta principal do Giro ou a subconta da empresa (`plataforma.ContaPagamento`)."""

    conta_externa_id: str


@dataclass(frozen=True)
class Pagador:
    nome: str
    documento: str = ""
    celular: str = ""


@dataclass(frozen=True)
class PedidoCobranca:
    tipo: str  # pix | boleto | cartao_link
    valor_centavos: int
    vencimento: date
    referencia_externa: str  # id da ContaReceber (ou da FaturaAssinatura)
    pagador: Pagador


@dataclass(frozen=True)
class Cobranca:
    id: str
    tipo: str
    valor_centavos: int
    vencimento: date
    pix_copia_e_cola: str = ""
    qr_code_url: str = ""
    linha_digitavel: str = ""
    boleto_url: str = ""


@dataclass(frozen=True)
class SituacaoCobranca:
    status: str  # aguardando | paga | vencida | cancelada | estornada
    valor_pago_centavos: int | None = None
    pago_em: datetime | None = None
    forma: str = ""  # pix | boleto


@dataclass(frozen=True)
class EventoWebhook:
    """O aviso lido do corpo. `token` é o do cabeçalho: quem recebe confere com o hash guardado
    da conta (`hmac.compare_digest`) antes de acreditar em qualquer coisa (S-14)."""

    provedor: str
    evento_id: str
    tipo: str
    cobranca_id: str
    referencia_externa: str
    token: str


class ProvedorPagamentos(Protocol):
    def criar_cobranca(self, conta: ContaPagamentoRef, pedido: PedidoCobranca) -> Cobranca: ...

    def cancelar_cobranca(self, conta: ContaPagamentoRef, cobranca_id: str) -> None: ...

    def consultar_cobranca(
        self, conta: ContaPagamentoRef, cobranca_id: str
    ) -> SituacaoCobranca: ...

    def validar_webhook(
        self, cabecalhos: Mapping[str, str], corpo: bytes
    ) -> EventoWebhook | None: ...
