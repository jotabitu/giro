"""Campos de dinheiro, percentual, cifrados e de hash de busca (ADR 0009 e 0014).

Dinheiro termina em `_centavos`; percentual, em `_pct`.
"""

import secrets
from typing import Any

from django.db import models

from comum import cripto


class CentavosField(models.PositiveBigIntegerField):  # type: ignore[type-arg]
    """Valor monetário que nunca é negativo, em centavos."""


class CentavosComSinalField(models.BigIntegerField):  # type: ignore[type-arg]
    """Só para saldos, diferenças e extrato bancário."""


class PercentualField(models.DecimalField):  # type: ignore[type-arg]
    """Percentual com 2 casas (`8.00`)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_digits", 5)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)


class CampoCifrado(models.TextField):  # type: ignore[type-arg]
    """Guarda só o cifrado. Para um campo `documento`, o model ganha:

    - `obj.definir_documento("123.218.330-45")`: cifra e preenche os `CampoHashBusca` ligados;
    - `obj.documento_claro()`: decifra sob demanda.

    O atributo `obj.documento` é o cifrado: o claro nunca aparece em `__str__`, `repr`, Admin
    nem auditoria (a auditoria omite todo `CampoCifrado`). O model precisa herdar de
    `comum.models.ModeloComCifra`.
    """

    def __init__(self, *args: Any, tipo: str = cripto.DADOS_PESSOAIS, **kwargs: Any) -> None:
        if tipo not in (cripto.DADOS_PESSOAIS, cripto.SEGREDOS):
            raise ValueError(f"Tipo de chave desconhecido: {tipo}")
        self.tipo = tipo
        kwargs.setdefault("blank", True)
        kwargs.setdefault("default", "")
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        nome, caminho, args, kwargs = super().deconstruct()
        kwargs["tipo"] = self.tipo
        kwargs.pop("editable", None)
        return nome, caminho, args, kwargs

    def contribute_to_class(self, cls: type[models.Model], name: str, **kwargs: Any) -> None:
        super().contribute_to_class(cls, name, **kwargs)
        campo = self

        def associado(obj: Any) -> bytes:
            if not hasattr(obj, "id_cifra"):
                raise TypeError(f"{type(obj).__name__} precisa herdar de ModeloComCifra.")
            return cripto.dado_associado(
                obj.empresa_id_da_cifra(), type(obj)._meta.db_table, campo.name, str(obj.id_cifra)
            )

        def claro(obj: Any) -> str:
            valor = getattr(obj, campo.attname)
            if not valor:
                return ""
            return cripto.decifrar(valor, tipo=campo.tipo, associado=associado(obj))

        def definir(obj: Any, valor: str | None) -> None:
            texto = valor or ""
            cifrado = cripto.cifrar(texto, tipo=campo.tipo, associado=associado(obj))
            setattr(obj, campo.attname, cifrado if texto else "")
            for outro in type(obj)._meta.concrete_fields:
                if isinstance(outro, CampoHashBusca) and outro.de == campo.name:
                    valor_hash = (
                        cripto.hash_busca(texto, empresa_id=obj.empresa_id_da_cifra())
                        if texto
                        else None
                    )
                    setattr(obj, outro.attname, valor_hash)

        setattr(cls, f"{name}_claro", claro)
        setattr(cls, f"definir_{name}", definir)


class CampoHashBusca(models.CharField):  # type: ignore[type-arg]
    """HMAC-SHA256 por empresa (hex de 64) do `CampoCifrado` indicado em `de`.

    Use `unique=True` para unicidade (`CLI-01`) ou `db_index=True` para busca exata.
    """

    def __init__(self, *args: Any, de: str = "", **kwargs: Any) -> None:
        if not de:
            raise ValueError("Informe em `de` o CampoCifrado de origem.")
        self.de = de
        kwargs["max_length"] = 64
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        nome, caminho, args, kwargs = super().deconstruct()
        kwargs["de"] = self.de
        kwargs.pop("max_length", None)
        kwargs.pop("editable", None)
        return nome, caminho, args, kwargs


def anonimizar_cifrado(obj: models.Model, nome: str) -> None:
    """AUD-06: apaga o cifrado e troca os hashes ligados por um valor aleatório.

    O valor aleatório mantém a unicidade sem guardar nada que identifique a pessoa. Quem chama
    grava `anonimizado_em` e salva.
    """
    campo = obj._meta.get_field(nome)
    if not isinstance(campo, CampoCifrado):
        raise TypeError(f"{nome} não é CampoCifrado.")
    setattr(obj, campo.attname, "")
    for outro in obj._meta.concrete_fields:
        if isinstance(outro, CampoHashBusca) and outro.de == nome:
            setattr(obj, outro.attname, secrets.token_hex(32))


def buscar_por_hash(valor: str) -> str:
    """Hash do termo de busca na empresa atual: `Cliente.objects.filter(documento_hash=...)`."""
    return cripto.hash_busca(valor)
