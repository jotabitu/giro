"""Classificação dos campos na auditoria (ADR 0014, item 3; substitui o item 7 da 0010).

Cada model declara o que é sensível; o resto vai inteiro para `antes`/`depois`:

    CAMPOS_AUDITORIA = {
        "omitir": ["password"],                       # vira {"alterado": true}
        "mascarar": {"documento": "documento", "celular": "telefone"},
        "inteiro": ["email"],                         # sensível pelo nome, mas vai inteiro
    }

`mascarar` também aceita lista; o tipo da máscara sai do nome do campo. São omitidos sem
declarar: `password`, todo `CampoCifrado`, todo `CampoHashBusca` e todo campo `*_hash`.
"""

import ipaddress
import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from typing import Any

from django.db import models

from comum.campos import CampoCifrado, CampoHashBusca

OMITIDO = {"alterado": True}

# Segmentos de nome (separados por "_") que obrigam a classificar o campo.
SEGMENTOS_SENSIVEIS = frozenset(
    {
        "cpf",
        "cnh",
        "documento",
        "senha",
        "password",
        "token",
        "chave",
        "secret",
        "celular",
        "telefone",
        "email",
        "endereco",
        "logradouro",
        "nascimento",
        "ip",
        # R-02 da T-050: nome de pessoa e pagador também obrigam a decidir (ADR 0014).
        "nome",
        "pagador",
    }
)

# Tipo de máscara deduzido do nome quando `mascarar` é uma lista.
_TIPO_POR_SEGMENTO = {
    "cpf": "documento",
    "cnpj": "documento",
    "documento": "documento",
    "cnh": "cnh",
    "nome": "nome",
    "pagador": "nome",
    "nascimento": "nascimento",
    "celular": "telefone",
    "telefone": "telefone",
    "email": "email",
    "endereco": "endereco",
    "logradouro": "endereco",
    "ip": "ip",
}


def _digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def mascarar_documento(valor: str) -> str:
    """CPF `123.218.330-45` vira `***.218.330-**`; CNPJ vai inteiro (é dado da empresa)."""
    digitos = _digitos(valor)
    if len(digitos) == 11:
        return f"***.{digitos[3:6]}.{digitos[6:9]}-**"
    if len(digitos) == 14:
        return digitos
    return mascarar_generico(valor)


def mascarar_cnh(valor: str) -> str:
    """`01234561234` vira `*******1234`."""
    digitos = _digitos(valor) or valor
    return "*" * max(len(digitos) - 4, 0) + digitos[-4:]


def mascarar_nome(valor: str) -> str:
    """`Larissa Souza` vira `L. S.`."""
    return " ".join(f"{parte[0].upper()}." for parte in valor.split() if parte)


def mascarar_nascimento(valor: Any) -> str:
    """Só o ano."""
    if isinstance(valor, date):
        return str(valor.year)
    achado = re.search(r"\d{4}", str(valor))
    return achado.group(0) if achado else "****"


def mascarar_telefone(valor: str) -> str:
    """`(85) 98765-1234` vira `(85) *****-1234`."""
    digitos = _digitos(valor)
    if digitos.startswith("55") and len(digitos) > 11:
        digitos = digitos[2:]
    if len(digitos) < 10:
        return mascarar_generico(valor)
    return f"({digitos[:2]}) {'*' * (len(digitos) - 6)}-{digitos[-4:]}"


def mascarar_email(valor: str) -> str:
    """`larissa@gmail.com` vira `l***@g***.com`."""
    local, arroba, dominio = valor.partition("@")
    if not arroba or not local or not dominio:
        return mascarar_generico(valor)
    _, ponto, final = dominio.rpartition(".")
    return f"{local[0]}***@{dominio[0]}***{ponto}{final if ponto else ''}"


def mascarar_endereco(valor: str) -> str:
    """Endereço em texto livre some; cidade e UF ficam inteiras em campos próprios."""
    return "***"


def mascarar_ip(valor: str) -> str:
    """IPv4 vira a rede /24 e IPv6, a rede /48."""
    try:
        ip = ipaddress.ip_address(valor)
    except ValueError:
        return mascarar_generico(valor)
    prefixo = 24 if ip.version == 4 else 48
    return str(ipaddress.ip_network(f"{ip}/{prefixo}", strict=False))


def mascarar_generico(valor: str) -> str:
    """Só os 3 últimos caracteres."""
    return "*" * max(len(valor) - 3, 0) + valor[-3:] if len(valor) > 3 else "*" * len(valor)


MASCARAS = {
    "documento": mascarar_documento,
    "cnh": mascarar_cnh,
    "nome": mascarar_nome,
    "nascimento": mascarar_nascimento,
    "telefone": mascarar_telefone,
    "email": mascarar_email,
    "endereco": mascarar_endereco,
    "ip": mascarar_ip,
}


@dataclass(frozen=True)
class Classificacao:
    omitir: frozenset[str]
    mascarar: dict[str, str]
    inteiro: frozenset[str]

    def classificados(self) -> frozenset[str]:
        return self.omitir | frozenset(self.mascarar) | self.inteiro


def _segmentos(nome: str) -> set[str]:
    return set(nome.lower().split("_"))


def _tipo_pelo_nome(nome: str) -> str:
    for segmento in nome.lower().split("_"):
        if segmento in _TIPO_POR_SEGMENTO:
            return _TIPO_POR_SEGMENTO[segmento]
    raise ValueError(f"Não sei mascarar '{nome}': declare o tipo em CAMPOS_AUDITORIA.")


def _omitido_automaticamente(campo: "models.Field[Any, Any]") -> bool:
    return (
        isinstance(campo, CampoCifrado | CampoHashBusca)
        or campo.name == "password"
        or campo.name.endswith("_hash")
    )


@cache
def classificacao(modelo: type[models.Model]) -> Classificacao:
    declarado: dict[str, Any] = getattr(modelo, "CAMPOS_AUDITORIA", {})
    desconhecidas = set(declarado) - {"omitir", "mascarar", "inteiro"}
    if desconhecidas:
        raise ValueError(f"{modelo.__name__}.CAMPOS_AUDITORIA: chaves {sorted(desconhecidas)}.")

    campos = {c.name: c for c in modelo._meta.concrete_fields}
    omitir = set(declarado.get("omitir", ()))
    omitir |= {nome for nome, campo in campos.items() if _omitido_automaticamente(campo)}

    mascarar_declarado = declarado.get("mascarar", {})
    inteiro = set(declarado.get("inteiro", ()))
    for nome in set(declarado.get("omitir", ())) | set(mascarar_declarado) | inteiro:
        if nome not in campos:
            raise ValueError(f"{modelo.__name__}.CAMPOS_AUDITORIA cita campo inexistente: {nome}")

    if isinstance(mascarar_declarado, dict):
        mascarar = dict(mascarar_declarado)
    else:
        mascarar = {nome: _tipo_pelo_nome(nome) for nome in mascarar_declarado}
    for nome, tipo in mascarar.items():
        if tipo not in MASCARAS:
            raise ValueError(f"{modelo.__name__}.{nome}: máscara desconhecida '{tipo}'.")
    return Classificacao(frozenset(omitir), mascarar, frozenset(inteiro))


def campos_sensiveis_sem_classificacao(modelo: type[models.Model]) -> list[str]:
    """Para o teste de arquitetura: campos com nome sensível que ninguém classificou."""
    classificados = classificacao(modelo).classificados()
    return sorted(
        campo.name
        for campo in modelo._meta.concrete_fields
        if _segmentos(campo.name) & SEGMENTOS_SENSIVEIS and campo.name not in classificados
    )


def aplicar(
    modelo: type[models.Model], antes: dict[str, Any], depois: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recebe a diferença com valores reais e devolve o que pode ir para o evento."""
    regras = classificacao(modelo)
    nomes = {c.attname: c.name for c in modelo._meta.concrete_fields}

    def tratar(lado: dict[str, Any], *, e_depois: bool) -> dict[str, Any]:
        tratado: dict[str, Any] = {}
        for chave, valor in lado.items():
            nome = nomes.get(chave, chave)
            if nome in regras.omitir:
                if e_depois:
                    tratado[chave] = OMITIDO
            elif nome in regras.mascarar and valor not in (None, ""):
                tratado[chave] = MASCARAS[regras.mascarar[nome]](
                    valor if regras.mascarar[nome] == "nascimento" else str(valor)
                )
            else:
                tratado[chave] = valor
        return tratado

    novo_depois = tratar(depois, e_depois=True)
    # Campo omitido que só existia no "antes" (raro) ainda marca que mudou.
    for chave in antes:
        if nomes.get(chave, chave) in regras.omitir and chave not in novo_depois:
            novo_depois[chave] = OMITIDO
    return tratar(antes, e_depois=False), novo_depois
