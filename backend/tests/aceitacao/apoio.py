"""Apoio dos testes de aceitação: marca de espera e dados do seed Moto Rápida.

Cada teste de aceitação nasce como esqueleto: leva o código do critério (CA-NNN-NN) e o da regra
no nome, traz no corpo os números esperados e chama `pendente`. O backend dono da tarefa implementa;
o qa preenche o corpo (arrange, ato, assert) e remove o `xfail` quando o endpoint existir.
"""

import pytest

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

# Tabela de preços da Filial Centro (T-013):
# categoria → (veículos, diária, semanal, mensal, caução).
PRECOS_SEED = {
    "Urbana 110–125": (42, 4490, 29940, 109000, 30000),
    "Street 150–160": (32, 5490, 32900, 119000, 30000),
    "Scooter premium": (6, 7990, 44900, 159000, 50000),
    "Carro compacto": (6, 10900, 64900, 229000, 80000),
}

CONTAGENS_FROTA_SEED = {
    "todos": 86,
    "disponivel": 16,
    "alugado": 42,
    "reservado": 9,
    "em_manutencao": 7,
    "a_venda": 12,
    "indisponivel": 0,
    "motos": 80,
    "carros": 6,
}
