"""Frota da Moto Rápida nos testes de aceitação: os dados são os do seed (`backend/seed/frota.py`).

Aqui a frota é gravada direto no banco, no status de partida que o teste pede (o seed de
desenvolvimento usa os serviços de domínio). Sem categorias (ADR 0043): cada veículo tem o tipo
(`tipo_veiculo`) do grupo da tabela e os planos do grupo (`modelo_do_grupo`).
"""

from datetime import date
from typing import Any

from apps.filiais.models import Filial
from apps.plataforma.services import recalcular_uso
from apps.veiculos.models import Categoria, PrecoCategoria, Veiculo
from apps.veiculos.services import ModeloDePreco, aplicar_modelo_de_preco, dados_da_vei_09
from seed.frota import DISTRIBUICAO, NOMEADOS, PRECOS_SEED, VIGENTE_DESDE, Frota

URBANA = "Urbana 110–125"
STREET = "Street 150–160"
SCOOTER = "Scooter premium"
CARRO = "Carro compacto"


def tipo_do_grupo(grupo: str) -> str:
    """Moto ou carro do grupo da tabela do seed (VEI-11)."""
    return DISTRIBUICAO[grupo][0]


def modelo_do_grupo(grupo: str) -> ModeloDePreco:
    """Os planos diária, semanal e mensal do grupo, ligados, com a caução do grupo."""
    _, diaria, semanal, mensal, caucao = PRECOS_SEED[grupo]
    return ModeloDePreco(diaria=diaria, semanal=semanal, mensal=mensal, caucao=caucao)


def com_planos_do_grupo(veiculo: Veiculo, grupo: str) -> Veiculo:
    """O veículo criado direto no banco ganha os planos do grupo (ligados, VEI-15)."""
    aplicar_modelo_de_preco([veiculo], "cadastro", modelo_do_grupo(grupo))
    return veiculo


def criar_veiculo(
    numero: int, grupo: str, filial: Filial, status: str = "disponivel", **dados: Any
) -> Veiculo:
    """Veículo direto no banco, como na importação do seed (status de partida), com o tipo do
    grupo da tabela e sem planos (quem quer os planos chama `com_planos_do_grupo`)."""
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
        "tipo_veiculo": tipo_do_grupo(grupo),
    }
    # Os blocos da VEI-09 do QXA-4B21 (T-421) viram os campos do model.
    dados |= dados_da_vei_09(dados)
    for bloco in ("documento", "rastreador"):
        dados.pop(bloco, None)
    return Veiculo.objects.create(**{**padrao, **dados}, filial=filial, status=status)


def montar_frota(moto: Any) -> Frota:
    """A Filial Centro (matriz, com as pessoas ligadas) e os 86 veículos com os planos do grupo."""
    centro = moto.centro()
    frota = Frota(centro=centro)
    numero = 0
    for nome, (_, modelos, por_status) in DISTRIBUICAO.items():
        nomeados = [p for p, d in NOMEADOS.items() if d["categoria"] == nome]
        faltam = dict(por_status)
        criados: list[Veiculo] = []
        for placa in nomeados:
            dados = {k: v for k, v in NOMEADOS[placa].items() if k != "categoria"}
            faltam[dados["status"]] -= 1
            frota.veiculos[placa] = criar_veiculo(0, nome, centro, placa=placa, **dados)
            criados.append(frota.veiculos[placa])
        for status, quantos in faltam.items():
            for _ in range(quantos):
                numero += 1
                marca, modelo = modelos[numero % len(modelos)]
                criados.append(
                    criar_veiculo(numero, nome, centro, status, marca=marca, modelo=modelo)
                )
        aplicar_modelo_de_preco(criados, "cadastro", modelo_do_grupo(nome))
        frota.grupos.update({veiculo.pk: nome for veiculo in criados})
    recalcular_uso(moto.empresa)
    return frota


def criar_categorias(alterado_por: Any) -> dict[str, Categoria]:
    """As 4 categorias da tabela, direto no banco, só para a importação, que ainda escolhe a
    categoria por modelo até a T-522 B2 (ADR 0043, item 4). O veículo não as lê."""
    categorias = {}
    for nome, (_, diaria, semanal, mensal, caucao) in PRECOS_SEED.items():
        categoria = Categoria.objects.create(nome=nome, tipo_veiculo=tipo_do_grupo(nome))
        PrecoCategoria.objects.create(
            categoria=categoria,
            vigente_desde=VIGENTE_DESDE,
            diaria_centavos=diaria,
            semanal_centavos=semanal,
            mensal_centavos=mensal,
            caucao_centavos=caucao,
            alterado_por=alterado_por,
        )
        categorias[nome] = categoria
    return categorias
