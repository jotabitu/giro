"""Registro de leituras compostas (ADR 0015)."""

from types import SimpleNamespace

from comum import leituras


def test_contador_ausente_vale_zero():
    leituras.registrar_contador("teste.Alvo", "a", lambda pk: pk * 2)
    try:
        assert leituras.contar("teste.Alvo", 3, ["a", "b"]) == {"a": 6, "b": 0}
    finally:
        leituras.remover_contador("teste.Alvo", "a")


def test_blocos_juntam_os_fornecedores():
    def nada(qs):
        return qs

    leituras.registrar_anotacao("teste.Bloco", "indicadores", nada, lambda o: {"x": o.x})
    leituras.registrar_anotacao("teste.Bloco", "indicadores", nada, lambda o: {"y": 2})
    leituras.registrar_anotacao("teste.Bloco", "vazio", nada, lambda o: None)
    assert leituras.blocos("teste.Bloco", SimpleNamespace(x=1)) == {"indicadores": {"x": 1, "y": 2}}


def test_filtro_sem_fornecedor_e_none_e_registrado_e_devolvido():
    """ADR 0015: `com_locacao` e `em_aberto` da lista de clientes chegam por aqui."""
    assert leituras.filtro("teste.Alvo", "com_locacao") is None

    def filtrar(qs):
        return qs

    leituras.registrar_filtro("teste.Alvo", "com_locacao", filtrar)
    try:
        assert leituras.filtro("teste.Alvo", "com_locacao") is filtrar
    finally:
        leituras.remover_filtro("teste.Alvo", "com_locacao")
    assert leituras.filtro("teste.Alvo", "com_locacao") is None
