import pytest

from comum import eventos
from tests.app_exemplo.models import Pedido


def test_assinantes_rodam_em_ordem_de_registro(db):
    chamadas: list[str] = []

    def primeiro(**dados: object) -> None:
        chamadas.append(f"1:{dados['parcela_id']}")

    def segundo(**dados: object) -> None:
        chamadas.append(f"2:{dados['parcela_id']}")

    eventos.assinar("teste.algo_aconteceu", primeiro)
    eventos.assinar("teste.algo_aconteceu", segundo)
    eventos.assinar("teste.algo_aconteceu", primeiro)  # registrar de novo não duplica
    try:
        eventos.publicar("teste.algo_aconteceu", parcela_id=9)
    finally:
        eventos.remover_assinante("teste.algo_aconteceu", primeiro)
        eventos.remover_assinante("teste.algo_aconteceu", segundo)
    assert chamadas == ["1:9", "2:9"]


def test_falha_de_assinante_volta_a_transacao_toda(empresa_a):
    def grava(**dados: object) -> None:
        Pedido.objects.create(cliente="Gravado pelo assinante")

    def falha(**dados: object) -> None:
        raise RuntimeError("assinante falhou")

    eventos.assinar("teste.pedido_criado", grava)
    eventos.assinar("teste.pedido_criado", falha)
    try:
        with pytest.raises(RuntimeError):
            eventos.publicar("teste.pedido_criado")
    finally:
        eventos.remover_assinante("teste.pedido_criado", grava)
        eventos.remover_assinante("teste.pedido_criado", falha)
    assert not Pedido.objects.filter(cliente="Gravado pelo assinante").exists()


def test_nome_de_evento_fora_do_padrao_e_recusado():
    with pytest.raises(ValueError):
        eventos.publicar("ParcelaPaga")
