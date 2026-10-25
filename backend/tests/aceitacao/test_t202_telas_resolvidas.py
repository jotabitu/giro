"""T-202 · Telas resolvidas (contratos da T-201): o andamento do assistente (`plataforma.md`,
`GET /api/implantacao/`), o nome curto da filial (`filiais.md`, FIL-01), os números da tela
Aprovações (`aprovacoes.md`, APR-12) e o evento da tabela de preço no seed (`auditoria.md`).

Roda na Moto Rápida da T-181 (Profissional, em teste, 07 out 2026).
"""

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.plataforma import selectors as plataforma_selectors
from apps.plataforma.models import UsoEmpresa

from .test_t014_clientes import _suporte
from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t181_configuracoes import _get, _resumo, moto_rapida  # noqa: F401 - fixture

IMPLANTACAO = "/api/implantacao/"
# O exemplo do contrato: 6 dos 10 passos da implantação, 5 dos 8 do assistente.
SEIS_PASSOS = {
    passo: "2026-10-07" for passo in ("conta", "marca", "filial", "ramo", "precos", "equipe")
}


def _passos(moto, passos: dict[str, str]) -> None:
    UsoEmpresa.objects.filter(empresa=moto.empresa).update(passos_implantacao=passos)


# --- Andamento do assistente (IMP-05) ---


def test_imp_05_andamento_do_assistente(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, SEIS_PASSOS)
    resposta = moto.api("Mariana").get(IMPLANTACAO)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["concluida"], corpo["total"], corpo["feitos"], corpo["proximo"]) == (
        False,
        8,
        5,
        "contrato",
    )
    assert [(p["passo"], p["numero"], p["rotulo"], p["feito"]) for p in corpo["passos"]] == [
        ("marca", 1, "Empresa e marca", True),
        ("filial", 2, "Primeira filial", True),
        ("ramo", 3, "O que a empresa faz", True),
        ("precos", 4, "Tabela de preços", True),
        ("contrato", 5, "Modelo de contrato", False),
        ("recebimentos", 6, "Recebimentos", False),
        ("importar", 7, "Importar dados", False),
        ("equipe", 8, "Convidar equipe", True),
    ]
    assert corpo["passos"][0]["feito_em"] == "2026-10-07"
    assert corpo["passos"][4]["feito_em"] is None


def test_imp_05_andamento_sem_recebimentos_tem_7_passos(moto_rapida, monkeypatch):  # noqa: F811
    # O Essencial não tem `recebimento_parceiro` (PLT-12): simulado sem trocar o plano.
    monkeypatch.setattr(plataforma_selectors, "assistente_tem_recebimentos", lambda _plano: False)
    _passos(moto_rapida.moto, {**SEIS_PASSOS, "recebimentos": "2026-10-07"})
    corpo = moto_rapida.moto.api("Mariana").get(IMPLANTACAO).json()
    assert corpo["total"] == 7
    assert [p["passo"] for p in corpo["passos"]][5:] == ["importar", "equipe"]
    assert corpo["passos"][5]["numero"] == 6  # "Passo 6 de 7"
    assert corpo["feitos"] == 5  # o `recebimentos` guardado não conta, e continua guardado


def test_imp_05_andamento_concluido_e_proximo_nulo(moto_rapida):  # noqa: F811
    todos = {p: "2026-10-07" for p, _ in plataforma_selectors.PASSOS_DO_ASSISTENTE}
    _passos(moto_rapida.moto, {**todos, "primeira_locacao": "2026-10-07"})
    corpo = moto_rapida.moto.api("Mariana").get(IMPLANTACAO).json()
    assert (corpo["concluida"], corpo["feitos"], corpo["proximo"]) == (True, 8, None)


def test_imp_05_pular_nao_marca_passo(moto_rapida):  # noqa: F811
    # Não há rota de pular: ler o andamento não muda nada.
    _passos(moto_rapida.moto, {"conta": "2026-10-07"})
    api = moto_rapida.moto.api("Mariana")
    assert api.get(IMPLANTACAO).json()["proximo"] == "marca"
    assert api.post(f"{IMPLANTACAO}pular/").status_code == 404
    assert api.get(IMPLANTACAO).json()["feitos"] == 0


@pytest.mark.parametrize("quem", ["Rodrigo", "Bruna", "João", "Lúcia"])
def test_imp_05_andamento_so_do_administrador(moto_rapida, quem):  # noqa: F811
    assert moto_rapida.moto.api(quem).get(IMPLANTACAO).status_code == 403


def test_imp_05_andamento_para_o_suporte(moto_rapida, relogio_jwt):  # noqa: F811
    resposta = _suporte(moto_rapida.moto, "ver").get(IMPLANTACAO)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["total"] == 8


# --- Nome curto da filial (FIL-01) e preço do litro (DEV-01) ---


def _filial(moto_rapida, dados, quem: str = "Mariana"):  # noqa: F811
    centro = moto_rapida.frota.centro
    return moto_rapida.moto.api(quem).patch(f"/api/filiais/{centro.pk}/", dados, format="json")


def test_fil_01_nome_curto(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    resposta = _filial(moto_rapida, {"nome_curto": "  Centro "})
    assert resposta.status_code == 200, resposta.json()
    assert (resposta.json()["nome"], resposta.json()["nome_curto"]) == ("Filial Centro", "Centro")

    minhas = moto.api("Rodrigo").get("/api/filiais/minhas/").json()["resultados"]
    assert [(f["nome"], f["nome_curto"]) for f in minhas] == [("Filial Centro", "Centro")]
    assert moto.api("Rodrigo").get("/api/auth/eu/").json()["filiais"] == [
        {"id": moto_rapida.frota.centro.pk, "nome": "Filial Centro", "nome_curto": "Centro"}
    ]
    usuarios = moto.api("Mariana").get("/api/usuarios/").json()["resultados"]
    rodrigo = next(u for u in usuarios if u["email"] == "rodrigo@motorapida.com.br")
    assert [f["nome_curto"] for f in rodrigo["filiais"]] == ["Centro"]
    assert _resumo(_get(moto_rapida), "filiais") == "1 filial · Centro, Fortaleza"

    # Sem nome curto vale o nome (CA-FIL-02); vazio guarda nada e sai `null` no formulário.
    vazio = _filial(moto_rapida, {"nome_curto": "   "})
    assert vazio.json()["nome_curto"] is None
    minhas = moto.api("Rodrigo").get("/api/filiais/minhas/").json()["resultados"]
    assert minhas[0]["nome_curto"] == "Filial Centro"
    assert _resumo(_get(moto_rapida), "filiais") == "1 filial · Filial Centro, Fortaleza"

    longo = _filial(moto_rapida, {"nome_curto": "C" * 31})
    assert longo.status_code == 400
    assert longo.json()["campos"] == {"nome_curto": ["Use até 30 caracteres."]}


def test_dev_01_preco_litro_pelo_administrador(moto_rapida):  # noqa: F811
    assert _filial(moto_rapida, {"preco_litro_centavos": 590}, quem="Rodrigo").status_code == 403
    zero = _filial(moto_rapida, {"preco_litro_centavos": 0})
    assert zero.status_code == 400
    assert zero.json()["campos"] == {"preco_litro_centavos": ["Informe um preço maior que zero."]}

    assert _filial(moto_rapida, {"preco_litro_centavos": 550}).status_code == 200
    assert _filial(moto_rapida, {"preco_litro_centavos": 590}).json()["preco_litro_centavos"] == 590
    evento = EventoAuditoria.objects.filter(acao="filial.editar").latest("id")
    assert (evento.antes, evento.depois) == (
        {"preco_litro_centavos": 550},
        {"preco_litro_centavos": 590},
    )
    lista = moto_rapida.moto.api("Mariana").get("/api/auditoria/eventos/").json()["resultados"]
    item = next(e for e in lista if e["id"] == evento.pk)
    assert (item["resumo"], item["detalhe"]) == (
        "Mudou o preço do litro",
        "Filial Centro · R$ 5,50 → R$ 5,90",
    )
    # O acerto lê o preço da filial na hora (`vistorias.services`): vale para o próximo.
    moto_rapida.frota.centro.refresh_from_db()
    assert moto_rapida.frota.centro.preco_litro_centavos == 590
