"""T-129 · Marca da empresa (`docs/api/empresas.md`; ADR 0002 e 0004; S-12).

As cores derivadas seguem a fórmula do design-system (`giro-produto/cores-da-marca.md`, 10 out
2026): cor sobre a marca pelo contraste WCAG; cores suaves em OKLCH (L 0,96 e 0,31, croma
0,31 x o da marca, mesmo matiz). Para a cor padrão, os valores fixos do `wl-theme.css`.
"""

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile

from apps.contas.models import Usuario
from apps.empresas import marca, selectors
from apps.empresas.models import ConfiguracaoEmpresa
from comum.empresa import nome_da_empresa

from .conftest import HOST_PLATAFORMA, cliente
from .test_t012_filiais import HOST, MotoRapida

MARCA = "/api/marca/"
LOGO = "/api/marca/logo/"
SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 36">'
    b'<rect width="120" height="36"/></svg>'
)

# Os três exemplos conferidos pelo design-system: (cor, sobre, suave, suave escuro).
EXEMPLOS = [
    ("#C8F04A", "#111114", "#EEF9CC", "#2B3510"),  # padrão: valores fixos do wl-theme.css
    ("#1D4ED8", "#FFFFFF", "#DBF2FF", "#1F2F52"),
    ("#C62828", "#FFFFFF", "#FFE3DC", "#4A2320"),
]
# As seis cores do Onboarding-Marca e o texto sobre cada uma.
ONBOARDING = {
    "#C8F04A": "#111114",
    "#FF7A45": "#111114",
    "#2F6FED": "#FFFFFF",
    "#16B8A6": "#111114",
    "#E11D48": "#FFFFFF",
    "#7A5AF8": "#FFFFFF",
}


# --- empresas/marca.py (funções puras) ---


@pytest.mark.parametrize(("cor", "sobre", "suave", "escuro"), EXEMPLOS)
def test_imp_marca_cores_derivadas_dos_exemplos_do_design_system(cor, sobre, suave, escuro):
    assert marca.cores(cor) == {
        "cor": cor,
        "cor_sobre": sobre,
        "cor_suave": suave,
        "cor_suave_escuro": escuro,
    }


def test_imp_marca_cor_padrao_reproduz_o_wl_theme_e_a_regra_da_o_mesmo_escuro():
    # O escuro da regra bate exato com o wl-theme.css; o claro da regra seria #EBF9CD.
    assert marca._suave("#C8F04A", marca.L_SUAVE_ESCURO) == "#2B3510"
    assert marca._suave("#C8F04A", marca.L_SUAVE) == "#EBF9CD"
    assert marca.cores(None)["cor_suave"] == "#EEF9CC"


@pytest.mark.parametrize(("cor", "sobre"), ONBOARDING.items())
def test_imp_marca_seis_cores_do_onboarding(cor, sobre):
    cores = marca.cores(cor.lower())
    assert cores["cor"] == cor  # maiúsculas
    assert cores["cor_sobre"] == sobre
    assert marca.contraste(cor, sobre) >= 4.5
    # Texto sobre as cores suaves: ink no claro e #F4F4F6 no escuro, bem acima de 7:1.
    assert marca.contraste(marca.INK, cores["cor_suave"]) >= 7
    assert marca.contraste("#F4F4F6", cores["cor_suave_escuro"]) >= 7
    assert all(marca.FORMATO.match(cores[c]) for c in cores)


def test_imp_marca_iniciais():
    assert marca.iniciais("Moto Rápida") == "MR"
    assert marca.iniciais("Casa das Motos e Carros") == "CM"
    assert marca.iniciais("Locadora") == "LO"


# --- GET /api/marca/ e GET /api/marca/logo/ ---


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


def _publico():
    return cliente(HOST)


def _configurar(**campos) -> ConfiguracaoEmpresa:
    configuracao, _ = ConfiguracaoEmpresa.objects.update_or_create(unica=1, defaults=campos)
    cache.delete(selectors.chave_da_marca())  # o serviço de escrita da marca fará isto
    return configuracao


def test_imp_marca_sem_configuracao_responde_o_padrao(moto):
    resposta = _publico().get(MARCA)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert {k: v for k, v in corpo.items() if k != "versao"} == {
        "nome_exibicao": "Empresa A",  # o nome da compra
        "iniciais": "EA",
        "logo": None,
        "cor": "#C8F04A",
        "cor_sobre": "#111114",
        "cor_suave": "#EEF9CC",
        "cor_suave_escuro": "#2B3510",
        "personalizada": False,
    }
    assert len(corpo["versao"]) == 8
    assert resposta["ETag"] == f'"{corpo["versao"]}"'
    assert resposta["Cache-Control"] == "public, max-age=300"


def test_imp_marca_etag_responde_304(moto):
    versao = _publico().get(MARCA).json()["versao"]
    mesma = _publico().get(MARCA, HTTP_IF_NONE_MATCH=f'"{versao}"')
    assert mesma.status_code == 304
    assert mesma.content == b""
    assert mesma["ETag"] == f'"{versao}"'
    assert _publico().get(MARCA, HTTP_IF_NONE_MATCH='"antiga00"').status_code == 200


def test_imp_marca_com_token_e_igual_e_no_host_da_plataforma_nao_existe(moto):
    sem = _publico().get(MARCA).json()
    assert moto.api("Bruna").get(MARCA).json() == sem
    assert cliente(HOST_PLATAFORMA).get(MARCA).status_code == 404


def test_imp_marca_personalizada_com_logo(moto):
    antes = _publico().get(MARCA).json()["versao"]
    configuracao = _configurar(
        nome_exibicao="Moto Rápida", cor_marca="#1D4ED8", logo_largura=120, logo_altura=36
    )
    configuracao.logo.save("logo.svg", ContentFile(SVG))
    cache.delete(selectors.chave_da_marca())
    corpo = _publico().get(MARCA).json()
    assert corpo["versao"] != antes
    assert corpo["nome_exibicao"] == "Moto Rápida"
    assert corpo["iniciais"] == "MR"
    assert (corpo["cor"], corpo["cor_sobre"], corpo["cor_suave"], corpo["cor_suave_escuro"]) == (
        "#1D4ED8",
        "#FFFFFF",
        "#DBF2FF",
        "#1F2F52",
    )
    assert corpo["logo"] == {
        "url": f"/api/marca/logo/?v={corpo['versao']}",
        "largura": 120,
        "altura": 36,
    }
    assert corpo["personalizada"] is True


def test_s_12_logo_servido_pela_api_com_os_cabecalhos(moto):
    configuracao = _configurar(cor_marca="#C62828")
    configuracao.logo.save("logo.svg", ContentFile(SVG))
    cache.delete(selectors.chave_da_marca())
    versao = _publico().get(MARCA).json()["versao"]

    atual = _publico().get(LOGO, {"v": versao})
    assert atual.status_code == 200
    assert atual.content == SVG
    assert atual["Content-Type"] == "image/svg+xml"
    assert atual["Cache-Control"] == "public, max-age=31536000, immutable"
    assert atual["X-Content-Type-Options"] == "nosniff"
    assert atual["Content-Security-Policy"] == (
        "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    )
    assert atual["Content-Disposition"] == 'inline; filename="logo.svg"'

    # Versão antiga ou sem versão: o logo atual, com cache curto (e-mail antigo).
    for parametros in ({"v": "antiga00"}, {}):
        antiga = _publico().get(LOGO, parametros)
        assert antiga.status_code == 200
        assert antiga["Cache-Control"] == "public, max-age=300"


def test_s_12_sem_logo_responde_404(moto):
    resposta = _publico().get(LOGO)
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "nao_encontrado"


def test_imp_marca_limite_de_120_por_minuto_por_ip(moto):
    api = cliente(HOST)
    api.credentials(HTTP_X_FORWARDED_FOR="200.10.20.30")
    codigos = [api.get(MARCA).status_code for _ in range(121)]
    assert codigos[:120] == [200] * 120
    assert codigos[120] == 429
    # Outro IP não é afetado.
    outro = cliente(HOST)
    outro.credentials(HTTP_X_FORWARDED_FOR="200.10.20.31")
    assert outro.get(MARCA).status_code == 200


# --- O nome da marca nos outros apps (comum.empresa) ---


def test_usr_02_nome_da_marca_no_eu_no_autenticador_e_na_senha(moto):
    _configurar(nome_exibicao="Moto Rápida")
    assert nome_da_empresa() == "Moto Rápida"
    assert moto.api("Bruna").get("/api/auth/eu/").json()["empresa"]["nome_exibicao"] == (
        "Moto Rápida"
    )
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError) as erro:
        validate_password("moto rápida", Usuario(email="bruna@motorapida.com.br"))
    assert "senha_e_empresa" in {e.code for e in erro.value.error_list}
