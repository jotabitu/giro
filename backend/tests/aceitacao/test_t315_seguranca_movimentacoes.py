"""T-315 · Revisão de segurança das Movimentações (T-288 parte 1).

Relatório: docs/seguranca/2026-10-16-t315-movimentacoes.md. Moto Rápida em 07 out 2026, com o
cenário da T-288.
"""

import io
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django_tenants.utils import schema_context
from PIL import Image

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.financeiro.models import Despesa
from apps.movimentacoes.models import FotoChegadaMovimentacao, LocalApoio, Movimentacao
from apps.plataforma.models import Empresa
from apps.plataforma.services import abrir_acesso_suporte

from .conftest import cliente as cliente_http
from .test_t012_filiais import HOST
from .test_t015_locacoes import Cenario
from .test_t288_movimentacoes import (
    LISTA,
    _baixar,
    _corpo,
    _criada,
    _foto,
    _lavagem,
    _post,
)
from .test_t288_movimentacoes import cenario as cenario

POSICOES = ("frente", "traseira", "lado_esquerdo", "lado_direito")


def _suporte(cenario: Cenario, permissao: str) -> Any:
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
        permissao=permissao,
    )
    connection.set_tenant(cenario.moto.empresa)
    return cliente_http(HOST, str(token))


def _foto_com_gps() -> SimpleUploadedFile:
    imagem = Image.new("RGB", (8, 8), "blue")
    exif = Image.Exif()
    exif[0x010F] = "Fabricante do Celular"  # Make
    exif[0x8825] = {2: (3.0, 43.0, 0.0), 1: "S"}  # GPSInfo
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", exif=exif)
    return SimpleUploadedFile("casa-do-joao.jpg", saida.getvalue(), content_type="image/jpeg")


def _com_vistoria(cenario: Cenario) -> dict[str, Any]:
    return _criada(cenario, vistoria_rapida=True)


def _concluida_com_fotos(cenario: Cenario) -> dict[str, Any]:
    mov = _com_vistoria(cenario)
    for posicao in POSICOES:
        foto = _post(
            cenario,
            "João",
            f"{mov['id']}/chegada/fotos/",
            {"posicao": posicao, "arquivo": _foto()},
            format="multipart",
        )
        assert foto.status_code == 201, foto.json()
    chegou = _post(cenario, "João", f"{mov['id']}/chegada/", {"km": 3146, "combustivel": "cheio"})
    assert chegou.status_code == 200, chegou.json()
    return dict(chegou.json())


# --- Suporte (PLT-07, ADR 0013 item 2, AUD-05) ---


def test_plt_07_suporte_so_ver_le_quadro_e_lista_sem_url(cenario, relogio_jwt):
    mov = _concluida_com_fotos(cenario)
    api = _suporte(cenario, "ver")
    centro = cenario.frota.centro.pk
    rotas = ("", "quadro/", "locais/", f"pessoas/?filial={centro}", f"{mov['id']}/recebedores/")
    for rota in rotas:
        resposta = api.get(f"{LISTA}{rota}")
        assert resposta.status_code == 200, (rota, resposta.json())
        texto = resposta.content.decode()
        assert "assinatura=" not in texto and "fotos_chegada" not in texto, rota


def test_plt_07_suporte_so_ver_nao_le_o_detalhe(cenario, relogio_jwt):
    mov = _concluida_com_fotos(cenario)
    api = _suporte(cenario, "ver")
    detalhe = api.get(f"{LISTA}{mov['id']}/")
    assert detalhe.status_code == 403 and detalhe.json()["codigo"] == "PLT-07"
    foto = api.post(
        f"{LISTA}{mov['id']}/chegada/fotos/",
        {"posicao": "frente", "arquivo": _foto()},
        format="multipart",
    )
    assert foto.status_code == 403 and foto.json()["codigo"] == "PLT-07"


def test_plt_07_suporte_ver_e_editar_so_le_as_movimentacoes(cenario, relogio_jwt):
    """CA-246-24 (T-319, opção A): mesmo em "ver e editar", toda escrita dá 403 PLT-07, sem 500;
    o detalhe segue legível."""
    mov = _com_vistoria(cenario)
    local = LocalApoio.objects.create(nome="Lava Rápido Aldeota", tipo="lava_jato")
    api = _suporte(cenario, "ver_editar")
    assert api.get(f"{LISTA}{mov['id']}/").status_code == 200
    parada = f"{mov['id']}/paradas/1/"
    escritas: tuple[tuple[str, str, Any, str], ...] = (
        ("post", "", _corpo(cenario, placa="PMZ3E17"), "json"),
        ("patch", f"{mov['id']}/", {"agendada_para": "2026-10-10T11:00:00Z"}, "json"),
        ("post", f"{mov['id']}/iniciar/", {}, "json"),
        ("post", f"{mov['id']}/cancelar/", {"motivo": "Teste"}, "json"),
        ("post", f"{parada}chegada/", {}, "json"),
        ("post", f"{parada}saida/", {"valor_pago_centavos": 0}, "multipart"),
        ("post", f"{mov['id']}/chegada/fotos/", {"posicao": "frente", "arquivo": _foto()},
         "multipart"),
        ("post", f"{mov['id']}/chegada/", {"km": 3146, "combustivel": "cheio"}, "json"),
        ("post", "locais/", {"nome": "Oficina do Zé", "tipo": "oficina"}, "json"),
        ("post", f"locais/{local.pk}/inativar/", {}, "json"),
        ("post", f"locais/{local.pk}/reativar/", {}, "json"),
    )  # fmt: skip
    for metodo, rota, corpo, formato in escritas:
        resposta = getattr(api, metodo)(f"{LISTA}{rota}", corpo, format=formato)
        assert resposta.status_code == 403, (rota, resposta.status_code)
        assert resposta.json()["codigo"] == "PLT-07", rota
    assert Movimentacao.objects.count() == 1
    assert not FotoChegadaMovimentacao.objects.exists()


# --- Fotos da vistoria rápida (AUD-05) ---


def test_aud_05_foto_da_chegada_sem_metadados_e_com_nome_aleatorio(cenario):
    mov = _com_vistoria(cenario)
    resposta = _post(
        cenario,
        "João",
        f"{mov['id']}/chegada/fotos/",
        {"posicao": "frente", "arquivo": _foto_com_gps()},
        format="multipart",
    )
    assert resposta.status_code == 201, resposta.json()
    assert "url_expira_em" in resposta.json()
    foto = FotoChegadaMovimentacao.objects.get()
    assert "casa-do-joao" not in foto.arquivo.name
    assert foto.arquivo.name.startswith(f"{connection.schema_name}/")
    with foto.arquivo.open("rb") as arquivo, Image.open(arquivo) as lida:
        assert not dict(lida.getexif())


def test_aud_05_foto_da_chegada_recusa_o_que_nao_e_imagem(cenario):
    mov = _com_vistoria(cenario)
    falsa = SimpleUploadedFile("foto.jpg", b"<?php system($_GET['c']); ?>", "image/jpeg")
    resposta = _post(
        cenario,
        "João",
        f"{mov['id']}/chegada/fotos/",
        {"posicao": "frente", "arquivo": falsa},
        format="multipart",
    )
    assert resposta.status_code == 400, resposta.json()
    assert not FotoChegadaMovimentacao.objects.exists()


def test_mov_02_so_quem_registra_a_chegada_envia_foto(cenario):
    mov = _com_vistoria(cenario)
    for quem in ("Lúcia", "Bruna"):
        resposta = _post(
            cenario,
            quem,
            f"{mov['id']}/chegada/fotos/",
            {"posicao": "frente", "arquivo": _foto()},
            format="multipart",
        )
        assert resposta.status_code == 403, (quem, resposta.status_code)
    assert not FotoChegadaMovimentacao.objects.exists()


def test_aud_01_foto_da_chegada_trocada_fica_na_auditoria(cenario):
    """B-01: cada envio gera `movimentacao.foto_chegada`, e a troca diz que substituiu."""
    mov = _com_vistoria(cenario)
    for _ in range(2):
        resposta = _post(
            cenario,
            "João",
            f"{mov['id']}/chegada/fotos/",
            {"posicao": "frente", "arquivo": _foto()},
            format="multipart",
        )
        assert resposta.status_code == 201
    eventos = EventoAuditoria.objects.filter(
        acao="movimentacao.foto_chegada", objeto_id=mov["id"]
    ).order_by("id")
    foto = FotoChegadaMovimentacao.objects.get()
    assert [e.depois for e in eventos] == [
        {"posicao": "frente", "foto_id": foto.pk, "substituiu": False},
        {"posicao": "frente", "foto_id": foto.pk, "substituiu": True},
    ]
    assert all(e.regra == "MOV-05" and e.objeto_codigo == mov["codigo"] for e in eventos)
    assert all(e.ator_id == cenario.pessoas["João"].pk for e in eventos)


def test_mov_02_quem_nao_registra_a_chegada_recebe_403_antes_de_ler_o_arquivo(cenario):
    """B-02: o arquivo inválido do financeiro dá 403, não 400: a permissão vem antes da leitura."""
    mov = _com_vistoria(cenario)
    falsa = SimpleUploadedFile("foto.jpg", b"nao e imagem", "image/jpeg")
    resposta = _post(
        cenario,
        "Lúcia",
        f"{mov['id']}/chegada/fotos/",
        {"posicao": "frente", "arquivo": falsa},
        format="multipart",
    )
    assert resposta.status_code == 403, resposta.json()


def test_aud_05_fin_06_nota_da_parada_sem_metadados(cenario):
    """B-03: a nota fotografada perde o EXIF e o GPS, como as fotos; vale para toda nota."""
    mov = _criada(cenario, paradas=_lavagem(cenario))
    parada = mov["paradas"][0]["id"]
    chegou = _post(cenario, "João", f"{mov['id']}/paradas/{parada}/chegada/")
    assert chegou.status_code == 200, chegou.json()
    saiu = _post(
        cenario,
        "João",
        f"{mov['id']}/paradas/{parada}/saida/",
        {"valor_pago_centavos": 3500, "nota": _foto_com_gps()},
        format="multipart",
    )
    assert saiu.status_code == 200, saiu.json()
    despesa = Despesa.objects.get()
    assert "casa-do-joao" not in despesa.nota.name
    with despesa.nota.open("rb") as arquivo, Image.open(arquivo) as lida:
        assert not dict(lida.getexif())


# --- Quem leva e quem recebe (MOV-02, MOV-06, T-300) ---


def test_mov_02_pessoas_e_recebedores_sem_contato(cenario):
    mov = _criada(cenario)
    centro = cenario.frota.centro.pk
    campos = {"id", "nome", "perfil", "perfil_rotulo", "eu"}
    pessoas = cenario.moto.api("Rodrigo").get(f"{LISTA}pessoas/", {"filial": centro}).json()
    recebem = cenario.moto.api("João").get(f"{LISTA}{mov['id']}/recebedores/").json()
    for lista in (pessoas, recebem):
        assert lista["resultados"]
        for pessoa in lista["resultados"]:
            assert set(pessoa) == campos
    # Quem não leva nem gere não lê quem recebe.
    assert cenario.moto.api("Bruna").get(f"{LISTA}{mov['id']}/recebedores/").status_code == 403
    assert cenario.moto.api("Lúcia").get(f"{LISTA}pessoas/", {"filial": centro}).status_code == 403


# --- Baixa que cancela (MOV-03, T-311) ---


def test_mov_03_baixa_cancela_com_o_ator_da_baixa(cenario):
    mov = _criada(cenario)
    assert (
        cenario.moto.api("João")
        .post(f"/api/veiculos/{cenario.sak.pk}/baixar/", {"motivo": "roubo"}, format="json")
        .status_code
        == 403
    )
    assert Movimentacao.objects.get(pk=mov["id"]).status == "em_transito"
    assert _baixar(cenario).status_code == 200
    evento = EventoAuditoria.objects.get(objeto_id=mov["id"], acao="movimentacao.cancelar")
    assert evento.ator_id == cenario.pessoas["Mariana"].pk
    assert evento.regra == "MOV-03"
