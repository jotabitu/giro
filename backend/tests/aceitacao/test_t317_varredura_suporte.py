"""T-317 · Varredura do suporte nas rotas de escrita (PLT-07, sugestão da segurança na T-315).

Com o token de suporte em "ver e editar", cada rota de escrita da empresa responde 2xx, 4xx ou
403 `PLT-07`, nunca 500. O 500 aparecia quando a view gravava `request.user` (o `AtorSuporte`)
num campo que exige `contas.Usuario` (`lancada_por`, `aberto_por`, `fechado_por`, `feito_por`).

O teste percorre as rotas do `config.urls` (as rotas novas entram sozinhas). Cada rota vai com o
corpo vazio e, onde o corpo vazio pararia na validação antes da gravação, com um corpo válido
(`CORPOS`), para o erro aparecer. Rota que ainda dá 500 fica em `QUEBRADAS` com `xfail` estrito:
quando o backend corrige, o teste passa a falhar até a rota sair da lista.
"""

import io
import re
from datetime import date
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import URLPattern, URLResolver, get_resolver
from django_tenants.utils import schema_context
from PIL import Image
from rest_framework.test import APIClient

from apps.clientes.models import Cliente
from apps.contas.models import Usuario
from apps.financeiro import services as financeiro
from apps.financeiro.models import Reembolso
from apps.plataforma.models import Empresa
from apps.plataforma.services import abrir_acesso_suporte

from .conftest import cliente as cliente_http
from .test_t012_filiais import HOST
from .test_t288_movimentacoes import Cenario
from .test_t288_movimentacoes import cenario as cenario

ESCRITA = ("post", "put", "patch", "delete")
PUBLICAS = ("auth/", "api/auth/", "api/ambiente/", "api/schema/", "api/docs/", "api/arquivos-dev/")


def _rotas() -> list[tuple[str, str]]:
    """(método, caminho com `{pk}`) de cada rota de escrita das views da empresa."""
    achadas: list[tuple[str, str]] = []

    def andar(padroes: Any, prefixo: str) -> None:
        for padrao in padroes:
            texto = prefixo + str(padrao.pattern)
            if isinstance(padrao, URLResolver):
                andar(padrao.url_patterns, texto)
            elif isinstance(padrao, URLPattern):
                visao = getattr(padrao.callback, "cls", None)
                if visao is None:
                    continue
                caminho = "/" + re.sub(r"<(?:\w+:)?vigente_desde>", "2026-10-07", texto)
                caminho = re.sub(r"<(?:\w+:)?\w+>", "1", caminho)
                for metodo in ESCRITA:
                    if hasattr(visao, metodo):
                        achadas.append((metodo, caminho))

    andar(get_resolver("config.urls").url_patterns, "")
    return sorted(set(achadas))


def _foto() -> SimpleUploadedFile:
    saida = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(saida, format="JPEG")
    return SimpleUploadedFile("nota.jpg", saida.getvalue(), content_type="image/jpeg")


# Corpos válidos (formato, corpo): a rota só grava depois de passar pela validação.
CORPOS: dict[tuple[str, str], Any] = {
    ("post", "/api/financeiro/caixas/"): ("json", lambda: {"troco_centavos": 20000}),
    ("post", "/api/financeiro/caixas/1/sangria/"): (
        "json",
        lambda: {"valor_centavos": 1000, "descricao": "Sangria"},
    ),
    ("post", "/api/financeiro/caixas/1/fechar/"): (
        "json",
        lambda: {"contado_centavos": 0, "motivo_diferenca": "Teste"},
    ),
    ("post", "/api/financeiro/despesas/"): (
        "multipart",
        lambda: {
            "descricao": "Óleo 1 litro",
            "valor_centavos": 2500,
            "data": "2026-10-07",
            "vencimento": "2026-10-07",
            "categoria": "manutencao",
            "nota": _foto(),
        },
    ),
    ("post", "/api/financeiro/reembolsos/1/feito/"): ("multipart", lambda: {}),
    ("post", "/api/financeiro/despesas/1/pagar/"): (
        "multipart",
        lambda: {"forma": "pix", "pago_em": "2026-10-07T13:00:00Z"},
    ),
}

# Rotas que ainda dão 500 com o suporte em "ver e editar": cada uma vira tarefa de backend.
# A T-324 (opção A do dono) fechou as quatro do financeiro com 403 PLT-07.
QUEBRADAS: dict[tuple[str, str], str] = {}


def _suporte(cenario: Cenario) -> APIClient:
    with schema_context("public"):
        diego = Usuario.objects.filter(email="diego@girolocadoras.com.br").first()
        if diego is None:
            diego = Usuario.objects.create_user(
                "diego@girolocadoras.com.br",
                "senha-forte-123",
                nome="Diego Santos",
                funcao_plataforma="suporte",
            )
    _, token = abrir_acesso_suporte(
        Empresa.objects.get(pk=cenario.moto.empresa.pk),
        diego,
        motivo="Chamado #1042",
        duracao_minutos=30,
        permissao="ver_editar",
    )
    connection.set_tenant(cenario.moto.empresa)
    api = cliente_http(HOST, str(token))
    api.raise_request_exception = False
    api.credentials(
        HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_FILIAL=str(cenario.frota.centro.pk)
    )
    return api


def _com_estado_real(cenario: Cenario, caminho: str) -> str:
    """Troca o `1` do caixa, da despesa e do reembolso pelos de verdade, para a rota passar da
    busca e chegar na gravação (o 404 do `1` inexistente esconderia o 500)."""
    mariana = cenario.pessoas["Mariana"]
    centro = cenario.frota.centro
    if "/caixas/1/" in caminho:
        caixa = financeiro.abrir_caixa(centro, mariana, 20000)
        caminho = caminho.replace("/caixas/1/", f"/caixas/{caixa.pk}/")
    if "/despesas/1/" in caminho:
        despesa = financeiro.lancar_despesa(
            filial=centro,
            usuario=mariana,
            descricao="Óleo 1 litro",
            valor_centavos=2500,
            data=date(2026, 10, 7),
            vencimento=date(2026, 10, 7),
            categoria="manutencao",
        )
        caminho = caminho.replace("/despesas/1/", f"/despesas/{despesa.pk}/")
    if "/reembolsos/1/" in caminho:
        cliente = Cliente.objects.first() or cenario.cliente("Lucas")
        reembolso = Reembolso.objects.create(
            filial=centro,
            cliente=cliente,
            valor_centavos=5000,
            forma="pix",
            origem_tipo="locacao",
            origem_id=1,
            origem_codigo="LOC-2836",
        )
        caminho = caminho.replace("/reembolsos/1/", f"/reembolsos/{reembolso.pk}/")
    return caminho


def _casos() -> list[Any]:
    casos = []
    for chave in _rotas():
        marcas = []
        if chave in QUEBRADAS:
            marcas.append(pytest.mark.xfail(strict=True, reason=QUEBRADAS[chave]))
        casos.append(pytest.param(*chave, id=f"{chave[0]} {chave[1]}", marks=marcas))
    return casos


@pytest.mark.parametrize(("metodo", "caminho"), _casos())
def test_plt_07_suporte_ver_e_editar_nunca_derruba_a_rota(
    cenario,
    relogio_jwt,
    metodo,
    caminho,
):
    if caminho.startswith(PUBLICAS):
        pytest.skip("rota pública ou de autenticação: o suporte nem chega (PLT-07)")
    api = _suporte(cenario)
    formato, corpo = CORPOS.get((metodo, caminho), ("json", lambda: {}))
    caminho = _com_estado_real(cenario, caminho)
    resposta = getattr(api, metodo)(caminho, corpo(), format=formato)
    assert resposta.status_code < 500, (metodo, caminho, resposta.status_code)


# T-324, opção A do dono: no financeiro, o suporte só lê caixa, despesa e reembolso.
SO_LEITURA_NO_FINANCEIRO = [
    ("post", "/api/financeiro/caixas/"),
    ("post", "/api/financeiro/caixas/1/fechar/"),
    ("post", "/api/financeiro/despesas/"),
    ("post", "/api/financeiro/reembolsos/1/feito/"),
]


@pytest.mark.parametrize(("metodo", "caminho"), SO_LEITURA_NO_FINANCEIRO)
def test_plt_07_fin_05_fin_07_suporte_nao_escreve_no_financeiro(
    cenario,
    relogio_jwt,
    metodo,
    caminho,
):
    """403 PLT-07 antes de ler o arquivo e de validar: com um arquivo que não é imagem e campos
    inválidos, a resposta é a mesma."""
    api = _suporte(cenario)
    caminho = _com_estado_real(cenario, caminho)
    corpo = {
        "troco_centavos": "x",
        "nota": SimpleUploadedFile("nota.png", b"nao e imagem", content_type="image/png"),
    }
    resposta = getattr(api, metodo)(caminho, corpo, format="multipart")
    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "PLT-07")
