"""T-068: correções dos achados F-01, F-02, F-04 e F-05 da revisão de segurança T-064.

Relatório: docs/seguranca/2026-10-09-t058-t012.md. Cada teste reproduz o achado.
"""

from types import SimpleNamespace

import pytest

from apps.filiais import selectors, services
from apps.filiais.models import Filial, UsuarioFilial
from apps.plataforma.models import Empresa
from comum.erros import SemPermissao

from .conftest import HOST_PLATAFORMA, cliente
from .test_t012_filiais import CENTRO, _filial, moto  # noqa: F401 (fixture)

ENTRAR = "/api/plataforma/auth/entrar/"


# --- F-01: empresa sem operação não administra filial ---


@pytest.mark.parametrize("status", ["suspensa", "pausada", "cancelada"])
def test_plt_03_empresa_suspensa_nao_cria_nem_edita_filial(moto, status):  # noqa: F811
    centro = moto.centro()
    Empresa._base_manager.filter(pk=moto.empresa.pk).update(status=status)
    api = moto.api()

    escritas = [
        api.post("/api/filiais/", _filial("Filial Caucaia"), format="json"),
        api.patch(f"/api/filiais/{centro.pk}/", {"nome": "Outro nome"}, format="json"),
        api.post(f"/api/filiais/{centro.pk}/tornar-matriz/"),
        api.post(f"/api/filiais/{centro.pk}/desativar/", {"motivo": "Teste"}, format="json"),
        api.post(f"/api/filiais/{centro.pk}/reativar/", {"motivo": "Teste"}, format="json"),
        api.post(
            f"/api/filiais/{centro.pk}/feriados/",
            {"feriados": [{"data": "2026-12-25", "nome": "Natal"}]},
            format="json",
        ),
    ]
    for resposta in escritas:
        assert resposta.status_code == 403, resposta.wsgi_request.path
        assert resposta.json()["codigo"] == "empresa_sem_operacao"
    assert Filial.objects.count() == 1
    assert Filial.objects.get(pk=centro.pk).nome == CENTRO["nome"]
    assert api.get("/api/filiais/").status_code == 200  # ler continua


def test_usr_07_x_filial_fora_do_escopo_recusado_nas_rotas_de_administrar(moto):  # noqa: F811
    """`EscopoDeFilial` vale também nas views só do administrador."""
    centro = moto.centro()
    resposta = moto.api(HTTP_X_FILIAL="999999").get(f"/api/filiais/{centro.pk}/feriados/")
    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "USR-07")


# --- F-02: "todas" e "sem filial" não são o mesmo valor ---


def _requisicao(usuario, filial: str = ""):
    return SimpleNamespace(META={"HTTP_X_FILIAL": filial} if filial else {}, user=usuario)


def test_usr_07_pessoa_sem_filial_recebe_403(moto):  # noqa: F811
    centro = moto.centro()
    rodrigo = moto.pessoas["Rodrigo"]
    UsuarioFilial.objects.filter(usuario=rodrigo).delete()

    with pytest.raises(SemPermissao) as erro:
        selectors.filial_da_requisicao(_requisicao(rodrigo))
    assert (erro.value.codigo, erro.value.mensagem) == (
        "USR-07",
        "Você não tem acesso a nenhuma filial",
    )
    with pytest.raises(SemPermissao):
        selectors.filtrar_por_filial(Filial.objects.all(), _requisicao(rodrigo), campo="pk")

    # O seletor continua respondendo, com a lista vazia.
    minhas = moto.api("Rodrigo").get("/api/filiais/minhas/")
    assert minhas.status_code == 200
    assert minhas.json()["resultados"] == []
    # Com filial, a mesma chamada filtra só a dele.
    services.definir_filiais_do_usuario(rodrigo.pk, [centro.pk])
    assert list(
        selectors.filtrar_por_filial(Filial.objects.all(), _requisicao(rodrigo), campo="pk")
    ) == [centro]


def test_usr_07_todas_inclui_filiais_desativadas(moto):  # noqa: F811
    centro = moto.centro()
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])
    services.desativar(caucaia, "Ponto fechado")
    mariana = moto.pessoas["Mariana"]

    escopo = selectors.filial_da_requisicao(_requisicao(mariana, "todas"))
    assert isinstance(escopo, selectors.TodasAsFiliais)
    assert escopo.ids == frozenset({centro.pk, caucaia.pk})
    filtradas = selectors.filtrar_por_filial(
        Filial.objects.all(), _requisicao(mariana, "todas"), campo="pk"
    )
    assert set(filtradas) == {centro, caucaia}

    # A filial desativada não é escolhida sozinha, e o seletor só lista as ativas (USR-07).
    with pytest.raises(SemPermissao):
        selectors.filial_da_requisicao(_requisicao(mariana, str(caucaia.pk)))
    minhas = moto.api().get("/api/filiais/minhas/").json()["resultados"]
    assert [f["id"] for f in minhas] == [centro.pk]


# --- F-04: limite por IP sem chave vazia e com IPv6 por /64 ---


def _entrar_de(ip: str, email: str):
    api = cliente(HOST_PLATAFORMA)
    api.defaults["REMOTE_ADDR"] = ip
    return api.post(ENTRAR, {"email": email, "senha": "x"}, format="json")


def test_limite_por_ip_sem_ip_nao_junta_todos(db, caplog):
    for numero in range(12):
        resposta = _entrar_de("", f"pessoa{numero}@girolocadoras.com.br")
        assert resposta.status_code == 401, numero
    assert "limite por IP não aplicado" in caplog.text


def test_limite_por_ip_conta_ipv6_pelo_prefixo_64(db):
    for numero in range(1, 11):
        assert _entrar_de(f"2001:db8:1:1::{numero:x}", f"p{numero}@g.com").status_code == 401
    assert _entrar_de("2001:db8:1:1:ffff::1", "outra@g.com").status_code == 429
    assert _entrar_de("2001:db8:1:2::1", "vizinha@g.com").status_code == 401  # outro /64


# --- F-05: limite na busca de CEP ---


def test_busca_de_cep_com_limite_por_usuario(moto):  # noqa: F811
    api = moto.api("Bruna")
    for _ in range(30):
        assert api.get("/api/enderecos/cep/60325000/").status_code == 200
    estourou = api.get("/api/enderecos/cep/60325000/")
    assert estourou.status_code == 429
    assert estourou.json()["codigo"] == "muitas_requisicoes"
    assert moto.api("Rodrigo").get("/api/enderecos/cep/60325000/").status_code == 200
