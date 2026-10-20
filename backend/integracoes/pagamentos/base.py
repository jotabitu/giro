"""Interface de pagamentos (contrato de financeiro, "Interface de pagamentos"; ADR 0007).

Só `financeiro` e `plataforma` chamam esta interface. Valores sempre em centavos e datas como
`date`; nenhum tipo, campo ou status do parceiro sai daqui. `falso.py` é a implementação padrão
em desenvolvimento e testes; `asaas.py` é a real (T-029).

A chave da subconta (S-05) chega cifrada: `ContaPagamentoRef.decifrar_chave` só é chamada dentro
da implementação, no momento da chamada ao parceiro.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol


def _sem_chave() -> str:
    return ""


@dataclass(frozen=True)
class ContaPagamentoRef:
    """A conta principal do Giro ou a subconta da empresa (`plataforma.ContaPagamento`).

    `decifrar_chave` devolve a chave da API da subconta; vazio para a conta principal, que usa a
    chave do ambiente."""

    conta_externa_id: str
    decifrar_chave: Callable[[], str] = field(default=_sem_chave, repr=False, compare=False)


@dataclass(frozen=True)
class Endereco:
    cep: str
    logradouro: str
    numero: str
    bairro: str
    cidade: str
    uf: str
    complemento: str = ""


@dataclass(frozen=True)
class Pagador:
    """Quem paga. Na conta principal (assinatura), a empresa: `id_externo` é o cliente já criado
    por `criar_ou_atualizar_pagador`, e a cobrança não procura de novo."""

    nome: str
    documento: str = ""
    celular: str = ""
    email: str = ""
    endereco: Endereco | None = None
    id_externo: str = ""


@dataclass(frozen=True)
class PedidoCobranca:
    tipo: str  # pix | boleto | cartao_link (página do parceiro, ADR 0023)
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
    url_pagina: str = ""  # cartao_link: a página do parceiro onde o cartão é digitado


@dataclass(frozen=True)
class CartaoGuardado:
    """O que o parceiro devolve do cartão pago na página dele (ADR 0023). Nunca o número: o token,
    a bandeira e os 4 últimos dígitos. Quem recebe cifra o token e nunca o mostra."""

    token: str = field(repr=False)
    bandeira: str  # visa | mastercard | elo | amex | hipercard | ... (minúsculas)
    final: str


@dataclass(frozen=True)
class SituacaoCobranca:
    status: str  # aguardando | paga | vencida | cancelada | estornada
    valor_pago_centavos: int | None = None
    pago_em: datetime | None = None
    forma: str = ""  # pix | boleto | cartao
    cartao: CartaoGuardado | None = None  # paga no cartão (conta principal, ADR 0023)
    recibo_url: str = ""  # comprovante do parceiro, quando paga (PLT-14)


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
    # Aviso de autorização do Pix Automático (conta principal, PLT-13): sem cobrança.
    autorizacao_id: str = ""


@dataclass(frozen=True)
class DadosEmpresa:
    """O que o passo "Recebimentos" manda para abrir a subconta (ADR 0007). `webhook_token` é o
    token aleatório que o parceiro devolve no cabeçalho de cada aviso; só o hash fica guardado."""

    nome: str
    documento: str  # CNPJ (ou CPF), só dígitos
    email: str
    celular: str
    logradouro: str
    numero: str
    bairro: str
    cep: str
    faturamento_mensal_centavos: int
    webhook_url: str
    webhook_token: str = field(repr=False)
    complemento: str = ""
    tipo_empresa: str = ""  # mei | limitada | individual | associacao


@dataclass(frozen=True)
class Subconta:
    """`chave_api` só existe nesta resposta: quem recebe cifra e guarda (S-05)."""

    conta_externa_id: str
    carteira_id: str
    chave_api: str = field(repr=False)
    status: str = "pendente"  # pendente | aprovada | recusada


@dataclass(frozen=True)
class PedidoRecorrencia:
    """Autorização de cobrança recorrente (AUT-04): o pagador aprova uma vez, e cada parcela é
    cobrada depois com `cobrar_com_autorizacao`. A primeira cobrança vai junto da autorização."""

    referencia_externa: str  # id da locação (até 35 caracteres)
    frequencia: str  # semanal | mensal | trimestral | semestral | anual
    inicio: date
    valor_centavos: int
    primeira_cobranca_centavos: int
    pagador: Pagador
    fim: date | None = None
    descricao: str = ""


@dataclass(frozen=True)
class Autorizacao:
    id: str
    status: str  # pendente | ativa | cancelada | recusada | expirada
    pix_copia_e_cola: str = ""


class CartaoRecusado(Exception):
    """A cobrança no cartão guardado foi recusada (PLT-02). `mensagem` sem o nome do parceiro."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class ParceiroIndisponivel(Exception):
    """O parceiro não respondeu no tempo limite ou respondeu 5xx. Nada foi feito pela metade."""


class ParceiroRecusou(Exception):
    """O parceiro recusou o pedido (dados inválidos). `mensagem` vem em português e pode ir para
    a tela de quem trabalha na locadora."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class StatusDesconhecido(Exception):
    """O parceiro devolveu um status que o Giro não conhece: vira erro para o financeiro, nunca
    uma baixa (CA-029-08)."""


class ProvedorPagamentos(Protocol):
    def criar_subconta(self, empresa: DadosEmpresa) -> Subconta: ...

    def consultar_subconta(self, conta: ContaPagamentoRef) -> str: ...

    def criar_cobranca(self, conta: ContaPagamentoRef, pedido: PedidoCobranca) -> Cobranca: ...

    def cancelar_cobranca(self, conta: ContaPagamentoRef, cobranca_id: str) -> None: ...

    def consultar_cobranca(
        self, conta: ContaPagamentoRef, cobranca_id: str
    ) -> SituacaoCobranca: ...

    def criar_autorizacao_recorrente(
        self, conta: ContaPagamentoRef, pedido: PedidoRecorrencia
    ) -> Autorizacao: ...

    def cobrar_com_autorizacao(
        self, conta: ContaPagamentoRef, autorizacao_id: str, pedido: PedidoCobranca
    ) -> Cobranca: ...

    def cancelar_autorizacao(self, conta: ContaPagamentoRef, autorizacao_id: str) -> None: ...

    def consultar_autorizacao(
        self, conta: ContaPagamentoRef, autorizacao_id: str
    ) -> Autorizacao: ...

    # Conta principal, para a assinatura (T-184, ADR 0023).

    def criar_ou_atualizar_pagador(self, conta: ContaPagamentoRef, pagador: Pagador) -> str:
        """Cria o cliente (ou atualiza o de `pagador.id_externo`) com as notificações do parceiro
        desligadas e devolve o id dele."""
        ...

    def anonimizar_pagador(self, conta: ContaPagamentoRef, cliente_id: str) -> None:
        """AUD-08 (B-01, T-236): tira e-mail, telefone e celular do cliente e desliga as
        notificações dele. Nome, CNPJ, cobranças e notas ficam no parceiro."""
        ...

    def cobrar_cartao_salvo(
        self, conta: ContaPagamentoRef, token: str, pedido: PedidoCobranca
    ) -> Cobranca:
        """Cobra no cartão guardado. Recusado: `CartaoRecusado`. A baixa vem pelo webhook."""
        ...

    def validar_webhook(
        self, cabecalhos: Mapping[str, str], corpo: bytes
    ) -> EventoWebhook | None: ...
