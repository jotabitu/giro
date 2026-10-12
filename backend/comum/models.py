"""Base dos models de domínio (ADR 0009). `comum` não importa nenhum app de domínio."""

import uuid
from typing import Any, ClassVar

from django.db import models, transaction


class ModeloBase(models.Model):
    """Todo model de domínio herda daqui. Datas em UTC."""

    id = models.BigAutoField(primary_key=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AtivosManager(models.Manager[Any]):
    def get_queryset(self) -> models.QuerySet[Any]:
        return super().get_queryset().filter(ativo=True)


class ModeloAtivavel(models.Model):
    """Nada de negócio é apagado: desative com `ativo=False`."""

    ativo = models.BooleanField(default=True)

    objects = models.Manager()
    ativos = AtivosManager()

    class Meta:
        abstract = True


class Sequencia(models.Model):
    """Contador por chave (prefixo do código), um por schema de empresa."""

    chave = models.CharField(max_length=20, unique=True)
    ultimo_numero = models.PositiveIntegerField(default=0)

    # "chave" aqui é o prefixo do código (LOC, VEN), não segredo.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["chave"]}

    class Meta:
        verbose_name = "sequência"

    def __str__(self) -> str:
        return f"{self.chave}: {self.ultimo_numero}"


class WebhookRecebido(models.Model):
    """Aviso de um parceiro (pagamentos), nos dois schemas (S-14): o `evento_id` único faz o mesmo
    aviso valer uma vez só. O corpo fica guardado para conferência; a baixa nunca confia nele e
    consulta o parceiro."""

    provedor = models.CharField(max_length=20)
    evento_id = models.CharField(max_length=100, unique=True)
    recebido_em = models.DateTimeField()
    corpo = models.JSONField(default=dict)
    processado_em = models.DateTimeField(null=True, blank=True)
    resultado = models.CharField(max_length=40, blank=True, default="")

    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"omitir": ["corpo"]}

    class Meta:
        verbose_name = "webhook recebido"
        verbose_name_plural = "webhooks recebidos"

    def __str__(self) -> str:
        return f"{self.provedor} {self.evento_id}"


class ModeloComCodigo(models.Model):
    """Código legível sequencial por empresa (`LOC-2856`), gerado no primeiro `save()`."""

    PREFIXO_CODIGO: ClassVar[str]

    numero = models.PositiveIntegerField(editable=False)
    codigo = models.CharField(max_length=20, unique=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self._state.adding and not self.codigo:
            from comum.codigos import formatar_codigo, proximo_numero

            # O número sai na mesma transação do registro: rollback devolve o número.
            with transaction.atomic():
                self.numero = proximo_numero(self.PREFIXO_CODIGO)
                self.codigo = formatar_codigo(self.PREFIXO_CODIGO, self.numero)
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class ModeloComCifra(models.Model):
    """Obrigatório para quem tem `CampoCifrado` (ADR 0014).

    `id_cifra` entra no dado associado da cifra: o cifrado copiado para outra linha não
    decifra. Ele nasce com o objeto, então dá para cifrar antes do primeiro `save()`.
    Models do public que guardam dado de uma empresa sobrescrevem `empresa_id_da_cifra`.
    """

    id_cifra = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._id_cifra_salvo = self.__dict__.get("id_cifra")

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Imutável (ADR 0014): trocar o id_cifra deixaria os cifrados da linha ilegíveis.
        if not self._state.adding and self.__dict__.get("id_cifra") != self._id_cifra_salvo:
            raise ValueError("id_cifra não pode mudar depois de criado.")
        super().save(*args, **kwargs)
        self._id_cifra_salvo = self.__dict__.get("id_cifra")

    def empresa_id_da_cifra(self) -> int:
        from comum.cripto import empresa_da_conexao

        return empresa_da_conexao()
