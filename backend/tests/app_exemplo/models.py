"""Model só de teste para exercitar a fundação de `comum` como um módulo real usaria."""

from typing import ClassVar

from django.db import models

from comum import cripto
from comum.campos import CampoCifrado, CampoHashBusca, CentavosField, PercentualField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase, ModeloComCifra, ModeloComCodigo


class Pedido(ModeloComCodigo, MaquinaDeEstados, ModeloBase):
    PREFIXO_CODIGO = "LOC"
    REGRA_TRANSICAO = "LOC-00"

    class Status(models.TextChoices):
        RESERVADA = "reservada", "Reservada"
        ATIVA = "ativa", "Ativa"
        ENCERRADA = "encerrada", "Encerrada"
        CANCELADA = "cancelada", "Cancelada"

    TRANSICOES = {
        "reservada": {"ativa", "cancelada"},
        "ativa": {"encerrada"},
    }
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"mascarar": ["cpf_cliente"]}

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVADA)
    cliente = models.CharField(max_length=100, default="")
    cpf_cliente = models.CharField(max_length=14, blank=True, default="")
    valor_centavos = CentavosField(default=0)
    desconto_pct = PercentualField(default=0)

    def __str__(self) -> str:
        return self.codigo


class Pessoa(ModeloComCifra, ModeloBase):
    """Parecido com o Cliente das regras, para testar cifra, hash e classificação."""

    CAMPOS_AUDITORIA: ClassVar[dict[str, object]] = {
        "mascarar": {
            "nome": "nome",
            "celular": "telefone",
            "email": "email",
            "nascimento": "nascimento",
            "endereco": "endereco",
        },
    }

    nome = models.CharField(max_length=150)
    documento = CampoCifrado()
    documento_hash = CampoHashBusca(de="documento", unique=True)
    cnh_numero = CampoCifrado()
    cnh_hash = CampoHashBusca(de="cnh_numero", db_index=True)
    celular = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    nascimento = models.DateField(null=True, blank=True)
    endereco = models.CharField(max_length=200, blank=True, default="")
    cidade = models.CharField(max_length=80, blank=True, default="")
    uf = models.CharField(max_length=2, blank=True, default="")
    anonimizado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.nome


class Credencial(ModeloComCifra, ModeloBase):
    """Parecido com plataforma.ContaPagamento: segredo cifrado com a chave de segredos."""

    descricao = models.CharField(max_length=80)
    chave_api_cifrada = CampoCifrado(tipo=cripto.SEGREDOS)

    def __str__(self) -> str:
        return self.descricao
