"""T-341: "Continuar implantação" pelo `proximo` do assistente e placa com hífen nos textos
(`docs/api/configuracoes.md`, `docs/api/README.md`, T-340; IMP-05, PLT-12, FIN-16)."""

import pytest

from apps.contratos.marcadores import EXEMPLOS
from apps.locacoes import contrato as contrato_da_locacao
from apps.plataforma import selectors as plataforma_selectors
from apps.relatorios import configuracoes as textos
from comum.documentos import placa_com_hifen

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t016_vistorias import _abrir_devolucao, da_carteira, juliana  # noqa: F401 - fixture
from .test_t181_configuracoes import _get, _passos, moto_rapida  # noqa: F401 - fixture

SEIS = ("conta", "marca", "filial", "ramo", "precos", "equipe")
NOVA_LOCACAO = {"rotulo": "Fazer uma locação de teste", "destino": "nova_locacao"}


def _continuar(passo: str) -> dict[str, str]:
    return {"rotulo": "Continuar implantação", "destino": "implantacao", "passo": passo}


@pytest.fixture
def essencial(monkeypatch):
    # O Essencial não tem `recebimento_parceiro` (PLT-12): simulado sem trocar o plano.
    monkeypatch.setattr(plataforma_selectors, "assistente_tem_recebimentos", lambda _plano: False)


# --- Continuar implantação (configuracoes.md, tabela de exemplos) ---


def test_imp_05_continuar_implantacao_pelo_proximo(moto_rapida):  # noqa: F811
    _passos(*SEIS)
    implantacao = _get(moto_rapida)["implantacao"]
    assert implantacao["titulo"] == "Implantação concluída em 6 de 10 passos"
    assert implantacao["acao"] == _continuar("contrato")
    # O mesmo `proximo` do assistente (`GET /api/implantacao/`).
    assistente = moto_rapida.moto.api("Mariana").get("/api/implantacao/").json()
    assert assistente["proximo"] == implantacao["acao"]["passo"]


def test_imp_05_plt_12_essencial_sem_recebimentos(moto_rapida, essencial):  # noqa: F811
    _passos(*SEIS)
    implantacao = _get(moto_rapida)["implantacao"]
    assert (implantacao["concluidos"], implantacao["total"]) == (6, 9)
    assert implantacao["titulo"] == "Implantação concluída em 6 de 9 passos"
    assert implantacao["faltam"] == "Faltam contrato, importar dados e a 1ª locação."
    assert implantacao["acao"] == _continuar("contrato")


def test_imp_05_plt_12_essencial_pula_recebimentos(moto_rapida, essencial):  # noqa: F811
    _passos(*SEIS, "contrato")
    assert _get(moto_rapida)["implantacao"]["acao"] == _continuar("importar")


def test_imp_05_oito_passos_do_assistente_feitos_vai_a_nova_locacao(moto_rapida):  # noqa: F811
    _passos(*(p for p, _ in plataforma_selectors.PASSOS_DO_ASSISTENTE), "conta")
    implantacao = _get(moto_rapida)["implantacao"]
    assert implantacao["faltam"] == "Falta a 1ª locação."
    assert implantacao["acao"] == NOVA_LOCACAO


def test_imp_05_so_conta_aberto_fica_sem_botao(moto_rapida):  # noqa: F811
    _passos(*(p for p, _ in plataforma_selectors.PASSOS_DO_ASSISTENTE))
    implantacao = _get(moto_rapida)["implantacao"]
    assert implantacao["faltam"] == "Faltam conta e acesso e a 1ª locação."
    assert implantacao["acao"] is None


def test_imp_05_textos_da_faixa_com_o_proximo():
    passos = [{"passo": p, "concluido_em": None} for p in textos.NOMES_DOS_PASSOS]
    com_proximo, sem_proximo = textos.implantacao(passos, "marca"), textos.implantacao(passos, None)
    assert com_proximo is not None and sem_proximo is not None
    assert com_proximo["acao"] == _continuar("marca")
    assert sem_proximo["acao"] is None


# --- Placa com hífen nos textos (docs/api/README.md, Convenções; FIN-16) ---


@pytest.mark.parametrize(
    ("guardada", "no_texto"),
    [
        ("PMZ3E17", "PMZ-3E17"),
        ("SAK1D39", "SAK-1D39"),
        ("pmz-3e17", "PMZ-3E17"),
        ("ABC12", "ABC12"),  # fora de 7 caracteres, sai como está
        ("", ""),
    ],
)
def test_fin_16_placa_com_hifen(guardada, no_texto):
    assert placa_com_hifen(guardada) == no_texto


def test_fin_16_placa_no_contrato_e_no_exemplo_do_marcador(juliana):  # noqa: F811
    placa = juliana.veiculo.placa
    assert "-" not in placa  # o campo guardado continua sem hífen
    assert contrato_da_locacao.valores(juliana)["veiculo.placa"] == f"{placa[:3]}-{placa[3:]}"
    assert EXEMPLOS["veiculo.placa"] == "SAK-1D39"


def test_fin_16_placa_no_texto_da_devolucao(cenario, juliana):  # noqa: F811
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    placa = juliana.veiculo.placa
    assert devolucao["locacao"]["veiculo"].endswith(f" · {placa[:3]}-{placa[3:]}")
