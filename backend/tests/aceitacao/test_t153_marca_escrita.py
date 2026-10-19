"""T-153 · Escrita da marca (`docs/api/empresas.md`, "Escrita da marca"; ADR 0022; IMP-05, S-12).

`PATCH /api/marca/` (multipart e JSON, só o administrador) e `POST /api/marca/simular/`. Os
vetores do SVG e do PNG, um a um, estão em `apps/empresas/tests/test_logo.py`; aqui, o caminho
pela API, a auditoria, o cache, o storage e o passo da implantação.
"""

import io
import logging

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.auditoria.models import EventoAuditoria
from apps.empresas import selectors, services
from apps.plataforma.models import Empresa, UsoEmpresa
from comum import arquivos
from comum.erros import ErroDeValidacao

from .test_t014_clientes import _suporte
from .test_t129_marca import LOGO, MARCA, SVG, _publico, moto  # noqa: F401 - fixture

SIMULAR = "/api/marca/simular/"

# A tabela "As seis cores do Onboarding-Marca" (`empresas.md`, "Dados").
SEIS_CORES = [
    ("#C8F04A", "#111114", "#EEF9CC", "#2B3510"),
    ("#FF7A45", "#111114", "#FFE7D6", "#47261A"),
    ("#2F6FED", "#FFFFFF", "#DBF3FF", "#1E3050"),
    ("#16B8A6", "#111114", "#D7FBF4", "#183732"),
    ("#E11D48", "#FFFFFF", "#FFE0E1", "#4D2023"),
    ("#7A5AF8", "#FFFFFF", "#EEECFF", "#2E2A51"),
]


def _patch(moto, dados, quem: str = "Mariana", formato: str = "multipart", **extra):  # noqa: F811
    return moto.api(quem, **extra).patch(MARCA, dados, format=formato)


def _arquivo(conteudo: bytes, nome: str = "logo.svg") -> SimpleUploadedFile:
    return SimpleUploadedFile(nome, conteudo, content_type="application/octet-stream")


def _png() -> bytes:
    saida = io.BytesIO()
    Image.new("RGBA", (30, 10), (47, 111, 237, 255)).save(saida, format="PNG")
    return saida.getvalue()


def _eventos() -> int:
    return EventoAuditoria.objects.filter(acao="empresa.alterar_marca").count()


# --- Simulação (ADR 0005) ---


@pytest.mark.parametrize(("cor", "sobre", "suave", "escuro"), SEIS_CORES)
def test_marca_simular_seis_cores(moto, cor, sobre, suave, escuro):  # noqa: F811
    resposta = moto.api().post(SIMULAR, {"cor": cor.lower()}, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json() == {
        "nome_exibicao": "Empresa A",
        "iniciais": "EA",
        "cor": cor,
        "cor_sobre": sobre,
        "cor_suave": suave,
        "cor_suave_escuro": escuro,
    }


def test_marca_simular_nao_grava_e_volta_ao_padrao(moto):  # noqa: F811
    services.salvar_marca(nome_exibicao="Moto Rápida", cor="#2F6FED")
    api = moto.api()
    corpo = api.post(SIMULAR, {"nome_exibicao": "Casa das Motos"}, format="json").json()
    assert (corpo["nome_exibicao"], corpo["iniciais"], corpo["cor"]) == (
        "Casa das Motos",
        "CM",
        "#2F6FED",
    )
    padrao = api.post(SIMULAR, {"cor": "", "nome_exibicao": ""}, format="json").json()
    assert (padrao["nome_exibicao"], padrao["cor"], padrao["cor_suave"]) == (
        "Empresa A",
        "#C8F04A",
        "#EEF9CC",
    )
    assert selectors.configuracao().nome_exibicao == "Moto Rápida"
    erro = api.post(SIMULAR, {"cor": "azul"}, format="json")
    assert erro.status_code == 400
    assert erro.json()["campos"] == {"cor": ["Use uma cor no formato #RRGGBB."]}


# --- PATCH /api/marca/ ---


def test_imp_05_salvar_marca_marca_o_passo(moto):  # noqa: F811
    resposta = _patch(moto, {"cor": "#ff7a45", "logo": _arquivo(SVG)})
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["cor"] == "#FF7A45" and corpo["personalizada"] is True
    assert corpo["logo"]["largura"] == 120 and corpo["logo"]["altura"] == 36
    passos = UsoEmpresa.objects.get(empresa=moto.empresa).passos_implantacao
    assert "marca" in passos

    evento = EventoAuditoria.objects.get(acao="empresa.alterar_marca")
    assert evento.categoria == "configuracoes"
    assert evento.antes["cor_marca"] == "" and evento.depois["cor_marca"] == "#FF7A45"
    assert evento.antes["logo"] is None
    assert evento.depois["logo"].endswith(".svg") and "/marca/logo-" in evento.depois["logo"]
    assert "<svg" not in str(evento.depois)


def test_marca_patch_invalida_cache_e_versao(moto, django_capture_on_commit_callbacks):  # noqa: F811
    antiga = _publico().get(MARCA).json()["versao"]
    assert cache.get(selectors.chave_da_marca()) is not None

    with django_capture_on_commit_callbacks(execute=True):
        resposta = _patch(moto, {"nome_exibicao": " Moto Rápida "}, formato="json")
    assert resposta.status_code == 200, resposta.json()
    nova = resposta.json()["versao"]
    assert nova != antiga
    assert resposta["ETag"] == f'"{nova}"'
    assert resposta.json()["nome_exibicao"] == "Moto Rápida"
    assert resposta.json()["iniciais"] == "MR"

    lida = _publico().get(MARCA, HTTP_IF_NONE_MATCH=f'"{antiga}"')
    assert lida.status_code == 200
    assert lida.json()["versao"] == nova
    assert _publico().get(MARCA, HTTP_IF_NONE_MATCH=f'"{nova}"').status_code == 304


def test_marca_patch_sem_mudanca_nao_grava_evento_nem_muda_versao(moto):  # noqa: F811
    primeira = _patch(moto, {"cor": "#2F6FED", "logo": _arquivo(SVG)}).json()
    assert _eventos() == 1
    for dados in ({}, {"cor": "#2f6fed"}, {"logo": _arquivo(SVG)}):
        resposta = _patch(moto, dados)
        assert resposta.status_code == 200, resposta.json()
        assert resposta.json()["versao"] == primeira["versao"]
    assert _eventos() == 1


@pytest.mark.parametrize("quem", ["Rodrigo", "Bruna", "João", "Lúcia"])
def test_marca_patch_so_administrador(moto, quem):  # noqa: F811
    assert _patch(moto, {"cor": "#2F6FED"}, quem=quem).status_code == 403
    assert moto.api(quem).post(SIMULAR, {"cor": "#2F6FED"}, format="json").status_code == 403
    assert selectors.configuracao().cor_marca == ""


def test_marca_patch_sem_login_suporte_e_empresa_pausada(moto, relogio_jwt):  # noqa: F811
    assert _publico().patch(MARCA, {"cor": "#2F6FED"}, format="json").status_code == 401
    suporte = _suporte(moto, "ver_editar")
    proibido = suporte.patch(MARCA, {"cor": "#2F6FED"}, format="json")
    assert proibido.status_code == 403
    assert proibido.json()["codigo"] == "PLT-07"
    assert suporte.post(SIMULAR, {"cor": "#2F6FED"}, format="json").status_code == 403
    assert suporte.get(MARCA).status_code == 200  # a leitura continua pública

    Empresa._base_manager.filter(pk=moto.empresa.pk).update(status="pausada")
    resposta = _patch(moto, {"cor": "#2F6FED"}, formato="json")
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "empresa_sem_operacao"
    assert _eventos() == 0


def test_marca_patch_mensagens_do_contrato(moto):  # noqa: F811
    casos = [
        ({"cor": "#12345"}, {"cor": ["Use uma cor no formato #RRGGBB."]}),
        ({"nome_exibicao": "M" * 81}, {"nome_exibicao": ["Use até 80 caracteres."]}),
        ({"logo": _arquivo(b"GIF89a")}, {"logo": ["Envie o logo em SVG ou PNG."]}),
        (
            {"logo": _arquivo(SVG), "remover_logo": "true"},
            {"remover_logo": ["Envie um logo novo ou remova o atual, não os dois."]},
        ),
        (
            {"logo": _arquivo(b"<svg><script>alert(1)</script></svg>")},
            {
                "logo": [
                    "Não conseguimos ler este SVG. Exporte o logo de novo pelo seu programa "
                    "de desenho."
                ]
            },
        ),
    ]
    for dados, campos in casos:
        resposta = _patch(moto, dados)
        assert resposta.status_code == 400, dados
        assert resposta.json()["codigo"] == "validacao"
        assert resposta.json()["campos"] == campos
    url = _patch(moto, {"logo": "https://mal.example/logo.svg"}, formato="json")
    assert url.json()["campos"] == {"logo": ["Envie o logo em SVG ou PNG."]}
    assert _eventos() == 0


def test_s_12_svg_ativo_recusado_com_warning_sem_conteudo(moto, caplog):  # noqa: F811
    ativo = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" onload="segredo()">'
        b'<rect width="1" height="1"/></svg>'
    )
    with caplog.at_level(logging.WARNING, logger="apps.empresas.services"):
        resposta = _patch(moto, {"logo": _arquivo(ativo)})
    assert resposta.status_code == 400
    assert resposta.json()["campos"]["logo"] == [
        "O SVG tem conteúdo que não aceitamos, como script ou link externo. Exporte o logo "
        "de novo, só com o desenho."
    ]
    avisos = [r for r in caplog.records if r.name == "apps.empresas.services"]
    assert len(avisos) == 1
    assert f"usuario={moto.pessoas['Mariana'].pk}" in avisos[0].getMessage()
    assert "segredo" not in caplog.text
    assert selectors.configuracao().logo.name in ("", None)


def test_s_12_png_servido_com_nosniff(moto):  # noqa: F811
    resposta = _patch(moto, {"logo": _arquivo(_png(), "logo.svg")})  # a extensão não manda
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["logo"]["largura"], corpo["logo"]["altura"]) == (30, 10)
    logo = _publico().get(LOGO, {"v": corpo["versao"]})
    assert logo.status_code == 200
    assert logo["Content-Type"] == "image/png"
    assert logo["X-Content-Type-Options"] == "nosniff"
    assert logo["Content-Disposition"] == 'inline; filename="logo.png"'
    assert logo.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_marca_trocar_e_remover_logo_apaga_o_arquivo_antigo(
    moto,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        _patch(moto, {"logo": _arquivo(SVG)})
    primeiro = selectors.configuracao().logo.name
    assert arquivos.provedor().existe(primeiro)

    with django_capture_on_commit_callbacks(execute=True):
        assert _patch(moto, {"logo": _arquivo(_png())}).status_code == 200
    segundo = selectors.configuracao().logo.name
    assert segundo.endswith(".png") and segundo != primeiro
    assert not arquivos.provedor().existe(primeiro)

    with django_capture_on_commit_callbacks(execute=True):
        corpo = _patch(moto, {"remover_logo": True}, formato="json").json()
    assert corpo["logo"] is None and corpo["iniciais"] == "EA"
    assert not arquivos.provedor().existe(segundo)
    assert _eventos() == 3
    evento = EventoAuditoria.objects.filter(acao="empresa.alterar_marca").latest("id")
    assert evento.antes["logo"] == segundo and evento.depois["logo"] is None


def test_marca_transacao_que_falha_apaga_o_arquivo_novo(moto, monkeypatch):  # noqa: F811
    def falha(*_args, **_kwargs):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(services.plataforma_services, "registrar_passo_implantacao", falha)
    gravados = set(arquivos.guardados)
    with pytest.raises(RuntimeError):
        services.salvar_marca(logo=SVG)
    assert set(arquivos.guardados) == gravados


def test_marca_servico_valida_como_a_api(moto):  # noqa: F811
    with pytest.raises(ErroDeValidacao) as erro:
        services.salvar_marca(cor="123456", nome_exibicao="x" * 81)
    assert set(erro.value.campos) == {"cor", "nome_exibicao"}


def test_marca_patch_limite_de_30_por_hora(moto):  # noqa: F811
    api = moto.api()
    codigos = [api.patch(MARCA, {"cor": "#2F6FED"}, format="json").status_code for _ in range(31)]
    assert codigos[:30] == [200] * 30
    assert codigos[30] == 429
