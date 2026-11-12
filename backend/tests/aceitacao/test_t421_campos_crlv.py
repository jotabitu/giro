"""T-421 · Campos do CRLV-e no cadastro e na ficha do veículo (VEI-09, VEI-08, VEI-01).

Critérios em docs/qa/criterios/T-421.md (CA-421-01 a 14); contrato em docs/api/veiculos.md,
"Dados do documento, rastreador e anotações" e "POST /api/veiculos/{id}/leitura-crlv/". Os PDFs
são fictícios, no leiaute simples e no do Detran (`documentos_pdf`), com os valores da lista dos
critérios; os CRLV-e reais da T-406 não entram no repositório.
"""

import io
from dataclasses import replace
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from pypdf import PdfReader

from apps.auditoria.models import EventoAuditoria
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import Empresa
from apps.veiculos.models import DocumentoVeiculo, Veiculo
from integracoes import leitura_documentos
from integracoes.leitura_documentos import crlv

from . import documentos_pdf as pdfs
from .frota import Frota, montar_frota
from .test_t012_filiais import MotoRapida

LEITURA = "/api/veiculos/leitura-crlv/"
VEICULOS = "/api/veiculos/"
DOCUMENTO_DO_QXA = {
    "potencia_cv": 15,
    "cilindrada_cc": 162,
    "especie": "passageiro",
    "tipo": "Motocicleta",
    "carroceria": None,
    "lotacao": 2,
    "peso_bruto_kg": 290,
    "numero_motor": "KC22E1P004401",
    "observacoes": "ALIENACAO FIDUCIARIA",
}
RASTREADOR_DO_QXA = {"numero": "356938035643809", "empresa": "Rastreia Fácil"}
ANOTACAO_DO_QXA = "Risco no tanque, lado esquerdo"
DOCUMENTO_VAZIO = dict.fromkeys(DOCUMENTO_DO_QXA)
SEM_MOTOR = ("Bruna", "João", "Lúcia")  # vendedor, vistoriador e financeiro


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


def _pdf(conteudo: bytes) -> SimpleUploadedFile:
    return SimpleUploadedFile("crlv.pdf", conteudo, content_type="application/pdf")


def _ler(moto: MotoRapida, documento: pdfs.Crlv, pessoa: str = "Mariana", rota: str = LEITURA):
    return moto.api(pessoa).post(rota, {"arquivo": _pdf(documento.pdf())}, format="multipart")


def _da_leitura(campos: dict[str, Any]) -> dict[str, Any]:
    return {
        chave.removeprefix("documento."): valor
        for chave, valor in campos.items()
        if chave.startswith("documento.")
    }


def _novo(frota: Frota, **extras: Any) -> dict[str, Any]:
    """Só os obrigatórios da VEI-01 (CA-421-06)."""
    return {
        "placa": "TBC5H21",
        "chassi": "9C2JC7510SR000123",
        "marca": "Honda",
        "modelo": "Pop 110i ES",
        "ano_fabricacao": 2025,
        "ano_modelo": 2026,
        "cor": "vermelha",
        "km_atual": 0,
        "categoria_id": frota.categorias["Urbana 110–125"].pk,
        "filial_id": frota.centro.pk,
        **extras,
    }


def _ficha(moto: MotoRapida, veiculo: Veiculo, pessoa: str = "Rodrigo") -> dict[str, Any]:
    resposta = moto.api(pessoa).get(f"{VEICULOS}{veiculo.pk}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _texto(documento: pdfs.Crlv) -> str:
    return PdfReader(io.BytesIO(documento.pdf())).pages[0].extract_text(extraction_mode="layout")


# --- Parser (VEI-08, "Do texto do CRLV-e ao campo") ---


def _lido(resultado: dict[str, Any] | None) -> dict[str, Any]:
    assert resultado is not None
    return resultado


def test_vei_09_parser_converte_o_texto_do_documento() -> None:
    assert crlv.potencia_cilindrada("15CV/0162") == {"potencia_cv": 15, "cilindrada_cc": 162}
    assert crlv.potencia_cilindrada("0CV/0109") == {"potencia_cv": None, "cilindrada_cc": 109}
    assert crlv.potencia_cilindrada("80CV/0000") == {"potencia_cv": 80, "cilindrada_cc": None}
    # fora da faixa
    assert _lido(crlv.potencia_cilindrada("1500CV/0162"))["potencia_cv"] is None
    assert crlv.potencia_cilindrada("PARTICULAR") is None
    assert crlv.especie_tipo("PASSAGEIRO MOTOCICLETA") == {
        "especie": "passageiro",
        "tipo": "Motocicleta",
    }
    assert _lido(crlv.especie_tipo("PASSAGEIRO AUTOMOVEL"))["tipo"] == "Automóvel"
    assert _lido(crlv.especie_tipo("PASSAGEIRO MICRO-ONIBUS"))["tipo"] == "Micro-ônibus"
    assert crlv.especie_tipo("CARGA CAMINHONETE") == {"especie": "carga", "tipo": "Caminhonete"}
    assert _lido(crlv.especie_tipo("MISTO UTILITARIO"))["tipo"] == "Utilitário"
    assert _lido(crlv.especie_tipo("COMPETICAO MOTOCICLETA"))["especie"] == "competicao"
    tipo = _lido(crlv.especie_tipo("PASSAGEIRO TRICICLO ELETRICO"))["tipo"]
    assert tipo == "Triciclo eletrico"
    assert crlv.especie_tipo("PARTICULAR MOTOCICLETA") is None  # espécie fora do CTB
    assert crlv.carroceria("NÃO APLICAVEL") == crlv.VAZIO
    assert crlv.carroceria("NAO APLICAVEL") == crlv.VAZIO
    assert crlv.carroceria("*****") == crlv.VAZIO
    assert crlv.carroceria("ABERTA") == "ABERTA"
    assert crlv.lotacao("02P") == 2 and crlv.lotacao("05P") == 5
    assert crlv.lotacao("0P") is None and crlv.lotacao("100P") is None
    assert crlv.peso_bruto_kg("0,29") == 290 and crlv.peso_bruto_kg("0.29") == 290
    assert crlv.peso_bruto_kg("1,40") == 1400 and crlv.peso_bruto_kg("0,1") == 100
    assert crlv.peso_bruto_kg("0,00") == crlv.VAZIO
    assert crlv.peso_bruto_kg("*.*") is None
    assert crlv.numero_motor("kc22e1p 004401") == "KC22E1P004401"
    assert crlv.numero_motor("****") == crlv.VAZIO
    assert crlv.numero_motor("A" * 22) is None


def test_vei_09_parser_observacoes_em_varias_linhas() -> None:
    """As linhas do bloco, com as quebras, até o próximo rótulo; nos dois leiautes."""
    duas = "ALIENACAO FIDUCIARIA\nRESTRICAO JUDICIAL"
    for base in (pdfs.CRLV_TBC5H21, pdfs.CRLV_DETRAN_MOTO):
        assert crlv.extrair(_texto(replace(base, observacoes=duas)))["observacoes"] == duas
        assert "observacoes" not in crlv.extrair(_texto(base))  # só asteriscos
    # No Detran, o bloco do seguro DPVAT na mesma linha não entra nas observações.
    detran = crlv.extrair(_texto(replace(pdfs.CRLV_DETRAN_MOTO, observacoes="ALIENACAO")))
    assert detran["observacoes"] == "ALIENACAO"


def test_vei_09_processo_filho_confere_os_campos_novos() -> None:
    """A segunda barreira do pai: faixa, lista da espécie, motor e quebra só nas observações."""
    conferidos = leitura_documentos.conferir(
        "crlv",
        {
            "potencia_cv": 1500,
            "cilindrada_cc": 162,
            "especie": "particular",
            "tipo": "Motocicleta\n",
            "lotacao": 2,
            "peso_bruto_kg": 0,
            "numero_motor": "KC22-E1P",
            "observacoes": "ALIENACAO\nFIDUCIARIA",
            "proprietario": "ANTONIO",
        },
    )
    assert conferidos == {
        "cilindrada_cc": 162,
        "lotacao": 2,
        "observacoes": "ALIENACAO\nFIDUCIARIA",
    }
    resposta = leitura_documentos.executar(
        "crlv", replace(pdfs.CRLV_TBC5H21, observacoes="LINHA UM\nLINHA DOIS").pdf()
    )
    assert resposta["campos"]["observacoes"] == "LINHA UM\nLINHA DOIS"


# --- Leitura no cadastro (VEI-08, CA-421-01 a 05) ---


@pytest.mark.parametrize(
    ("documento", "esperado"),
    [
        pytest.param(
            pdfs.CRLV_TBC5H21,
            {
                "potencia_cv": 8,
                "cilindrada_cc": 109,
                "especie": "passageiro",
                "tipo": "Motocicleta",
                "carroceria": None,
                "lotacao": 2,
                "peso_bruto_kg": 240,
                "numero_motor": "JC75E1S123456",
                "observacoes": None,
            },
            id="CA-421-01-tbc5h21",
        ),
        pytest.param(
            pdfs.CRLV_ALIENADO,
            {
                "potencia_cv": None,
                "cilindrada_cc": 109,
                "especie": "passageiro",
                "tipo": "Motocicleta",
                "carroceria": None,
                "lotacao": 2,
                "peso_bruto_kg": 240,
                "numero_motor": "JC75E1S123456",
                "observacoes": "ALIENACAO FIDUCIARIA",
            },
            id="CA-421-02-alienado",
        ),
        pytest.param(
            pdfs.CRLV_CARRO,
            {
                "potencia_cv": 75,
                "cilindrada_cc": 999,
                "especie": "passageiro",
                "tipo": "Automóvel",
                "carroceria": None,
                "lotacao": 5,
                "peso_bruto_kg": 1400,
                "numero_motor": "552440012345",
                "observacoes": None,
            },
            id="CA-421-03-carro",
        ),
        pytest.param(
            pdfs.CRLV_DETRAN_MOTO,
            {
                "potencia_cv": 8,
                "cilindrada_cc": 109,
                "especie": "passageiro",
                "tipo": "Motocicleta",
                "carroceria": None,
                "lotacao": 2,
                "peso_bruto_kg": 240,
                "numero_motor": "JC75E1S123456",
                "observacoes": None,
            },
            id="detran-moto",
        ),
        pytest.param(
            pdfs.CRLV_DETRAN_CARRO,
            {
                "potencia_cv": 75,
                "cilindrada_cc": 999,
                "especie": "passageiro",
                "tipo": "Automóvel",
                "carroceria": None,
                "lotacao": 5,
                "peso_bruto_kg": 1400,
                "numero_motor": "552440012345",
                "observacoes": None,
            },
            id="detran-carro",
        ),
    ],
)
def test_vei_08_le_os_campos_da_vei_09(moto, documento, esperado) -> None:
    antes = Veiculo.objects.count()
    resposta = _ler(moto, documento)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert _da_leitura(corpo["campos"]) == esperado
    lidos_do_documento = [c for c in corpo["lidos"] if c.startswith("documento.")]
    assert lidos_do_documento == [f"documento.{c}" for c, v in esperado.items() if v is not None]
    assert corpo["quantidade"] == len(corpo["lidos"])
    assert corpo["rotulo"] == f"CRLV-e lido · {corpo['quantidade']} campos preenchidos"
    assert Veiculo.objects.count() == antes  # nada gravado


def test_vei_08_le_16_campos_com_alienacao(moto) -> None:
    """CA-421-01 e 02: a potência 0 sai, as observações entram; os dois somam 16."""
    for documento in (pdfs.CRLV_TBC5H21, pdfs.CRLV_ALIENADO):
        corpo = _ler(moto, documento).json()
        assert corpo["quantidade"] == 16
        assert corpo["rotulo"] == "CRLV-e lido · 16 campos preenchidos"


def test_vei_08_nao_le_o_que_nao_e_da_lista(moto) -> None:
    """CA-421-04: nem categoria, capacidade, CMT, eixos, CRV, segurança, DPVAT ou proprietário;
    nem rastreador ou anotações."""
    permitidas = {
        "placa",
        "chassi",
        "renavam",
        "marca",
        "modelo",
        "ano_fabricacao",
        "ano_modelo",
        "cor",
        "combustivel",
        *(f"documento.{c}" for c in DOCUMENTO_DO_QXA),
    }
    for documento in (
        pdfs.CRLV_TBC5H21,
        pdfs.CRLV_ALIENADO,
        pdfs.CRLV_QXA4B21,
        pdfs.CRLV_PNB7C04,
        pdfs.CRLV_CARRO,
        pdfs.CRLV_DETRAN_MOTO,
        pdfs.CRLV_DETRAN_CARRO,
    ):
        resposta = _ler(moto, documento)
        corpo = resposta.json()
        assert set(corpo["campos"]) == permitidas
        texto = resposta.content.decode()
        for fora in ("PARTICULAR", "123456789012", "12345678901", pdfs.PROPRIETARIO, "rastreador"):
            assert fora not in texto
        assert "anotacoes" not in corpo["campos"]


def test_vei_08_corrigidos_com_campos_novos(moto, frota) -> None:
    """CA-421-05: a lotação corrigida vale, rastreador e anotação digitados à mão, e o evento
    diz o que veio do documento com as chaves pontuadas."""
    conteudo = pdfs.CRLV_TBC5H21.pdf()
    lido = moto.api().post(LEITURA, {"arquivo": _pdf(conteudo)}, format="multipart").json()
    corpo = {
        **{k: v for k, v in lido["campos"].items() if v is not None},
        "documento.lotacao": 1,
        "rastreador.numero": "356938035643810",
        "rastreador.empresa": "Rastreia Fácil",
        "anotacoes": "Retrovisor trocado",
        "km_atual": 0,
        "categoria_id": frota.categorias["Urbana 110–125"].pk,
        "filial_id": frota.centro.pk,
        "crlv_arquivo": _pdf(conteudo),
        "crlv_validade": "2027-10-31",
        "crlv_exercicio": lido["exercicio"],
        "leitura": lido["leitura"],
    }
    resposta = moto.api().post(VEICULOS, corpo, format="multipart")
    assert resposta.status_code == 201, resposta.json()
    dados = resposta.json()
    assert dados["documento"] == {
        "potencia_cv": 8,
        "cilindrada_cc": 109,
        "especie": "passageiro",
        "tipo": "Motocicleta",
        "carroceria": None,
        "lotacao": 1,
        "peso_bruto_kg": 240,
        "numero_motor": "JC75E1S123456",
        "observacoes": None,
    }
    assert dados["rastreador"] == {"numero": "356938035643810", "empresa": "Rastreia Fácil"}
    assert dados["anotacoes"] == "Retrovisor trocado"
    veiculo = Veiculo.objects.get(placa="TBC5H21")
    assert DocumentoVeiculo.objects.filter(veiculo=veiculo, tipo="crlv", ativo=True).exists()
    evento = EventoAuditoria.objects.get(acao="veiculo.cadastrar", objeto_id=veiculo.pk)
    marca = evento.depois["preenchido_pelo_documento"]
    assert marca["corrigidos"] == ["documento.lotacao"]
    assert "documento.numero_motor" in marca["campos"] and len(marca["campos"]) == 16
    assert not any(c.startswith("rastreador") or c == "anotacoes" for c in marca["campos"])


# --- Cadastro e editar (VEI-01, VEI-09, CA-421-06 a 09) ---


def test_vei_09_campos_opcionais(moto, frota) -> None:
    """CA-421-06: só os obrigatórios; os campos da VEI-09 ficam vazios e vêm `null`."""
    resposta = moto.api().post(VEICULOS, _novo(frota), format="json")
    assert resposta.status_code == 201, resposta.json()
    dados = resposta.json()
    assert dados["combustivel"] is None
    assert dados["documento"] == DOCUMENTO_VAZIO
    assert dados["rastreador"] == {"numero": None, "empresa": None}
    assert dados["anotacoes"] is None


def test_vei_09_cadastro_com_os_blocos(moto, frota) -> None:
    """Em JSON, os blocos aninhados; o texto é limpo (pontas, maiúsculas no motor e no
    rastreador) e as observações guardam as quebras de linha."""
    corpo = _novo(
        frota,
        combustivel="flex",
        documento={
            **DOCUMENTO_DO_QXA,
            "numero_motor": " kc22e1p 004401 ",
            "observacoes": "ALIENACAO FIDUCIARIA\nRESTRICAO JUDICIAL ",
            "carroceria": "   ",
        },
        rastreador={"numero": "3569 3803 5643 809", "empresa": " Rastreia Fácil "},
        anotacoes=" Risco no tanque,\nlado esquerdo ",
    )
    resposta = moto.api("Rodrigo").post(VEICULOS, corpo, format="json")
    assert resposta.status_code == 201, resposta.json()
    dados = resposta.json()
    assert dados["documento"] == {
        **DOCUMENTO_DO_QXA,
        "observacoes": "ALIENACAO FIDUCIARIA\nRESTRICAO JUDICIAL",
    }
    assert dados["rastreador"] == RASTREADOR_DO_QXA
    assert dados["anotacoes"] == "Risco no tanque,\nlado esquerdo"
    veiculo = Veiculo.objects.get(pk=dados["id"])
    assert veiculo.carroceria == "" and veiculo.tipo_documento == "Motocicleta"
    # A Frota não traz os blocos.
    item = moto.api().get(VEICULOS, {"busca": "TBC5H21"}).json()["resultados"][0]
    assert "documento" not in item and "rastreador" not in item and "anotacoes" not in item


@pytest.mark.parametrize(
    ("corpo", "chave", "mensagem"),
    [
        ({"documento": {"potencia_cv": 1500}}, "documento.potencia_cv", "Informe a potência em cv, de 1 a 999."),  # noqa: E501
        ({"documento": {"potencia_cv": 0}}, "documento.potencia_cv", "Informe a potência em cv, de 1 a 999."),  # noqa: E501
        ({"documento": {"cilindrada_cc": 0}}, "documento.cilindrada_cc", "Informe a cilindrada em cc, de 1 a 9999."),  # noqa: E501
        ({"documento": {"lotacao": 0}}, "documento.lotacao", "Informe a lotação em pessoas, de 1 a 99."),  # noqa: E501
        ({"documento": {"lotacao": 100}}, "documento.lotacao", "Informe a lotação em pessoas, de 1 a 99."),  # noqa: E501
        ({"documento": {"peso_bruto_kg": "abc"}}, "documento.peso_bruto_kg", "Informe o peso bruto em kg."),  # noqa: E501
        ({"documento": {"especie": "particular"}}, "documento.especie", "Escolha a espécie da lista."),  # noqa: E501
        ({"documento": {"tipo": "M" * 31}}, "documento.tipo", "Use até 30 caracteres."),
        ({"documento": {"carroceria": "C" * 31}}, "documento.carroceria", "Use até 30 caracteres."),
        ({"documento": {"numero_motor": "A" * 22}}, "documento.numero_motor", "Use só letras e números, até 21."),  # noqa: E501
        ({"documento": {"numero_motor": "KC22-E1P"}}, "documento.numero_motor", "Use só letras e números, até 21."),  # noqa: E501
        ({"documento": {"observacoes": "x" * 501}}, "documento.observacoes", "Use até 500 caracteres."),  # noqa: E501
        ({"rastreador": {"numero": "1" * 21}}, "rastreador.numero", "Use só letras e números, até 20."),  # noqa: E501
        ({"rastreador": {"empresa": "E" * 61}}, "rastreador.empresa", "Use até 60 caracteres."),
        ({"anotacoes": "x" * 501}, "anotacoes", "Use até 500 caracteres."),
    ],
)  # fmt: skip
def test_vei_09_formatos(moto, frota, corpo, chave, mensagem) -> None:
    """CA-421-07: 400 com a mensagem na chave pontuada, nada gravado, no cadastro e no editar."""
    antes = Veiculo.objects.count()
    resposta = moto.api().post(VEICULOS, _novo(frota, **corpo), format="json")
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "validacao"
    assert resposta.json()["campos"] == {chave: [mensagem]}
    assert Veiculo.objects.count() == antes
    sak = frota.veiculo("SAK1D39")
    resposta = moto.api().patch(f"{VEICULOS}{sak.pk}/", corpo, format="json")
    assert resposta.status_code == 400
    assert resposta.json()["campos"] == {chave: [mensagem]}


def test_vei_09_formatos_no_servico(moto, frota) -> None:
    """O serviço confere também quando o cadastro não vem pela API (a importação, o seed)."""
    from apps.veiculos import services
    from comum.erros import ErroDeValidacao

    with pytest.raises(ErroDeValidacao) as erro:
        services.cadastrar(_novo(frota, documento={"potencia_cv": 1500, "lotacao": "2"}))
    assert erro.value.campos == {"documento.potencia_cv": ["Informe a potência em cv, de 1 a 999."]}


def test_vei_09_editar_por_chave(moto, frota) -> None:
    """Chave enviada substitui, ausente não muda, `null` ou "" apaga (dentro dos blocos)."""
    qxa = frota.veiculo("QXA4B21")
    api = moto.api("Rodrigo")
    resposta = api.patch(f"{VEICULOS}{qxa.pk}/", {"documento": {"lotacao": 1}}, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["documento"] == {**DOCUMENTO_DO_QXA, "lotacao": 1}
    assert resposta.json()["rastreador"] == RASTREADOR_DO_QXA
    resposta = api.patch(
        f"{VEICULOS}{qxa.pk}/",
        {"documento": {"observacoes": None, "tipo": ""}, "rastreador": {"empresa": None}},
        format="json",
    )
    dados = resposta.json()
    assert dados["documento"]["observacoes"] is None and dados["documento"]["tipo"] is None
    assert dados["documento"]["numero_motor"] == "KC22E1P004401"
    assert dados["rastreador"] == {"numero": "356938035643809", "empresa": None}
    assert dados["anotacoes"] == ANOTACAO_DO_QXA
    resposta = api.patch(f"{VEICULOS}{qxa.pk}/", {"anotacoes": None}, format="json")
    assert resposta.json()["anotacoes"] is None


def test_vei_09_combustivel_e_auditoria(moto, frota) -> None:
    """CA-421-08: o combustível flex do QXA-4B21 vira gasolina; a auditoria tem antes e depois,
    com as chaves pontuadas da VEI-09."""
    qxa = frota.veiculo("QXA4B21")
    assert _ficha(moto, qxa)["combustivel"] == "flex"
    resposta = moto.api("Rodrigo").patch(
        f"{VEICULOS}{qxa.pk}/",
        {"combustivel": "gasolina", "documento": {"lotacao": 1}, "rastreador": {"numero": "X1"}},
        format="json",
    )
    assert resposta.status_code == 200, resposta.json()
    assert _ficha(moto, qxa)["combustivel"] == "gasolina"
    evento = EventoAuditoria.objects.filter(acao="veiculo.editar", objeto_id=qxa.pk).latest("id")
    assert evento.antes == {
        "combustivel": "flex",
        "documento.lotacao": 2,
        "rastreador.numero": "356938035643809",
    }
    assert evento.depois == {
        "combustivel": "gasolina",
        "documento.lotacao": 1,
        "rastreador.numero": "X1",
    }
    # O motor e as observações entram inteiros (a auditoria é só do administrador).
    moto.api().patch(
        f"{VEICULOS}{qxa.pk}/", {"documento": {"numero_motor": "KC22E1P004402"}}, format="json"
    )
    evento = EventoAuditoria.objects.filter(acao="veiculo.editar", objeto_id=qxa.pk).latest("id")
    assert evento.antes == {"documento.numero_motor": "KC22E1P004401"}
    assert evento.depois == {"documento.numero_motor": "KC22E1P004402"}


def test_vei_09_quem_edita(moto, frota) -> None:
    """CA-421-09: administrador e gerente editam; vendedor, vistoriador e financeiro, 403, e a
    ficha não oferece o editar."""
    qxa = frota.veiculo("QXA4B21")
    corpo = {"documento": {"lotacao": 1}, "anotacoes": "Outra"}
    for pessoa in ("Mariana", "Rodrigo"):
        assert (
            moto.api(pessoa).patch(f"{VEICULOS}{qxa.pk}/", corpo, format="json").status_code == 200
        )
    for pessoa in SEM_MOTOR:
        resposta = moto.api(pessoa).patch(
            f"{VEICULOS}{qxa.pk}/", {"anotacoes": "Nada"}, format="json"
        )
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "permissao"
        assert _ficha(moto, qxa, pessoa)["acoes"]["editar"] is False
    qxa.refresh_from_db()
    assert qxa.anotacoes == "Outra"


# --- Ficha (VEI-09, USR-09, CA-421-11 a 14) ---


def test_vei_09_motor_e_observacoes_por_perfil(moto, frota) -> None:
    """CA-421-11 e 12: o QXA-4B21 do seed; o motor e as observações só para administrador e
    gerente, ausentes (não `null`) para os outros perfis."""
    qxa = frota.veiculo("QXA4B21")
    for pessoa in ("Mariana", "Rodrigo"):
        ficha = _ficha(moto, qxa, pessoa)
        assert ficha["combustivel"] == "flex"
        assert ficha["documento"] == DOCUMENTO_DO_QXA
        assert ficha["rastreador"] == RASTREADOR_DO_QXA
        assert ficha["anotacoes"] == ANOTACAO_DO_QXA
    sem = {c: v for c, v in DOCUMENTO_DO_QXA.items() if c not in ("numero_motor", "observacoes")}
    for pessoa in SEM_MOTOR:
        ficha = _ficha(moto, qxa, pessoa)
        assert ficha["documento"] == sem
        assert "numero_motor" not in ficha["documento"]
        assert "observacoes" not in ficha["documento"]
        assert ficha["rastreador"] == RASTREADOR_DO_QXA
        assert ficha["anotacoes"] == ANOTACAO_DO_QXA
        assert "KC22E1P004401" not in str(ficha) and "ALIENACAO" not in str(ficha)


def test_vei_09_alienacao_nao_bloqueia(moto, frota) -> None:
    """CA-421-13: com a alienação nas observações, bloquear, desbloquear, colocar à venda e
    voltar para a frota seguem como em qualquer veículo, sem alerta nem tarefa."""
    sak = frota.veiculo("SAK1D39")
    api = moto.api("Mariana")
    url = f"{VEICULOS}{sak.pk}/"
    alienado = {"documento": {"observacoes": "ALIENACAO FIDUCIARIA\nRESTRICAO JUDICIAL"}}
    assert api.patch(url, alienado, format="json").status_code == 200
    notificacoes = Notificacao.objects.count()
    for acao, corpo in (
        ("bloquear", {"motivo": "Revisão do documento"}),
        ("desbloquear", {}),
        ("colocar-a-venda", {"valor_venda_centavos": 1290000}),
        ("voltar-para-frota", {}),
    ):
        resposta = api.post(f"{url}{acao}/", corpo, format="json")
        assert resposta.status_code == 200, (acao, resposta.json())
    sak.refresh_from_db()
    assert sak.status == "disponivel"
    assert Notificacao.objects.count() == notificacoes
    assert _ficha(moto, sak, "Mariana")["situacao"]["codigo"] == "disponivel"


def test_vei_09_veiculo_antigo(moto, frota) -> None:
    """CA-421-14: o PNB-7C04 do seed não tem os campos novos; tudo `null`, sem erro."""
    pnb = frota.veiculo("PNB7C04")
    for pessoa in ("Rodrigo", "Bruna"):
        ficha = _ficha(moto, pnb, pessoa)
        assert ficha["combustivel"] is None
        esperado = (
            DOCUMENTO_VAZIO
            if pessoa == "Rodrigo"
            else {c: None for c in DOCUMENTO_VAZIO if c not in ("numero_motor", "observacoes")}
        )
        assert ficha["documento"] == esperado
        assert ficha["rastreador"] == {"numero": None, "empresa": None}
        assert ficha["anotacoes"] is None


def test_vei_09_isolamento_entre_empresas(moto, frota) -> None:
    """Os dados do QXA-4B21 da empresa A não aparecem na empresa B."""
    assert Veiculo.objects.filter(numero_motor="KC22E1P004401").exists()
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not Veiculo.objects.filter(numero_motor="KC22E1P004401").exists()
    assert not Veiculo.objects.exclude(anotacoes="").exists()


# --- Leitura no editar (padrão A, CA-421-10) ---


def _rota(veiculo: Veiculo) -> str:
    return f"{VEICULOS}{veiculo.pk}/leitura-crlv/"


def test_vei_08_leitura_no_editar(moto, frota) -> None:
    """CA-421-10: o PNB-7C04 com o próprio CRLV-e; placa e chassi fora da resposta, nada
    gravado, o documento CRLV do veículo não muda."""
    pnb = frota.veiculo("PNB7C04")
    documentos = list(DocumentoVeiculo.objects.filter(veiculo=pnb).values_list("pk", "arquivo"))
    resposta = _ler(moto, pdfs.CRLV_PNB7C04, pessoa="Rodrigo", rota=_rota(pnb))
    assert resposta.status_code == 200, resposta.json()
    assert resposta["Cache-Control"] == "no-store"
    corpo = resposta.json()
    assert "placa" not in corpo["campos"] and "chassi" not in corpo["campos"]
    assert "placa" not in corpo["lidos"] and "chassi" not in corpo["lidos"]
    assert corpo["campos"]["marca"] == "Yamaha" and corpo["campos"]["renavam"] == "00987654330"
    assert _da_leitura(corpo["campos"]) == {
        "potencia_cv": 12,
        "cilindrada_cc": 149,
        "especie": "passageiro",
        "tipo": "Motocicleta",
        "carroceria": None,
        "lotacao": 2,
        "peso_bruto_kg": 270,
        "numero_motor": "E3V1E0012345",
        "observacoes": None,
    }
    assert corpo["quantidade"] == len(corpo["lidos"]) == 14
    assert corpo["rotulo"] == "CRLV-e lido · 14 campos preenchidos"
    pnb_depois = Veiculo.objects.get(pk=pnb.pk)
    assert pnb_depois.potencia_cv is None and pnb_depois.combustivel is None  # nada gravado
    assert (
        list(DocumentoVeiculo.objects.filter(veiculo=pnb).values_list("pk", "arquivo"))
        == documentos
    )


def test_vei_08_leitura_no_editar_outro_veiculo(moto, frota) -> None:
    """CA-421-10: o CRLV-e do TBC-5H21 no PNB-7C04 → 422 `crlv_outro_veiculo`, sem campos."""
    pnb = frota.veiculo("PNB7C04")
    resposta = _ler(moto, pdfs.CRLV_TBC5H21, pessoa="Rodrigo", rota=_rota(pnb))
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "crlv_outro_veiculo",
        "mensagem": "Este CRLV-e é de outro veículo.",
        "detalhes": None,
    }
    # Só a placa igual não basta: todo o que foi lido tem de ser igual.
    trocado = replace(pdfs.CRLV_PNB7C04, chassi="9C6RG3110PR003303")
    assert _ler(moto, trocado, "Rodrigo", _rota(pnb)).json()["codigo"] == "crlv_outro_veiculo"
    # Sem placa e sem chassi lidos, não dá para conferir: a 422 VEI-08 de sempre.
    sem_identificacao = replace(pdfs.CRLV_PNB7C04, placa="*******", chassi="*****")
    resposta = _ler(moto, sem_identificacao, "Rodrigo", _rota(pnb))
    assert resposta.status_code == 422 and resposta.json()["codigo"] == "VEI-08"


def test_vei_08_leitura_no_editar_quem_pode(moto, frota) -> None:
    """Os mesmos perfis da leitura do cadastro; fora das filiais da pessoa, 404."""
    pnb = frota.veiculo("PNB7C04")
    for pessoa in SEM_MOTOR:
        resposta = _ler(moto, pdfs.CRLV_PNB7C04, pessoa=pessoa, rota=_rota(pnb))
        assert resposta.status_code == 403
    resposta = _ler(
        moto, pdfs.CRLV_PNB7C04, pessoa="Rodrigo", rota=f"{VEICULOS}999999/leitura-crlv/"
    )
    assert resposta.status_code == 404


def test_vei_08_editar_com_comprovante(moto, frota) -> None:
    """O `PATCH` com o comprovante da leitura no editar: o evento leva
    `preenchido_pelo_documento`; o comprovante de outro veículo, do cadastro ou de outra pessoa
    não marca nada."""
    pnb = frota.veiculo("PNB7C04")
    api = moto.api("Rodrigo")
    lido = _ler(moto, pdfs.CRLV_PNB7C04, pessoa="Rodrigo", rota=_rota(pnb)).json()
    # A tela manda o que foi lido, com a lotação corrigida pela pessoa.
    documento = {**_da_leitura(lido["campos"]), "lotacao": 1}
    corpo = {
        **{c: v for c, v in lido["campos"].items() if "." not in c and v is not None},
        "documento": documento,
        "leitura": lido["leitura"],
    }
    resposta = api.patch(f"{VEICULOS}{pnb.pk}/", corpo, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["documento"]["lotacao"] == 1
    evento = EventoAuditoria.objects.filter(acao="veiculo.editar", objeto_id=pnb.pk).latest("id")
    marca = evento.depois["preenchido_pelo_documento"]
    assert marca["tipo"] == "crlv"
    assert set(marca["campos"]) == set(lido["lidos"])
    assert marca["corrigidos"] == ["documento.lotacao"]
    assert "comprovante" not in str(evento.depois) and lido["leitura"] not in str(evento.depois)

    def sem_marca(leitura: str, veiculo: Veiculo, pessoa: str = "Rodrigo") -> None:
        resposta = moto.api(pessoa).patch(
            f"{VEICULOS}{veiculo.pk}/",
            {"anotacoes": "Conferido", "leitura": leitura},
            format="json",
        )
        assert resposta.status_code == 200, resposta.json()
        evento = EventoAuditoria.objects.filter(acao="veiculo.editar", objeto_id=veiculo.pk).latest(
            "id"
        )
        assert "preenchido_pelo_documento" not in evento.depois
        moto.api(pessoa).patch(f"{VEICULOS}{veiculo.pk}/", {"anotacoes": None}, format="json")

    sem_marca(lido["leitura"], frota.veiculo("SAK1D39"))  # outro veículo
    sem_marca(lido["leitura"], pnb, pessoa="Mariana")  # outra pessoa
    do_cadastro = _ler(moto, pdfs.CRLV_PNB7C04, pessoa="Rodrigo").json()["leitura"]
    sem_marca(do_cadastro, pnb)  # leitura do cadastro
    sem_marca(lido["leitura"] + "x", pnb)  # adulterado


def test_vei_08_comprovante_do_editar_nao_vale_no_cadastro(moto, frota) -> None:
    """O comprovante do editar leva o veículo; no cadastro, ele não marca nada."""
    pnb = frota.veiculo("PNB7C04")
    conteudo = pdfs.CRLV_PNB7C04.pdf()
    lido = moto.api("Rodrigo").post(_rota(pnb), {"arquivo": _pdf(conteudo)}, format="multipart")
    corpo = {
        **_novo(frota, placa="TBC5H29", chassi="9C2JC7510SR000129"),
        "crlv_arquivo": _pdf(conteudo),
        "crlv_validade": "2027-10-31",
        "leitura": lido.json()["leitura"],
    }
    resposta = moto.api("Rodrigo").post(VEICULOS, corpo, format="multipart")
    assert resposta.status_code == 201, resposta.json()
    evento = EventoAuditoria.objects.get(acao="veiculo.cadastrar", objeto_id=resposta.json()["id"])
    assert "preenchido_pelo_documento" not in evento.depois
