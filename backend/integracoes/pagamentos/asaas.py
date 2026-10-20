"""Asaas (ADR 0007): subconta por locadora, cobrança Pix e boleto, Pix Automático e webhook.

Nenhum nome de campo, tipo ou status do Asaas sai deste arquivo: tudo vira os tipos de `base.py`
(CA-029-17). Só a biblioteca padrão (`urllib`), como o ViaCEP.

- Chaves: a da conta principal vem do ambiente (`GIRO_ASAAS_CHAVE_API`) e só abre subcontas; cada
  subconta usa a própria chave, cifrada em `plataforma.ContaPagamento` e decifrada aqui, na hora
  da chamada (S-05). Nenhuma chave, corpo ou CPF vai para o log.
- Valores: centavos viram reais por `Decimal` e voltam por `Decimal` (CA-029-05), sem `float`.
- Marca da locadora: o pagador é criado com as notificações do Asaas desligadas; o cliente só
  recebe as mensagens do Giro, com a marca da locadora (AUT-03, AUT-05, CA-029-03).
- Conta principal (assinatura, T-184, ADR 0023): `conta_principal()` sem chave de subconta usa a
  chave do ambiente. O cartão é digitado só na página do parceiro (`cartao_link`, a `invoiceUrl`);
  pago, a consulta devolve o token, a bandeira e o final (`creditCard`), e as próximas faturas são
  cobradas por `cobrar_cartao_salvo` (`creditCardToken`). Pendente de conferir no sandbox.
- Falhas: tempo limite de 10 s; sem resposta ou 5xx → `ParceiroIndisponivel`; 4xx →
  `ParceiroRecusou` com a mensagem do Asaas, que vem em português.
"""

import json
import logging
import re
from collections.abc import Callable, Mapping
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from comum import relogio

from . import CABECALHO_DO_TOKEN, CONTA_PRINCIPAL
from .base import (
    Autorizacao,
    CartaoGuardado,
    CartaoRecusado,
    Cobranca,
    ContaPagamentoRef,
    DadosEmpresa,
    EventoWebhook,
    Pagador,
    ParceiroIndisponivel,
    ParceiroRecusou,
    PedidoCobranca,
    PedidoRecorrencia,
    SituacaoCobranca,
    StatusDesconhecido,
    Subconta,
)

logger = logging.getLogger(__name__)

TEMPO_LIMITE_SEGUNDOS = 10
URL_SANDBOX = "https://api-sandbox.asaas.com/v3"

# (método, url, corpo, cabeçalhos) -> (status HTTP, corpo). Os testes de contrato trocam por
# respostas gravadas.
Transporte = Callable[[str, str, bytes | None, Mapping[str, str]], tuple[int, bytes]]

TIPOS = {"pix": "PIX", "boleto": "BOLETO", "cartao_link": "CREDIT_CARD"}
FORMAS = {"PIX": "pix", "BOLETO": "boleto", "CREDIT_CARD": "cartao"}

# CA-029-08. Pago: recebido (Pix, boleto compensado) ou confirmado (boleto antes da compensação).
# Estorno e contestação viram pendência, nunca reabrem a conta. O resto é desconhecido.
STATUS_COBRANCA = {
    "PENDING": "aguardando",
    "AWAITING_RISK_ANALYSIS": "aguardando",
    "RECEIVED": "paga",
    "CONFIRMED": "paga",
    "OVERDUE": "vencida",
    "REFUNDED": "estornada",
    "REFUND_REQUESTED": "estornada",
    "REFUND_IN_PROGRESS": "estornada",
    "CHARGEBACK_REQUESTED": "estornada",
    "CHARGEBACK_DISPUTE": "estornada",
    "AWAITING_CHARGEBACK_REVERSAL": "estornada",
}
STATUS_AUTORIZACAO = {
    "CREATED": "pendente",
    "ACTIVE": "ativa",
    "CANCELLED": "cancelada",
    "REFUSED": "recusada",
    "EXPIRED": "expirada",
}
STATUS_SUBCONTA = {
    "APPROVED": "aprovada",
    "REJECTED": "recusada",
    "PENDING": "pendente",
    "AWAITING_APPROVAL": "pendente",
}
FREQUENCIAS = {
    "semanal": "WEEKLY",
    "mensal": "MONTHLY",
    "trimestral": "QUARTERLY",
    "semestral": "SEMIANNUALLY",
    "anual": "ANNUALLY",
}
TIPOS_EMPRESA = {
    "mei": "MEI",
    "limitada": "LIMITED",
    "individual": "INDIVIDUAL",
    "associacao": "ASSOCIATION",
}
# Avisos que a subconta manda ao Giro. Outros não chegam (e chegariam como 401).
EVENTOS_DO_WEBHOOK = [
    "PAYMENT_CONFIRMED",
    "PAYMENT_RECEIVED",
    "PAYMENT_REFUNDED",
    "PAYMENT_PARTIALLY_REFUNDED",
    "PAYMENT_CHARGEBACK_REQUESTED",
]
MENSAGEM_RECUSA = "Os dados foram recusados pelo parceiro de pagamento."


# --- Dinheiro sem float (CA-029-05) ---


def reais(centavos: int) -> Decimal:
    """30609 → Decimal("306.09")."""
    return Decimal(centavos).scaleb(-2)


def centavos(valor: Any) -> int:
    """306.09 (lido como `Decimal`) → 30609. Recusa fração de centavo."""
    em_centavos = Decimal(str(valor)) * 100
    if em_centavos != em_centavos.to_integral_value():
        raise ValueError(f"Valor com fração de centavo: {valor}")
    return int(em_centavos)


_MARCA_DECIMAL = re.compile(r'"__decimal__(-?\d+\.\d+)__"')


def _para_json(dados: Mapping[str, Any]) -> bytes:
    """JSON com os `Decimal` como número (306.09), sem passar por `float`."""

    def converter(valor: Any) -> Any:
        if isinstance(valor, Decimal):
            return f"__decimal__{valor:f}__"
        if isinstance(valor, Mapping):
            return {k: converter(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [converter(v) for v in valor]
        return valor

    texto = json.dumps(converter(dados), ensure_ascii=False)
    return _MARCA_DECIMAL.sub(r"\1", texto).encode()


def _de_json(corpo: bytes) -> Any:
    return json.loads(corpo, parse_float=Decimal) if corpo else {}


# --- HTTP ---


def transporte_urllib(
    metodo: str, url: str, corpo: bytes | None, cabecalhos: Mapping[str, str]
) -> tuple[int, bytes]:
    if not url.startswith("https://"):
        raise ValueError("O Asaas só é chamado por HTTPS.")
    pedido = Request(url, data=corpo, method=metodo, headers=dict(cabecalhos))  # noqa: S310
    try:
        with urlopen(pedido, timeout=TEMPO_LIMITE_SEGUNDOS) as resposta:  # noqa: S310
            return int(resposta.status), bytes(resposta.read())
    except HTTPError as erro:
        return int(erro.code), bytes(erro.read() or b"")
    except (URLError, TimeoutError, OSError) as erro:
        raise ParceiroIndisponivel(str(type(erro).__name__)) from erro


def _caminho_sem_consulta(url: str) -> str:
    """Para o log: a consulta pode ter CPF."""
    return urlsplit(url).path


class Asaas:
    def __init__(
        self,
        *,
        url_base: str | None = None,
        chave_principal: str | None = None,
        transporte: Transporte | None = None,
    ) -> None:
        self.url_base = (url_base or getattr(settings, "GIRO_ASAAS_URL", "") or URL_SANDBOX).rstrip(
            "/"
        )
        self._chave_principal = (
            chave_principal
            if chave_principal is not None
            else getattr(settings, "GIRO_ASAAS_CHAVE_API", "")
        )
        self._transporte = transporte or transporte_urllib

    def __repr__(self) -> str:
        return f"Asaas({self.url_base})"

    # --- chamadas ---

    def _chave(self, conta: ContaPagamentoRef | None) -> str:
        """A chave do ambiente só serve à conta principal (sem conta, ou `CONTA_PRINCIPAL`). A
        subconta usa só a dela: sem chave, nada é chamado, para a cobrança da locadora nunca ir
        para a conta do Giro (ADR 0007; M-02 da T-189, T-269)."""
        if conta is None or conta.conta_externa_id == CONTA_PRINCIPAL:
            chave = self._chave_principal
        else:
            chave = conta.decifrar_chave()
        if not chave:
            raise ParceiroIndisponivel("Sem a chave da API do parceiro de pagamento.")
        return chave

    def _chamar(
        self,
        metodo: str,
        caminho: str,
        *,
        conta: ContaPagamentoRef | None,
        corpo: Mapping[str, Any] | None = None,
        consulta: Mapping[str, str] | None = None,
        aceitar: tuple[int, ...] = (),
    ) -> tuple[int, Any]:
        url = f"{self.url_base}{caminho}"
        if consulta:
            url = f"{url}?{urlencode(consulta)}"
        cabecalhos = {
            "access_token": self._chave(conta),
            "Accept": "application/json",
            "User-Agent": "Giro",
        }
        dados = None
        if corpo is not None:
            dados = _para_json(corpo)
            cabecalhos["Content-Type"] = "application/json"
        status, resposta = self._transporte(metodo, url, dados, cabecalhos)
        logger.info("Asaas %s %s: %s", metodo, _caminho_sem_consulta(url), status)
        if status >= 500:
            raise ParceiroIndisponivel(f"Asaas respondeu {status}")
        try:
            lido = _de_json(resposta)
        except ValueError as erro:
            raise ParceiroIndisponivel("Resposta do Asaas ilegível") from erro
        if status >= 400 and status not in aceitar:
            raise ParceiroRecusou(_mensagem_de_erro(lido))
        return status, lido

    # --- subconta (passo "Recebimentos") ---

    def criar_subconta(self, empresa: DadosEmpresa) -> Subconta:
        corpo: dict[str, Any] = {
            "name": empresa.nome,
            "email": empresa.email,
            "cpfCnpj": empresa.documento,
            "mobilePhone": empresa.celular,
            "incomeValue": reais(empresa.faturamento_mensal_centavos),
            "address": empresa.logradouro,
            "addressNumber": empresa.numero,
            "complement": empresa.complemento,
            "province": empresa.bairro,
            "postalCode": empresa.cep,
            "webhooks": [
                {
                    "name": "Giro",
                    "url": empresa.webhook_url,
                    "email": empresa.email,
                    "sendType": "SEQUENTIALLY",
                    "interrupted": False,
                    "enabled": True,
                    "apiVersion": 3,
                    "authToken": empresa.webhook_token,
                    "events": EVENTOS_DO_WEBHOOK,
                }
            ],
        }
        if empresa.tipo_empresa:
            corpo["companyType"] = TIPOS_EMPRESA[empresa.tipo_empresa]
        _, dados = self._chamar("POST", "/accounts", conta=None, corpo=corpo)
        # A chave vem só nesta resposta (`accessToken.apiKey`; antes, `apiKey` na raiz).
        chave = (dados.get("accessToken") or {}).get("apiKey") or dados.get("apiKey") or ""
        if not chave:
            raise ParceiroIndisponivel("Subconta criada sem a chave da API.")
        return Subconta(
            conta_externa_id=str(dados["id"]),
            carteira_id=str(dados.get("walletId") or ""),
            chave_api=str(chave),
        )

    def consultar_subconta(self, conta: ContaPagamentoRef) -> str:
        _, dados = self._chamar("GET", "/myAccount/status", conta=conta)
        return STATUS_SUBCONTA.get(str(dados.get("general", "")), "pendente")

    # --- pagador ---

    def _pagador(self, conta: ContaPagamentoRef, pagador: Pagador) -> str:
        """O cliente da locadora na subconta: criado uma vez, achado pelo CPF depois (CA-029-04).
        Com as notificações do Asaas desligadas (CA-029-03). Na conta principal, a empresa já
        criada por `criar_ou_atualizar_pagador` vem com o `id_externo`."""
        if pagador.id_externo:
            return pagador.id_externo
        if pagador.documento:
            _, achados = self._chamar(
                "GET", "/customers", conta=conta, consulta={"cpfCnpj": pagador.documento}
            )
            for achado in achados.get("data") or []:
                if not achado.get("deleted"):
                    return str(achado["id"])
        corpo: dict[str, Any] = {"name": pagador.nome, "notificationDisabled": True}
        if pagador.documento:
            corpo["cpfCnpj"] = pagador.documento
        if pagador.celular:
            corpo["mobilePhone"] = pagador.celular
        if pagador.email:
            corpo["email"] = pagador.email
        _, criado = self._chamar("POST", "/customers", conta=conta, corpo=corpo)
        return str(criado["id"])

    def criar_ou_atualizar_pagador(self, conta: ContaPagamentoRef, pagador: Pagador) -> str:
        """A empresa como cliente da conta principal, com razão social, CNPJ, endereço e o e-mail
        de cobrança, e as notificações do Asaas desligadas (as mensagens são do Giro)."""
        corpo: dict[str, Any] = {
            "name": pagador.nome,
            "cpfCnpj": pagador.documento,
            "email": pagador.email,
            "notificationDisabled": True,
        }
        if pagador.celular:
            corpo["mobilePhone"] = pagador.celular
        if pagador.endereco is not None:
            endereco = pagador.endereco
            corpo.update(
                {
                    "postalCode": endereco.cep,
                    "address": endereco.logradouro,
                    "addressNumber": endereco.numero,
                    "complement": endereco.complemento,
                    "province": endereco.bairro,
                }
            )
        if pagador.id_externo:
            caminho = f"/customers/{quote(pagador.id_externo, safe='')}"
            _, dados = self._chamar("POST", caminho, conta=conta, corpo=corpo)
        else:
            _, dados = self._chamar("POST", "/customers", conta=conta, corpo=corpo)
        return str(dados["id"])

    def cobrar_cartao_salvo(
        self, conta: ContaPagamentoRef, token: str, pedido: PedidoCobranca
    ) -> Cobranca:
        """PLT-02: cobra no token do cartão guardado. Recusa do cartão (4xx) → `CartaoRecusado`."""
        if pedido.valor_centavos <= 0:
            raise ValueError("Cobrança sem valor.")
        corpo: dict[str, Any] = {
            "customer": self._pagador(conta, pedido.pagador),
            "billingType": "CREDIT_CARD",
            "value": reais(pedido.valor_centavos),
            "dueDate": pedido.vencimento.isoformat(),
            "externalReference": pedido.referencia_externa,
            "creditCardToken": token,
        }
        try:
            _, criada = self._chamar("POST", "/payments", conta=conta, corpo=corpo)
        except ParceiroRecusou as erro:
            raise CartaoRecusado(erro.mensagem) from erro
        if centavos(criada["value"]) != pedido.valor_centavos:
            raise ParceiroRecusou("O valor da cobrança voltou diferente do pedido.")
        return Cobranca(
            str(criada["id"]),
            "cartao",
            pedido.valor_centavos,
            date.fromisoformat(str(criada["dueDate"])),
        )

    # --- cobranças (FIN-04) ---

    def criar_cobranca(self, conta: ContaPagamentoRef, pedido: PedidoCobranca) -> Cobranca:
        return self._criar_cobranca(conta, pedido)

    def _criar_cobranca(
        self, conta: ContaPagamentoRef, pedido: PedidoCobranca, autorizacao_id: str = ""
    ) -> Cobranca:
        if pedido.tipo not in TIPOS:
            raise ValueError(f"Tipo de cobrança sem suporte no Asaas: {pedido.tipo}")
        if pedido.valor_centavos <= 0:
            raise ValueError("Cobrança sem valor.")
        cliente = self._pagador(conta, pedido.pagador)
        # Uma cobrança aberta por conta (CA-029-16): a que ficou para trás numa tentativa que
        # falhou do lado do Giro é cancelada antes de criar a nova.
        self._cancelar_abertas_da_referencia(conta, pedido.referencia_externa)
        corpo: dict[str, Any] = {
            "customer": cliente,
            "billingType": TIPOS[pedido.tipo],
            "value": reais(pedido.valor_centavos),
            "dueDate": pedido.vencimento.isoformat(),
            "externalReference": pedido.referencia_externa,
        }
        if autorizacao_id:
            corpo["pixAutomaticAuthorizationId"] = autorizacao_id
        _, criada = self._chamar("POST", "/payments", conta=conta, corpo=corpo)
        cobranca_id = str(criada["id"])
        try:
            return self._completar(conta, pedido, cobranca_id, criada)
        except (ParceiroIndisponivel, ParceiroRecusou):
            # Sem o Pix copia e cola ou a linha digitável, a cobrança não serve: não deixa uma
            # cobrança pela metade no parceiro.
            self.cancelar_cobranca(conta, cobranca_id)
            raise

    def _completar(
        self,
        conta: ContaPagamentoRef,
        pedido: PedidoCobranca,
        cobranca_id: str,
        criada: Mapping[str, Any],
    ) -> Cobranca:
        if centavos(criada["value"]) != pedido.valor_centavos:
            raise ParceiroRecusou("O valor da cobrança voltou diferente do pedido.")
        vencimento = date.fromisoformat(str(criada["dueDate"]))
        if pedido.tipo == "cartao_link":
            # O cartão é digitado só na página do parceiro (ADR 0023).
            url = str(criada.get("invoiceUrl") or "")
            if not url:
                raise ParceiroIndisponivel("Cobrança no cartão sem a página do parceiro.")
            return Cobranca(
                cobranca_id, pedido.tipo, pedido.valor_centavos, vencimento, url_pagina=url
            )
        caminho = f"/payments/{quote(cobranca_id, safe='')}"
        if pedido.tipo == "pix":
            _, pix = self._chamar("GET", f"{caminho}/pixQrCode", conta=conta)
            # A imagem vem em base64 e não cabe numa URL: a tela desenha o QR do copia e cola.
            return Cobranca(
                cobranca_id,
                pedido.tipo,
                pedido.valor_centavos,
                vencimento,
                pix_copia_e_cola=str(pix["payload"]),
            )
        _, linha = self._chamar("GET", f"{caminho}/identificationField", conta=conta)
        return Cobranca(
            cobranca_id,
            pedido.tipo,
            pedido.valor_centavos,
            vencimento,
            linha_digitavel=str(linha["identificationField"]),
            boleto_url=str(criada.get("bankSlipUrl") or ""),
            pix_copia_e_cola=self._pix_do_boleto(conta, caminho, cobranca_id),
        )

    def _pix_do_boleto(self, conta: ContaPagamentoRef, caminho: str, cobranca_id: str) -> str:
        """FIN-04 (T-305): o boleto também se paga por Pix, pelo mesmo `pixQrCode`. Recusado
        (400, a conta sem Pix disponível), o boleto sai sem ele e não é cancelado. Parceiro fora
        do ar sobe, e a cobrança é cancelada como as outras."""
        try:
            _, pix = self._chamar("GET", f"{caminho}/pixQrCode", conta=conta)
        except ParceiroRecusou:
            logger.warning("Boleto %s sem o Pix: o parceiro recusou o QR Code", cobranca_id)
            return ""
        return str(pix.get("payload") or "")

    def _cancelar_abertas_da_referencia(self, conta: ContaPagamentoRef, referencia: str) -> None:
        _, achadas = self._chamar(
            "GET",
            "/payments",
            conta=conta,
            consulta={"externalReference": referencia, "status": "PENDING"},
        )
        for achada in achadas.get("data") or []:
            if not achada.get("deleted"):
                self.cancelar_cobranca(conta, str(achada["id"]))

    def cancelar_cobranca(self, conta: ContaPagamentoRef, cobranca_id: str) -> None:
        status, _ = self._chamar(
            "DELETE",
            f"/payments/{quote(cobranca_id, safe='')}",
            conta=conta,
            aceitar=(400, 404),
        )
        if status in (400, 404):
            # Já paga, já removida ou inexistente: se foi paga, o webhook chega e vira pendência
            # (CA-029-07, CA-029-13). Gerar a cobrança nova não pode travar por isso.
            logger.warning("Asaas não cancelou a cobrança %s: %s", cobranca_id, status)

    def consultar_cobranca(self, conta: ContaPagamentoRef, cobranca_id: str) -> SituacaoCobranca:
        status_http, dados = self._chamar(
            "GET", f"/payments/{quote(cobranca_id, safe='')}", conta=conta, aceitar=(404,)
        )
        if status_http == 404 or dados.get("deleted"):
            return SituacaoCobranca("cancelada")
        status_parceiro = str(dados.get("status", ""))
        status = STATUS_COBRANCA.get(status_parceiro)
        if status is None:
            raise StatusDesconhecido(status_parceiro)
        forma = FORMAS.get(str(dados.get("billingType", "")), "")
        if status != "paga":
            return SituacaoCobranca(status, forma=forma)
        dia = (
            dados.get("clientPaymentDate") or dados.get("paymentDate") or dados.get("confirmedDate")
        )
        return SituacaoCobranca(
            "paga",
            valor_pago_centavos=centavos(dados["value"]),
            pago_em=_momento_do_pagamento(str(dia)) if dia else relogio.agora(),
            forma=forma,
            cartao=_cartao(dados) if forma == "cartao" else None,
            recibo_url=str(dados.get("transactionReceiptUrl") or ""),
        )

    # --- Pix Automático (AUT-04) ---

    def criar_autorizacao_recorrente(
        self, conta: ContaPagamentoRef, pedido: PedidoRecorrencia
    ) -> Autorizacao:
        cliente = self._pagador(conta, pedido.pagador)
        corpo: dict[str, Any] = {
            "customerId": cliente,
            "contractId": pedido.referencia_externa[:35],
            "frequency": FREQUENCIAS[pedido.frequencia],
            "startDate": pedido.inicio.isoformat(),
            "value": reais(pedido.valor_centavos),
            "paymentCreationMode": "MANUAL",
            "immediateQrCode": {
                "expirationSeconds": 24 * 60 * 60,
                "originalValue": reais(pedido.primeira_cobranca_centavos),
            },
        }
        if pedido.fim is not None:
            corpo["finishDate"] = pedido.fim.isoformat()
        if pedido.descricao:
            corpo["description"] = pedido.descricao[:35]
        _, dados = self._chamar("POST", "/pix/automatic/authorizations", conta=conta, corpo=corpo)
        return _autorizacao(dados)

    def cobrar_com_autorizacao(
        self, conta: ContaPagamentoRef, autorizacao_id: str, pedido: PedidoCobranca
    ) -> Cobranca:
        if pedido.tipo != "pix":
            raise ValueError("A autorização recorrente cobra só por Pix.")
        return self._criar_cobranca(conta, pedido, autorizacao_id)

    def cancelar_autorizacao(self, conta: ContaPagamentoRef, autorizacao_id: str) -> None:
        status, _ = self._chamar(
            "DELETE",
            f"/pix/automatic/authorizations/{quote(autorizacao_id, safe='')}",
            conta=conta,
            aceitar=(404,),
        )
        if status == 404:
            logger.warning("Asaas não achou a autorização %s para cancelar", autorizacao_id)

    def consultar_autorizacao(self, conta: ContaPagamentoRef, autorizacao_id: str) -> Autorizacao:
        status, dados = self._chamar(
            "GET",
            f"/pix/automatic/authorizations/{quote(autorizacao_id, safe='')}",
            conta=conta,
            aceitar=(404,),
        )
        if status == 404:
            return Autorizacao(autorizacao_id, "cancelada")
        return _autorizacao(dados)

    # --- webhook (S-14) ---

    def validar_webhook(self, cabecalhos: Mapping[str, str], corpo: bytes) -> EventoWebhook | None:
        """Só lê o corpo e o token. A view confere o token com o hash guardado, e a baixa
        consulta a cobrança no Asaas sem confiar no corpo (S-14)."""
        token = cabecalhos.get(CABECALHO_DO_TOKEN, "")
        try:
            dados = json.loads(corpo)
            if "payment" not in dados and "pixAutomaticAuthorization" in dados:
                # PLT-13: a autorização do Pix Automático mudou (conta principal). Nomes do
                # evento e do objeto a conferir no sandbox.
                autorizacao = dados["pixAutomaticAuthorization"]
                return EventoWebhook(
                    provedor="asaas",
                    evento_id=str(dados["id"]),
                    tipo=str(dados["event"]),
                    cobranca_id="",
                    referencia_externa=str(autorizacao.get("contractId") or ""),
                    token=token,
                    autorizacao_id=str(autorizacao["id"]),
                )
            pagamento = dados["payment"]
            return EventoWebhook(
                provedor="asaas",
                evento_id=str(dados["id"]),
                tipo=str(dados["event"]),
                cobranca_id=str(pagamento["id"]),
                referencia_externa=str(pagamento.get("externalReference") or ""),
                token=token,
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            return None


def _autorizacao(dados: Mapping[str, Any]) -> Autorizacao:
    status_parceiro = str(dados.get("status", ""))
    status = STATUS_AUTORIZACAO.get(status_parceiro)
    if status is None:
        raise StatusDesconhecido(status_parceiro)
    return Autorizacao(
        id=str(dados["id"]), status=status, pix_copia_e_cola=str(dados.get("payload") or "")
    )


def _cartao(dados: Mapping[str, Any]) -> CartaoGuardado | None:
    """O cartão pago na página do parceiro: token, bandeira e os 4 últimos (`creditCard`)."""
    cartao = dados.get("creditCard")
    if not isinstance(cartao, Mapping) or not cartao.get("creditCardToken"):
        return None
    return CartaoGuardado(
        token=str(cartao["creditCardToken"]),
        bandeira=str(cartao.get("creditCardBrand") or "").lower(),
        final=str(cartao.get("creditCardNumber") or "")[-4:],
    )


def _momento_do_pagamento(dia: str) -> datetime:
    """O Asaas dá só o dia do pagamento. Pago hoje: agora; noutro dia: o começo dele, no fuso
    da locadora."""
    pago = date.fromisoformat(dia[:10])
    if pago == relogio.hoje():
        return relogio.agora()
    return datetime.combine(pago, time.min, tzinfo=timezone.get_current_timezone())


def _mensagem_de_erro(dados: Any) -> str:
    erros = dados.get("errors") if isinstance(dados, Mapping) else None
    descricoes = [
        str(e.get("description")).strip()
        for e in erros or []
        if isinstance(e, Mapping) and e.get("description")
    ]
    texto = " ".join(descricoes) or MENSAGEM_RECUSA
    # A mensagem pode ir para a tela da locadora: sem o nome do parceiro.
    return re.sub(r"\basaas\b", "parceiro de pagamento", texto, flags=re.IGNORECASE)[:300]
