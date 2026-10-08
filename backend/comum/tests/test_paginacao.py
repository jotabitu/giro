"""Envelope de lista com extras (ponto 6 da T-045)."""

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from comum.paginacao import PaginacaoPorCursor, envelope_sem_paginas


def _paginacao() -> PaginacaoPorCursor:
    paginacao = PaginacaoPorCursor()
    paginacao.request = Request(APIRequestFactory().get("/api/x/"))
    paginacao.has_next = paginacao.has_previous = False
    paginacao.base_url = "http://testserver/api/x/"
    return paginacao


def test_extras_vao_no_mesmo_corpo():
    resposta = _paginacao().get_paginated_response([1], extras={"contagens": {"todas": 1}})
    assert resposta.data == {
        "contagens": {"todas": 1},
        "resultados": [1],
        "proximo": None,
        "anterior": None,
    }


def test_sem_extras_continua_igual():
    assert set(_paginacao().get_paginated_response([]).data) == {
        "resultados",
        "proximo",
        "anterior",
    }


@pytest.mark.parametrize("chave", ["resultados", "proximo", "anterior"])
def test_extra_nao_troca_o_envelope(chave):
    with pytest.raises(ValueError):
        _paginacao().get_paginated_response([], extras={chave: "x"})
    with pytest.raises(ValueError):
        envelope_sem_paginas([], extras={chave: "x"})


def test_lista_sem_paginas_tem_o_mesmo_envelope():
    assert envelope_sem_paginas([1, 2], {"indicadores": {}}).data == {
        "indicadores": {},
        "resultados": [1, 2],
        "proximo": None,
        "anterior": None,
    }
