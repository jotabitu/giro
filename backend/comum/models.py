"""Base dos models de domínio (ADR 0009). `comum` não importa nenhum app de domínio."""

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

    class Meta:
        verbose_name = "sequência"

    def __str__(self) -> str:
        return f"{self.chave}: {self.ultimo_numero}"


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
