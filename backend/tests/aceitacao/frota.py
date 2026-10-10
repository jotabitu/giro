"""Frota da Moto Rápida nos testes de aceitação: os dados são os do seed (`backend/seed/frota.py`).

Aqui a frota é gravada direto no banco, no status de partida que o teste pede (o seed de
desenvolvimento usa os serviços de domínio).
"""

from datetime import date
from typing import Any

from apps.filiais.models import Filial
from apps.plataforma.services import recalcular_uso
from apps.veiculos.models import Categoria, PrecoCategoria, Veiculo
from seed.frota import (
    DISTRIBUICAO,
    NOMEADOS,
    PRECOS_SEED,
    STREET_ANTES,
    STREET_SEMANAL_ANTES,
    VIGENTE_DESDE,
    Frota,
)


def criar_veiculo(
    numero: int, categoria: Categoria, filial: Filial, status: str = "disponivel", **dados: Any
) -> Veiculo:
    """Veículo direto no banco, como na importação do seed (status de partida)."""
    padrao: dict[str, Any] = {
        "placa": f"GEN{numero:04d}",
        "chassi": f"9C2GEN{numero:011d}",
        "marca": "Honda",
        "modelo": "Pop 110i",
        "ano_fabricacao": 2024,
        "ano_modelo": 2024,
        "cor": "preta",
        "km_atual": 1000 + numero,
        "entrou_na_frota_em": date(2025, 1, 10),
    }
    return Veiculo.objects.create(
        **{**padrao, **dados}, categoria=categoria, filial=filial, status=status
    )


def criar_categorias(alterado_por: Any) -> dict[str, Categoria]:
    """As 4 categorias com os preços vigentes desde 01 out (e a Street antiga), direto no banco."""
    categorias = {}
    for nome, (_, diaria, semanal, mensal, caucao) in PRECOS_SEED.items():
        tipo = DISTRIBUICAO[nome][0]
        categoria = Categoria.objects.create(nome=nome, tipo_veiculo=tipo)
        valores = {
            "diaria_centavos": diaria,
            "mensal_centavos": mensal,
            "caucao_centavos": caucao,
            "alterado_por": alterado_por,
        }
        if nome == "Street 150–160":
            PrecoCategoria.objects.create(
                categoria=categoria,
                vigente_desde=STREET_ANTES,
                semanal_centavos=STREET_SEMANAL_ANTES,
                **valores,
            )
        PrecoCategoria.objects.create(
            categoria=categoria, vigente_desde=VIGENTE_DESDE, semanal_centavos=semanal, **valores
        )
        categorias[nome] = categoria
    return categorias


def montar_frota(moto: Any) -> Frota:
    """A Filial Centro (matriz, com as pessoas ligadas), a tabela de preços e os 86 veículos."""
    centro = moto.centro()
    frota = Frota(centro=centro, categorias=criar_categorias(moto.pessoas["Mariana"]))
    numero = 0
    for nome, (_, modelos, por_status) in DISTRIBUICAO.items():
        categoria = frota.categorias[nome]
        nomeados = [p for p, d in NOMEADOS.items() if d["categoria"] == nome]
        faltam = dict(por_status)
        for placa in nomeados:
            dados = {k: v for k, v in NOMEADOS[placa].items() if k != "categoria"}
            faltam[dados["status"]] -= 1
            frota.veiculos[placa] = criar_veiculo(0, categoria, centro, placa=placa, **dados)
        for status, quantos in faltam.items():
            for _ in range(quantos):
                numero += 1
                marca, modelo = modelos[numero % len(modelos)]
                criar_veiculo(numero, categoria, centro, status, marca=marca, modelo=modelo)
    recalcular_uso(moto.empresa)
    return frota
