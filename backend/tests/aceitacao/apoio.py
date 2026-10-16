"""Apoio dos testes de aceitação: marca de espera e dados do seed Moto Rápida.

Cada teste de aceitação nasce como esqueleto: leva o código do critério (CA-NNN-NN) e o da regra
no nome, traz no corpo os números esperados e chama `pendente`. O backend dono da tarefa implementa;
o qa preenche o corpo (arrange, ato, assert) e remove o `xfail` quando o endpoint existir.
"""

import pytest

from seed.frota import PRECOS_SEED  # noqa: F401  (a tabela é do seed; os testes importam daqui)

DATA_DE_REFERENCIA = "2026-10-07"
FUSO = "America/Sao_Paulo"


def aguarda(tarefa: str):
    """Marca o teste como esperado até o backend da tarefa entregar."""
    return pytest.mark.xfail(
        reason=f"{tarefa} (backend) ainda não implementou",
        strict=True,
        raises=NotImplementedError,
    )


def pendente(**esperado) -> None:
    """Corpo provisório: guarda os números do critério e falha como não implementado."""
    raise NotImplementedError(esperado)


# Plano e preços (PLT-03): centavos; None = ilimitado.
PLANOS_SEED = {
    "Essencial": {"mensal": 19900, "anual": 199000, "veiculos": 30, "filiais": 1, "usuarios": 3},
    "Profissional": {
        "mensal": 44900,
        "anual": 449000,
        "veiculos": 150,
        "filiais": 3,
        "usuarios": 10,
    },
    "Completo": {
        "mensal": 89900,
        "anual": 899000,
        "veiculos": None,
        "filiais": None,
        "usuarios": None,
    },
}

# Usuários da Moto Rápida (T-011): nome → (perfil, status).
USUARIOS_SEED = {
    "Mariana Costa": ("administrador", "ativo"),
    "Rodrigo Pinheiro": ("gerente", "ativo"),
    "Bruna Alves": ("vendedor", "ativo"),
    "João Silva": ("vistoriador", "convite_pendente"),
    "Lúcia Freitas": ("financeiro", "convite_pendente"),
    "Felipe Nunes": ("vendedor", "desativado"),
}

CONTAGENS_FROTA_SEED = {
    "todos": 86,
    "disponivel": 16,
    "alugado": 42,
    "reservado": 9,
    "em_manutencao": 7,
    "a_venda": 12,
    "indisponivel": 0,
    "em_movimentacao": 0,  # MOV-03 (T-288)
    "motos": 80,
    "carros": 6,
}
