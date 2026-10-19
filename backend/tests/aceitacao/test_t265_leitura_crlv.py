"""T-265 · Leitura do CRLV-e (VEI-08, ADR 0026, docs/qa/criterios/T-247.md, CA-247-01 a 07).

Os PDFs são fictícios, gerados em `documentos_pdf.py`. As rotas rodam na `empresa_a` com as
pessoas e a frota da Moto Rápida, com o relógio em 07 out 2026.
"""

import inspect
import io
import logging
import sys
import threading
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfReader

from apps.auditoria.models import EventoAuditoria
from apps.veiculos.models import DocumentoVeiculo, Veiculo
from comum import comprovante_leitura, cripto
from integracoes import leitura_documentos
from integracoes.leitura_documentos import crlv, trabalhador

from . import documentos_pdf as pdfs
from .frota import Frota, montar_frota
from .test_t012_filiais import MotoRapida

LEITURA = "/api/veiculos/leitura-crlv/"
FALHA = {
    "codigo": "VEI-08",
    "mensagem": "Não conseguimos ler este documento. Preencha os campos à mão.",
}
NOVE = [
    "placa",
    "chassi",
    "renavam",
    "marca",
    "modelo",
    "ano_fabricacao",
    "ano_modelo",
    "cor",
    "combustivel",
]


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


def _pdf(conteudo: bytes, nome: str = "crlv.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


def _ler(moto: MotoRapida, conteudo: bytes, nome: str = "crlv.pdf", pessoa: str = "Mariana"):
    return moto.api(pessoa).post(LEITURA, {"arquivo": _pdf(conteudo, nome)}, format="multipart")


def _texto(conteudo: bytes) -> str:
    return PdfReader(io.BytesIO(conteudo)).pages[0].extract_text(extraction_mode="layout")


# --- Parser puro ---


def test_vei_08_parser_le_os_campos_e_nao_o_proprietario() -> None:
    campos = crlv.extrair(_texto(pdfs.CRLV_TBC5H21.pdf()))
    assert campos == {
        "placa": "TBC5H21",
        "chassi": "9C2JC7510SR000123",
        "renavam": "01234567897",
        "marca_modelo": "HONDA/POP 110I ES",
        "ano_fabricacao": 2025,
        "ano_modelo": 2026,
        "cor": "vermelha",
        "combustivel": "gasolina",
        "exercicio": 2026,
    }
    assert pdfs.PROPRIETARIO not in str(campos)


def test_vei_08_parser_validadores() -> None:
    assert crlv.placa("tbc-5h21") == "TBC5H21"
    assert crlv.placa("ABC1234") == "ABC1234"
    assert crlv.placa("*******/CE") is None
    assert crlv.chassi("9C2JC7510SR000123") == "9C2JC7510SR000123"
    assert crlv.chassi("9C2JC7510SR00012") is None  # 16
    assert crlv.chassi("9C2JC7510SO000123") is None  # O não existe em chassi
    assert crlv.renavam("01234567897") == "01234567897"
    assert crlv.renavam("01234567890") is None  # dígito errado
    assert crlv.renavam("00000000000") is None
    assert crlv.ano("2026") == 2026
    assert crlv.ano("1850") is None
    assert crlv.combustivel("ALCOOL/GASOLINA") == "flex"
    assert crlv.combustivel("GÁS NATURAL") is None  # fora do enum: fica fora de `lidos`
    assert crlv.cor("VERMELHA") == "vermelha"
    assert crlv.cor("529.982.247-25") is None
    # O ano do modelo é o de fabricação ou o seguinte (VEI-01): senão, fica de fora.
    texto = _texto(pdfs.Crlv(ano_fabricacao="2020", ano_modelo="2026").pdf())
    assert "ano_modelo" not in crlv.extrair(texto)


# --- Processo filho (ADR 0026, itens 4 e 6) ---


def test_adr_0026_filho_so_com_path_e_lang_e_os_limites() -> None:
    resposta = leitura_documentos.executar("_diagnostico", b"")
    assert resposta["ok"] is True
    assert resposta["ambiente"] == ["LANG", "PATH"]  # M-01
    assert resposta["modulos"] == []  # B-01: nem django, nem comum, nem apps
    if sys.platform != "win32":  # M-02
        assert resposta["limites"] == {
            "RLIMIT_CPU": [5, 5],
            "RLIMIT_AS": [512 * 1024 * 1024] * 2,
            "RLIMIT_FSIZE": [0, 0],
            "RLIMIT_NOFILE": [16, 16],
            "RLIMIT_CORE": [0, 0],
        }


def test_adr_0026_pai_chama_isolado_sem_preexec_fn(monkeypatch) -> None:
    chamadas = []
    original = leitura_documentos.subprocess.Popen

    def espiao(*args, **kwargs):
        chamadas.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(leitura_documentos.subprocess, "Popen", espiao)
    leitura_documentos.executar("_diagnostico", b"")
    ((args, kwargs),) = chamadas
    assert args[0] == [sys.executable, "-I", trabalhador.__file__, "_diagnostico"]
    assert Path(args[0][2]).is_absolute()
    assert kwargs["env"] == {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}
    assert kwargs["start_new_session"] is True and kwargs["close_fds"] is True
    assert "preexec_fn" not in kwargs
    assert "preexec_fn" not in inspect.getsource(leitura_documentos.executar)


def test_adr_0026_filho_travado_morre_no_tempo(monkeypatch, tmp_path) -> None:
    travado = tmp_path / "travado.py"
    travado.write_text("import time\nwhile True:\n    time.sleep(1)\n", encoding="utf-8")
    monkeypatch.setattr(leitura_documentos, "TRABALHADOR", str(travado))
    monkeypatch.setattr(leitura_documentos, "TEMPO_DE_RELOGIO", 1)
    assert leitura_documentos.ler("crlv", b"%PDF-1.4") == leitura_documentos.Leitura(motivo="tempo")


def test_adr_0026_saida_grande_ou_campos_estranhos(monkeypatch, tmp_path) -> None:
    grande = tmp_path / "grande.py"
    grande.write_text("import sys\nsys.stdout.write('x' * 200000)\n", encoding="utf-8")
    monkeypatch.setattr(leitura_documentos, "TRABALHADOR", str(grande))
    assert leitura_documentos.ler("crlv", b"").motivo == "nao_reconhecido"
    # B-02/B-03: só as chaves do tipo, com o tipo e o tamanho certos.
    conferidos = leitura_documentos.conferir(
        "crlv",
        {"placa": "TBC5H21", "nome": pdfs.PROPRIETARIO, "chassi": "X" * 99, "ano_modelo": "2026"},
    )
    assert conferidos == {"placa": "TBC5H21"}


@pytest.mark.parametrize(
    ("conteudo", "motivo"),
    [
        (pdfs.com_senha(), "senha"),
        (pdfs.sem_texto(), "sem_texto"),
        (pdfs.com_paginas(4), "paginas"),
        (pdfs.nao_e_documento(), "nao_reconhecido"),
        (b"\xff\xd8\xff\xe0 foto", "nao_pdf"),
        (b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024), "grande"),
        (b"%PDF-1.4\nlixo sem estrutura", "nao_reconhecido"),
    ],
)
def test_adr_0026_filho_falha_com_o_codigo(conteudo: bytes, motivo: str) -> None:
    assert leitura_documentos.ler("crlv", conteudo) == leitura_documentos.Leitura(motivo=motivo)


def test_adr_0026_pdf_com_javascript_e_anexo_nao_executa() -> None:
    leitura = leitura_documentos.ler("crlv", pdfs.com_javascript_e_anexo())
    assert leitura.campos.get("placa") == "TBC5H21"  # só o texto é lido
    assert "conteudo escondido" not in str(leitura.campos)


def test_adr_0026_vaga_ocupada() -> None:
    with (
        leitura_documentos.vaga(),
        leitura_documentos.vaga(),
        pytest.raises(leitura_documentos.LeituraOcupada),
        leitura_documentos.vaga(),
    ):
        pass
    with leitura_documentos.vaga():  # liberou
        pass


# --- Rotas (CA-247-01 a 07) ---


def test_vei_08_le_os_9_campos(moto, frota, caplog) -> None:
    """CA-247-01 e CA-247-02."""
    antes = Veiculo.objects.count()
    with caplog.at_level(logging.DEBUG):
        resposta = _ler(moto, pdfs.CRLV_TBC5H21.pdf(), nome="crlv-antonio-ficticio.pdf")
    assert resposta.status_code == 200, resposta.json()
    assert resposta["Cache-Control"] == "no-store"
    corpo = resposta.json()
    assert corpo["campos"] == {
        "placa": "TBC5H21",
        "chassi": "9C2JC7510SR000123",
        "renavam": "01234567897",
        "marca": "Honda",
        "modelo": "Pop 110i ES",
        "ano_fabricacao": 2025,
        "ano_modelo": 2026,
        "cor": "vermelha",
        "combustivel": "gasolina",
    }
    assert corpo["lidos"] == NOVE and corpo["quantidade"] == 9
    assert corpo["rotulo"] == "CRLV-e lido · 9 campos preenchidos"
    assert corpo["exercicio"] == 2026
    assert corpo["dicas"] == {"marca_modelo": None}
    assert corpo["documento"] == "crlv" and corpo["leitura"]
    assert Veiculo.objects.count() == antes  # nada gravado
    # CA-247-02: nem na resposta nem no log; nem placa, nem o nome do arquivo.
    registros = "\n".join(r.getMessage() for r in caplog.records)
    for segredo in (pdfs.PROPRIETARIO, pdfs.CPF_PROPRIETARIO, "52998224725", "antonio"):
        assert segredo.lower() not in resposta.content.decode().lower()
        assert segredo.lower() not in registros.lower()
    assert "TBC5H21" not in registros and "9C2JC7510SR000123" not in registros
    assert "tipo=crlv resultado=lido motivo=- campos=9" in registros


def test_vei_08_salva_com_o_documento(moto, frota) -> None:
    """CA-247-03: a cor corrigida vale, e o evento diz o que veio do documento."""
    conteudo = pdfs.CRLV_TBC5H21.pdf()
    lido = _ler(moto, conteudo).json()
    urbana = frota.categorias["Urbana 110–125"]
    antes = Veiculo.objects.count()
    corpo = {
        **{k: v for k, v in lido["campos"].items() if v is not None},
        "cor": "preta",
        "km_atual": 0,
        "categoria_id": urbana.pk,
        "filial_id": frota.centro.pk,
        "crlv_arquivo": _pdf(conteudo, "crlv-antonio-ficticio.pdf"),
        "crlv_validade": "2027-10-31",
        "crlv_exercicio": lido["exercicio"],
        "leitura": lido["leitura"],
    }
    resposta = moto.api().post("/api/veiculos/", corpo, format="multipart")
    assert resposta.status_code == 201, resposta.json()
    assert resposta.json()["cor"] == "preta" and resposta.json()["combustivel"] == "gasolina"
    assert Veiculo.objects.count() == antes + 1
    veiculo = Veiculo.objects.get(placa="TBC5H21")
    documento = DocumentoVeiculo.objects.get(veiculo=veiculo, tipo="crlv", ativo=True)
    assert documento.exercicio == 2026
    assert str(documento.validade) == "2027-10-31"
    assert documento.arquivo_nome == "CRLV-e.pdf"  # o nome enviado não fica
    assert documento.arquivo.name.endswith(".pdf")
    evento = EventoAuditoria.objects.get(acao="veiculo.cadastrar", objeto_id=veiculo.pk)
    assert evento.depois["preenchido_pelo_documento"] == {
        "tipo": "crlv",
        "campos": NOVE,
        "corrigidos": ["cor"],
    }


def test_vei_08_comprovante_de_outra_pessoa_ou_de_outro_arquivo(moto, frota) -> None:
    conteudo = pdfs.CRLV_TBC5H21.pdf()
    do_rodrigo = _ler(moto, conteudo, pessoa="Rodrigo").json()["leitura"]
    outro = pdfs.Crlv(cor="AZUL").pdf()
    da_mariana = _ler(moto, conteudo).json()["leitura"]

    def salvar(placa: str, chassi: str, arquivo: bytes, leitura: str) -> int:
        corpo = {
            "placa": placa,
            "chassi": chassi,
            "marca": "Honda",
            "modelo": "Pop 110i ES",
            "ano_fabricacao": 2025,
            "ano_modelo": 2026,
            "cor": "vermelha",
            "categoria_id": frota.categorias["Urbana 110–125"].pk,
            "filial_id": frota.centro.pk,
            "crlv_arquivo": _pdf(arquivo),
            "crlv_validade": "2027-10-31",
            "leitura": leitura,
        }
        resposta = moto.api().post("/api/veiculos/", corpo, format="multipart")
        assert resposta.status_code == 201, resposta.json()
        return resposta.json()["id"]

    for veiculo_id in (
        salvar("TBC5H21", "9C2JC7510SR000123", conteudo, do_rodrigo),  # outra pessoa
        salvar("TBC5H22", "9C2JC7510SR000124", outro, da_mariana),  # outro arquivo
        salvar("TBC5H23", "9C2JC7510SR000125", conteudo, da_mariana + "x"),  # adulterado
    ):
        evento = EventoAuditoria.objects.get(acao="veiculo.cadastrar", objeto_id=veiculo_id)
        assert "preenchido_pelo_documento" not in evento.depois
        assert DocumentoVeiculo.objects.filter(veiculo_id=veiculo_id, tipo="crlv").exists()


def test_adr_0026_resumo_difere_do_hash_de_busca(moto) -> None:
    """B-04: o resumo de um CPF não é o `CampoHashBusca` do mesmo CPF, e depende do arquivo."""
    cpf = "52998224725"
    um = comprovante_leitura.resumo(comprovante_leitura.sha256(b"a"), "cpf", cpf)
    outro = comprovante_leitura.resumo(comprovante_leitura.sha256(b"b"), "cpf", cpf)
    assert um != outro
    assert um != cripto.hash_busca(cpf)


def test_vei_08_validacoes_de_sempre(moto, frota) -> None:
    """CA-247-04: o QXA-4B21 lido; salvar recebe o 409 VEI-01 e nada é criado."""
    conteudo = pdfs.CRLV_QXA4B21.pdf()
    lido = _ler(moto, conteudo, pessoa="Rodrigo").json()
    assert lido["campos"]["placa"] == "QXA4B21"
    assert lido["campos"]["chassi"] == "9C2KC2210PR004401"
    assert lido["campos"]["combustivel"] == "flex"
    antes = (Veiculo.objects.count(), DocumentoVeiculo.objects.count())
    corpo = {
        **{k: v for k, v in lido["campos"].items() if v is not None},
        "categoria_id": frota.categorias["Urbana 110–125"].pk,
        "filial_id": frota.centro.pk,
        "crlv_arquivo": _pdf(conteudo),
        "crlv_validade": "2027-10-31",
        "leitura": lido["leitura"],
    }
    resposta = moto.api("Rodrigo").post("/api/veiculos/", corpo, format="multipart")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "VEI-01"
    assert (Veiculo.objects.count(), DocumentoVeiculo.objects.count()) == antes


def test_vei_08_salvar_sem_validade_ou_com_arquivo_que_nao_e_pdf(moto, frota) -> None:
    base = {
        "placa": "TBC5H21",
        "chassi": "9C2JC7510SR000123",
        "marca": "Honda",
        "modelo": "Pop 110i ES",
        "ano_fabricacao": 2025,
        "ano_modelo": 2026,
        "cor": "vermelha",
        "categoria_id": frota.categorias["Urbana 110–125"].pk,
        "filial_id": frota.centro.pk,
    }
    sem_validade = {**base, "crlv_arquivo": _pdf(pdfs.CRLV_TBC5H21.pdf())}
    resposta = moto.api().post("/api/veiculos/", sem_validade, format="multipart")
    assert resposta.status_code == 400
    assert resposta.json()["campos"]["crlv_validade"] == ["Informe a validade do CRLV."]
    foto = {**base, "crlv_arquivo": _pdf(b"\xff\xd8\xff\xe0 foto"), "crlv_validade": "2027-10-31"}
    resposta = moto.api().post("/api/veiculos/", foto, format="multipart")
    assert resposta.status_code == 400
    assert "crlv_arquivo" in resposta.json()["campos"]
    assert not Veiculo.objects.filter(placa="TBC5H21").exists()


def test_vei_08_modelo_fora_da_lista(moto) -> None:
    """CA-247-05."""
    corpo = _ler(moto, pdfs.CRLV_FORA_DA_LISTA.pdf()).json()
    assert corpo["campos"]["marca"] is None and corpo["campos"]["modelo"] is None
    assert corpo["quantidade"] == 7
    assert corpo["rotulo"] == "CRLV-e lido · 7 campos preenchidos"
    assert corpo["dicas"] == {"marca_modelo": "SUZUKI/YES 125"}


def test_vei_08_um_campo_no_singular() -> None:
    from apps.veiculos.leitura import rotulo

    assert rotulo(1) == "CRLV-e lido · 1 campo preenchido"


def test_vei_08_nao_da_para_ler(moto) -> None:
    """CA-247-06: a mesma 422 para toda falha; a foto recebe 400."""
    grande = b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024)
    for conteudo, nome in (
        (pdfs.nao_e_documento(), "nao-e-documento.pdf"),
        (pdfs.com_senha(), "crlv-senha.pdf"),
        (grande, "crlv.pdf"),
        (b"\xff\xd8\xff\xe0 foto", "crlv.pdf"),  # a extensão diz PDF, o conteúdo não
    ):
        resposta = _ler(moto, conteudo, nome)
        assert resposta.status_code == 422, nome
        assert {k: resposta.json()[k] for k in FALHA} == FALHA
    foto = _ler(moto, b"\xff\xd8\xff\xe0 foto", "foto-crlv.jpg")
    assert foto.status_code == 400
    assert foto.json()["campos"]["arquivo"] == ["Envie o PDF do CRLV-e."]
    sem_arquivo = moto.api().post(LEITURA, {}, format="multipart")
    assert sem_arquivo.status_code == 400


def test_vei_08_quem_pode(moto) -> None:
    """CA-247-07."""
    for pessoa in ("Bruna", "João", "Lúcia"):
        resposta = _ler(moto, pdfs.CRLV_TBC5H21.pdf(), pessoa=pessoa)
        assert resposta.status_code == 403, pessoa
    assert _ler(moto, pdfs.CRLV_TBC5H21.pdf(), pessoa="Rodrigo").status_code == 200


def test_vei_08_leitura_ocupada(moto, monkeypatch) -> None:
    monkeypatch.setattr(leitura_documentos, "_vagas", threading.BoundedSemaphore(1))
    with leitura_documentos.vaga():
        resposta = _ler(moto, pdfs.CRLV_TBC5H21.pdf())
    assert resposta.status_code == 503
    assert resposta.json()["codigo"] == "leitura_ocupada"
    assert resposta["Retry-After"]


def test_vei_08_limite_por_usuario_conta_as_recusas(moto) -> None:
    for _ in range(30):
        assert _ler(moto, b"foto", "foto.jpg").status_code == 400
    resposta = _ler(moto, pdfs.CRLV_TBC5H21.pdf())
    assert resposta.status_code == 429
    assert resposta.json()["codigo"] == "muitas_requisicoes"
    assert _ler(moto, pdfs.CRLV_TBC5H21.pdf(), pessoa="Rodrigo").status_code == 200
