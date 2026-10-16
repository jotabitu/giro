"""Documentos brasileiros: normalização e dígitos verificadores de CPF e CNPJ (CLI-01)."""

import re

_NAO_DIGITO = re.compile(r"\D")


def so_digitos(valor: str) -> str:
    return _NAO_DIGITO.sub("", valor or "")


def _digito_cnpj(base: str) -> str:
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base) :]
    resto = sum(int(d) * p for d, p in zip(base, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(valor: str) -> bool:
    """Aceita com ou sem máscara. Recusa sequência repetida (00000000000000)."""
    cnpj = so_digitos(valor)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    primeiro = _digito_cnpj(cnpj[:12])
    segundo = _digito_cnpj(cnpj[:12] + primeiro)
    return cnpj[12:] == primeiro + segundo


def _digito_cpf(base: str) -> str:
    peso_inicial = len(base) + 1
    resto = sum(int(d) * (peso_inicial - i) for i, d in enumerate(base)) * 10 % 11
    return "0" if resto == 10 else str(resto)


def cpf_valido(valor: str) -> bool:
    """Aceita com ou sem máscara. Recusa sequência repetida (111.111.111-11)."""
    cpf = so_digitos(valor)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    primeiro = _digito_cpf(cpf[:9])
    segundo = _digito_cpf(cpf[:9] + primeiro)
    return cpf[9:] == primeiro + segundo


UFS = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)  # fmt: skip
