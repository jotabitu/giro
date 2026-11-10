"""T-440 · Importação de veículos sem filial e sem categoria na planilha (IMP-08, IMP-02).

Critérios em docs/qa/criterios/T-440.md (CA-440-01 a 13); contrato em docs/api/importacao.md. A
planilha é a `frota-moto-rapida.xlsx` da T-027 sem as colunas categoria e filial: 86 linhas nos
7 modelos do seed (`MODELOS`), com os 3 erros do CA-027-03 nas linhas 14 (Pop 110i), 37 (Biz
125) e 52 (CG 160 Fan). O limite do plano (CA-440-13) segue em `test_imp_03_*` da T-027.
"""

import io
from typing import Any

import pytest
from openpyxl import load_workbook

from apps.veiculos.models import Categoria, Veiculo

from .frota import criar_categorias
from .test_t012_filiais import MotoRapida, _filial
from .test_t027_importacao import (  # noqa: F401
    COLUNAS_CLIENTE,
    COLUNAS_VEICULO,
    JULIANA,
    URL,
    _enviar,
    _frota,
    _frota_com_os_3_erros,
    _importar,
    _linhas,
    _rodando,
    _xlsx,
    escolher_categorias,
)

ESCOLHA = {
    "Pop 110i": "Urbana 110–125",
    "Biz 125": "Urbana 110–125",
    "CG 160 Fan": "Street 150–160",
    "Factor 150": "Street 150–160",
    "NMax 160": "Scooter premium",
    "Kwid": "Carro compacto",
    "Mobi": "Carro compacto",
}


@pytest.fixture
def moto(empresa_a, planos, relogio_jwt) -> MotoRapida:
    """Como na T-027: Filial Centro e as 4 categorias de `Precos`, nenhum veículo."""
    moto = MotoRapida(empresa_a, planos["Profissional"])
    moto.filial = moto.centro()
    moto.categorias = criar_categorias(moto.pessoas["Mariana"])
    return moto


def _enviada(moto, capturar, linhas: list[list[Any]] | None = None, **mais) -> int:
    resposta = _rodando(
        capturar,
        _enviar,
        moto.api(),
        _xlsx(COLUNAS_VEICULO, linhas if linhas is not None else _frota_com_os_3_erros()),
        **mais,
    )
    assert resposta.status_code == 202, resposta.json()
    return int(resposta.json()["id"])


def _corpo(moto, imp: int) -> dict[str, Any]:
    resposta = moto.api().get(f"{URL}{imp}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _escolher(moto, imp: int, escolha: dict[str, str]) -> Any:
    ids = {c["nome"]: c["id"] for c in _corpo(moto, imp)["categorias"]["opcoes"]}
    modelos = [
        {"marca": m["marca"], "modelo": m["modelo"], "categoria_id": ids[escolha[m["modelo"]]]}
        for m in _corpo(moto, imp)["categorias"]["modelos"]
        if m["modelo"] in escolha
    ]
    return moto.api().post(f"{URL}{imp}/categorias/", {"modelos": modelos}, format="json")


def _importar_direto(moto, capturar, imp: int) -> Any:
    """Sem a escolha automática do helper da T-027."""
    return _rodando(capturar, moto.api().post, f"{URL}{imp}/importar/", {}, format="json")


def _por_categoria() -> dict[str, int]:
    contagem: dict[str, int] = {}
    for nome in Veiculo.objects.values_list("categoria__nome", flat=True):
        contagem[nome] = contagem.get(nome, 0) + 1
    return contagem


def _messejana(moto) -> int:
    criada = moto.criar(_filial("Filial Messejana"))
    assert criada.status_code == 201, criada.json()
    return int(criada.json()["id"])


# --- Planilha (CA-440-01, 02) ---


def test_imp_08_modelo_sem_filial_e_categoria(moto) -> None:
    """CA-440-01: a planilha modelo de veículos não tem categoria nem filial."""
    resposta = moto.api().get(f"{URL}modelo/?tipo=veiculos")
    folha = load_workbook(io.BytesIO(resposta.content)).worksheets[0]
    assert [celula.value for celula in folha[1]] == [
        "placa",
        "chassi",
        "renavam",
        "marca",
        "modelo",
        "ano_fabricacao",
        "ano_modelo",
        "cor",
        "km",
        "capacidade_tanque_litros",
        "valor_compra",
        "data_compra",
    ]


def test_imp_08_planilha_antiga_ignora_as_colunas(moto, django_capture_on_commit_callbacks):
    """CA-440-02: "Scooter" (não existe) e "Filial Norte" são ignoradas; nenhuma linha fica com
    erro por elas, e a filial e a categoria seguem a escolha da tela."""
    linhas = [[*linha, "Scooter", "Filial Norte"] for linha in _frota(3)]
    resposta = _rodando(
        django_capture_on_commit_callbacks,
        _enviar,
        moto.api(),
        _xlsx([*COLUNAS_VEICULO, "categoria", "filial"], linhas),
    )
    imp = resposta.json()["id"]
    assert _corpo(moto, imp)["contagens"]["prontas"] == 3
    assert "categoria" not in _linhas(moto.api(), imp)[0]["dados"]
    assert _escolher(moto, imp, ESCOLHA).status_code == 200
    _importar_direto(moto, django_capture_on_commit_callbacks, imp)
    assert set(Veiculo.objects.values_list("filial_id", flat=True)) == {moto.filial.pk}
    assert _por_categoria() == {"Urbana 110–125": 3}


# --- Filial (CA-440-03, 04) ---


def test_imp_08_uma_filial_sem_pergunta(moto, django_capture_on_commit_callbacks):
    """CA-440-03: com só a Filial Centro, nada é perguntado e a conferência dá 83 e 3."""
    preparo = moto.api().get(f"{URL}preparo/").json()
    assert preparo == {
        "filiais": [{"id": moto.filial.pk, "nome": "Filial Centro"}],
        "pede_filial": False,
        "filial": {"id": moto.filial.pk, "nome": "Filial Centro"},
        "pode_importar": True,
        "motivo": None,
    }
    corpo = _corpo(moto, _enviada(moto, django_capture_on_commit_callbacks))
    assert corpo["filial_padrao"] == {"id": moto.filial.pk, "nome": "Filial Centro"}
    assert (corpo["contagens"]["prontas"], corpo["contagens"]["com_erro"]) == (83, 3)


def test_imp_08_mais_de_uma_filial(moto, django_capture_on_commit_callbacks):
    """CA-440-04: com duas filiais, "Filial dos veículos" sem nenhuma marcada; sem a escolha, o
    envio é recusado; com a Messejana, todos ficam nela."""
    messejana = _messejana(moto)
    preparo = moto.api().get(f"{URL}preparo/").json()
    assert preparo["pede_filial"] is True and preparo["filial"] is None
    assert [f["nome"] for f in preparo["filiais"]] == ["Filial Centro", "Filial Messejana"]
    sem = _enviar(moto.api(), _xlsx(COLUNAS_VEICULO, _frota(4)))
    assert sem.status_code == 400
    assert sem.json()["campos"] == {"filial_id": ["Escolha a filial dos veículos."]}
    imp = _enviada(moto, django_capture_on_commit_callbacks, _frota(4), filial_id=messejana)
    _importar(moto.api(), django_capture_on_commit_callbacks, imp)
    assert set(Veiculo.objects.values_list("filial_id", flat=True)) == {messejana}


# --- Categoria (CA-440-05 a 11) ---


def test_imp_08_categoria_de_cada_modelo(moto, django_capture_on_commit_callbacks):
    """CA-440-05 e 06: os 7 modelos com os prontos de cada um, as 4 categorias, "Importar"
    travado até a escolha; depois, cada veículo na categoria do modelo dele."""
    imp = _enviada(moto, django_capture_on_commit_callbacks)
    categorias = _corpo(moto, imp)["categorias"]
    assert categorias["pergunta"] is True
    assert categorias["falta_escolher"] is True
    assert [c["nome"] for c in categorias["opcoes"]] == [
        "Carro compacto",
        "Scooter premium",
        "Street 150–160",
        "Urbana 110–125",
    ]
    assert [
        (m["marca"], m["modelo"], m["veiculos"], m["categoria_id"]) for m in categorias["modelos"]
    ] == [
        ("Honda", "Pop 110i", 20, None),
        ("Honda", "Biz 125", 20, None),
        ("Honda", "CG 160 Fan", 15, None),
        ("Yamaha", "Factor 150", 16, None),
        ("Yamaha", "NMax 160", 6, None),
        ("Renault", "Kwid", 3, None),
        ("Fiat", "Mobi", 3, None),
    ]
    travado = _importar_direto(moto, django_capture_on_commit_callbacks, imp)
    assert travado.status_code == 422
    assert travado.json() == {
        "codigo": "categoria_do_modelo",
        "mensagem": "Escolha a categoria de cada modelo.",
        "detalhes": None,
    }
    escolhida = _escolher(moto, imp, ESCOLHA)
    assert escolhida.status_code == 200, escolhida.json()
    assert escolhida.json()["categorias"]["falta_escolher"] is False
    assert _importar_direto(moto, django_capture_on_commit_callbacks, imp).status_code == 202
    assert Veiculo.objects.filter(status="disponivel", filial=moto.filial).count() == 83
    assert _por_categoria() == {
        "Urbana 110–125": 40,
        "Street 150–160": 31,
        "Scooter premium": 6,
        "Carro compacto": 6,
    }


def test_imp_08_corrigidas_seguem_o_modelo(moto, django_capture_on_commit_callbacks):
    """CA-440-07: corrigidas as 3 e importadas sem escolher nada, ficam na categoria do modelo;
    86 veículos, 42 + 32 + 6 + 6, e os 6 carros no filtro de carros da Frota."""
    imp = _enviada(moto, django_capture_on_commit_callbacks)
    _escolher(moto, imp, ESCOLHA)
    _importar_direto(moto, django_capture_on_commit_callbacks, imp)
    for numero, dados in (
        (14, {"placa": "QXA4B21"}),
        (37, {"chassi": "9C2KC2210PR999999"}),
        (52, {"ano_modelo": "2024"}),
    ):
        linha = moto.api().patch(f"{URL}{imp}/linhas/{numero}/", {"dados": dados}, format="json")
        assert linha.json()["status"] == "pronta", linha.json()
        assert linha.json()["categoria_id"] is not None
    assert _corpo(moto, imp)["categorias"]["falta_escolher"] is False
    assert _importar_direto(moto, django_capture_on_commit_callbacks, imp).status_code == 202
    assert _por_categoria() == {
        "Urbana 110–125": 42,
        "Street 150–160": 32,
        "Scooter premium": 6,
        "Carro compacto": 6,
    }
    carros = moto.api("Rodrigo").get("/api/veiculos/", {"tipo_veiculo": "carro"}).json()
    assert carros["contagens"]["carros"] == 6


def test_imp_08_modelo_novo_na_correcao(moto, django_capture_on_commit_callbacks):
    """CA-440-08: a linha 52 corrigida para "Honda Elite 125" pede a categoria desse modelo."""
    imp = _enviada(moto, django_capture_on_commit_callbacks)
    _escolher(moto, imp, ESCOLHA)
    corrigida = moto.api().patch(
        f"{URL}{imp}/linhas/52/",
        {"dados": {"modelo": "Elite 125", "ano_modelo": "2024"}},
        format="json",
    )
    assert corrigida.json()["status"] == "pronta"
    assert corrigida.json()["categoria_id"] is None
    categorias = _corpo(moto, imp)["categorias"]
    elite = [m for m in categorias["modelos"] if m["modelo"] == "Elite 125"]
    assert elite == [{"marca": "Honda", "modelo": "Elite 125", "veiculos": 1, "categoria_id": None}]
    assert categorias["falta_escolher"] is True
    assert _importar_direto(moto, django_capture_on_commit_callbacks, imp).status_code == 422
    assert _escolher(moto, imp, {"Elite 125": "Urbana 110–125"}).status_code == 200
    assert _importar_direto(moto, django_capture_on_commit_callbacks, imp).status_code == 202
    assert Veiculo.objects.get(modelo="Elite 125").categoria.nome == "Urbana 110–125"


def test_imp_08_excecao_numa_linha(moto, django_capture_on_commit_callbacks):
    """CA-440-09: uma CG 160 Fan na Urbana em "Corrigir aqui"; as outras, na Street. A marca e
    o modelo se comparam sem maiúsculas, acentos e espaços."""
    imp = _enviada(moto, django_capture_on_commit_callbacks)
    urbana = moto.categorias["Urbana 110–125"].pk
    excecao = moto.api().patch(f"{URL}{imp}/linhas/45/", {"categoria_id": urbana}, format="json")
    assert excecao.status_code == 200, excecao.json()
    assert (excecao.json()["categoria_id"], excecao.json()["categoria_propria"]) == (urbana, True)
    _escolher(moto, imp, ESCOLHA)
    cg = next(m for m in _corpo(moto, imp)["categorias"]["modelos"] if m["modelo"] == "CG 160 Fan")
    assert cg["veiculos"] == 14  # a exceção sai da conta do modelo
    # A linha 52 (CG) corrigida com o modelo escrito de outro jeito segue o modelo dela.
    corrigida = moto.api().patch(
        f"{URL}{imp}/linhas/52/",
        {"dados": {"modelo": "cg  160 FAN", "ano_modelo": "2024"}},
        format="json",
    )
    assert corrigida.json()["categoria_id"] == moto.categorias["Street 150–160"].pk
    _importar_direto(moto, django_capture_on_commit_callbacks, imp)
    cgs = Veiculo.objects.filter(modelo__iexact="CG 160 Fan")
    assert cgs.get(placa="QAA0043").categoria.nome == "Urbana 110–125"
    assert {v.categoria.nome for v in cgs.exclude(placa="QAA0043")} == {"Street 150–160"}


def test_imp_08_uma_categoria_so(moto, django_capture_on_commit_callbacks):
    """CA-440-10: com só a Street ativa, nada é perguntado e "Importar" já fica liberado."""
    Categoria.objects.exclude(nome="Street 150–160").update(ativo=False)
    imp = _enviada(moto, django_capture_on_commit_callbacks)
    categorias = _corpo(moto, imp)["categorias"]
    assert (categorias["pergunta"], categorias["falta_escolher"]) == (False, False)
    assert _importar_direto(moto, django_capture_on_commit_callbacks, imp).status_code == 202
    assert _por_categoria() == {"Street 150–160": 83}


def test_imp_08_categoria_de_outra_filial(moto, django_capture_on_commit_callbacks):
    """CA-440-11: a "Street Messejana" só aparece na importação para a Filial Messejana."""
    messejana = _messejana(moto)
    Categoria.objects.create(nome="Street Messejana", tipo_veiculo="moto", filial_id=messejana)
    centro = _enviada(moto, django_capture_on_commit_callbacks, _frota(2), filial_id=moto.filial.pk)
    nomes = [c["nome"] for c in _corpo(moto, centro)["categorias"]["opcoes"]]
    assert "Street Messejana" not in nomes
    rua = Categoria.objects.get(nome="Street Messejana").pk
    modelo = {"marca": "Honda", "modelo": "Pop 110i", "categoria_id": rua}
    recusa = moto.api().post(f"{URL}{centro}/categorias/", {"modelos": [modelo]}, format="json")
    assert recusa.status_code == 400
    moto.api().post(f"{URL}{centro}/cancelar/", {}, format="json")
    outra = _enviada(moto, django_capture_on_commit_callbacks, _frota(2), filial_id=messejana)
    nomes = [c["nome"] for c in _corpo(moto, outra)["categorias"]["opcoes"]]
    assert len(nomes) == 5 and "Street Messejana" in nomes


def test_imp_08_sem_categoria_nao_comeca(moto, django_capture_on_commit_callbacks):
    """CA-440-12: sem categoria ativa, a de veículos não começa; a de clientes, sim."""
    Categoria.objects.update(ativo=False)
    preparo = moto.api().get(f"{URL}preparo/").json()
    assert preparo["pode_importar"] is False
    assert preparo["motivo"] == "Cadastre os preços antes de importar veículos."
    recusa = _enviar(moto.api(), _xlsx(COLUNAS_VEICULO, _frota(2)))
    assert recusa.status_code == 422
    assert recusa.json()["codigo"] == "sem_categoria"
    assert recusa.json()["mensagem"] == "Cadastre os preços antes de importar veículos."
    clientes = _enviar(moto.api(), _xlsx(COLUNAS_CLIENTE, [JULIANA]), "c.xlsx", "clientes")
    assert clientes.status_code == 202


def test_imp_08_categoria_inativada_depois_da_escolha(moto, django_capture_on_commit_callbacks):
    """A categoria escolhida desativada antes de importar: a linha volta com erro."""
    imp = _enviada(moto, django_capture_on_commit_callbacks, _frota(2))
    _escolher(moto, imp, ESCOLHA)
    Categoria.objects.filter(nome="Urbana 110–125").update(ativo=False)
    resposta = _importar_direto(moto, django_capture_on_commit_callbacks, imp)
    assert resposta.status_code == 422  # sem categoria válida, "Importar" segue travado
    assert resposta.json()["codigo"] == "categoria_do_modelo"


@pytest.mark.parametrize("quem", ["Rodrigo", "Bruna"])
def test_imp_08_so_administrador_escolhe(moto, quem, django_capture_on_commit_callbacks):
    imp = _enviada(moto, django_capture_on_commit_callbacks, _frota(1))
    resposta = moto.api(quem).post(f"{URL}{imp}/categorias/", {"modelos": []}, format="json")
    assert resposta.status_code == 403
    assert moto.api(quem).get(f"{URL}preparo/").status_code == 403
