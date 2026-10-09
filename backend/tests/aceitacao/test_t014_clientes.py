"""T-014 · Clientes, documentos, bloqueio, LGPD (docs/qa/criterios/T-014.md).

Roda na `empresa_a` com as pessoas da Moto Rápida e a Filial Centro, com o relógio em 07 out
2026, 10:00. Os blocos de locações, financeiro e vendas ainda não existem: onde o critério é
[integração] (CA-014-15, 16, 19, 20, 21 e parte do 18), o fornecedor é falso, registrado pela
mesma porta que o app de verdade vai usar (ADR 0011 e 0015). Os números do seed completo
(612 clientes, R$ 1.646,40 em aberto) voltam na T-019.
"""

import io
from datetime import date
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django_tenants.utils import schema_context
from PIL import Image

from apps.aprovacoes import services as aprovacoes_services
from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.clientes import selectors
from apps.clientes.models import Cliente, DocumentoCliente
from apps.contas.models import Usuario
from apps.plataforma.models import Empresa
from apps.plataforma.services import abrir_acesso_suporte
from comum import arquivos, eventos, leituras
from comum.erros import SemPermissao
from comum.permissoes import filiais_permitidas

from .conftest import cliente as cliente_http
from .test_t012_filiais import HOST, MotoRapida
from .test_t013_veiculos import _caucaia

LISTA = "/api/clientes/"
DOCUMENTOS = ("cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia")

JULIANA: dict[str, Any] = {
    "tipo": "pf",
    "nome": "Juliana Rocha",
    "documento": "052.218.330-18",
    "nascimento": "1998-02-14",
    "celular": "85981142290",
    "email": "juliana@email.com",
    "profissao": "Entregadora",
    "cnh": {
        "numero": "04512345678",
        "categoria": "A",
        "validade": "2029-05-10",
        "primeira_habilitacao": "2017-06-01",
    },
    "endereco": {
        "cep": "60325000",
        "logradouro": "Rua Padre Mororó",
        "numero": "145",
        "complemento": None,
        "bairro": "Centro",
        "cidade": "Fortaleza",
        "uf": "CE",
    },
    "referencia": {"nome": "Maria Rocha", "parentesco": "mãe", "telefone": "85999990000"},
    "consentimento": True,
}
LUCAS = {
    "tipo": "pf",
    "nome": "Lucas Ferreira",
    "documento": "12345678909",
    "celular": "85988771203",
}
PJ = {
    "tipo": "pj",
    "nome": "Entregas Já Ltda",
    "documento": "12.345.678/0001-95",
    "celular": "8532221100",
}


def _pessoa(nome: str, documento: str, celular: str, **extra: Any) -> dict[str, Any]:
    """Cadastro completo com os dados da Juliana e outro nome, CPF e celular."""
    return {**JULIANA, "nome": nome, "documento": documento, "celular": celular, **extra}


RAFAEL = _pessoa("Rafael Sousa", "32137710587", "85987651234")
ANA = _pessoa("Ana Beatriz Lima", "74155201658", "85986543210")
CARLOS = _pessoa("Carlos Menezes", "25890144227", "85985554433")
PATRICIA = _pessoa("Patrícia Gomes", "36912987451", "85984443322")
DIEGO = _pessoa("Diego Martins", "14778912349", "85983332211")


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    moto = MotoRapida(empresa_a, planos["Profissional"])
    moto.centro()
    return moto


def _jpg(com_gps: bool = False) -> bytes:
    imagem = Image.new("RGB", (16, 16), "red")
    exif = imagem.getexif()
    if com_gps:
        exif[0x010F] = "Celular da Bruna"  # Make
        gps = exif.get_ifd(0x8825)
        gps[1] = "S"
        gps[2] = (3.0, 43.0, 30.0)
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", exif=exif)
    return saida.getvalue()


def _arquivo(conteudo: bytes | None = None, nome: str = "foto.jpg") -> SimpleUploadedFile:
    return SimpleUploadedFile(nome, conteudo or _jpg(), content_type="image/jpeg")


def _post(moto: MotoRapida, corpo: dict[str, Any], quem: str = "Bruna"):
    return moto.api(quem).post(LISTA, corpo, format="json")


def _criar(moto: MotoRapida, corpo: dict[str, Any], quem: str = "Bruna") -> dict[str, Any]:
    resposta = _post(moto, corpo, quem)
    assert resposta.status_code == 201, resposta.json()
    return dict(resposta.json())


def _patch(moto: MotoRapida, cliente_id: int, corpo: dict[str, Any], quem: str = "Bruna"):
    return moto.api(quem).patch(f"{LISTA}{cliente_id}/", corpo, format="json")


def _enviar(
    moto: MotoRapida,
    cliente_id: int,
    tipo: str,
    quem: str = "Bruna",
    arquivo: SimpleUploadedFile | None = None,
):
    return moto.api(quem).post(
        f"{LISTA}{cliente_id}/documentos/",
        {"tipo": tipo, "arquivo": arquivo or _arquivo()},
        format="multipart",
    )


def _completo(moto: MotoRapida, corpo: dict[str, Any]) -> dict[str, Any]:
    criado = _criar(moto, corpo)
    for tipo in DOCUMENTOS:
        resposta = _enviar(moto, criado["id"], tipo)
        assert resposta.status_code == 201, resposta.json()
    return dict(resposta.json())


def _get(moto: MotoRapida, cliente_id: int, quem: str = "Mariana") -> dict[str, Any]:
    resposta = moto.api(quem).get(f"{LISTA}{cliente_id}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _acao(moto: MotoRapida, quem: str, cliente_id: int, acao: str, motivo: str = "Conferido"):
    return moto.api(quem).post(f"{LISTA}{cliente_id}/{acao}/", {"motivo": motivo}, format="json")


def _lista(moto: MotoRapida, quem: str = "Mariana", **params: str) -> dict[str, Any]:
    resposta = moto.api(quem).get(LISTA, params)
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _nomes(corpo: dict[str, Any]) -> list[str]:
    return sorted(c["nome"] for c in corpo["resultados"])


# --- Cadastro (CLI-01, CLI-03, CLI-08) ---


def test_cli_01_ca_014_01_cpf_validado_e_unico(moto):
    errado = _post(moto, {**LUCAS, "documento": "123.456.789-00"})
    assert errado.status_code == 400
    assert errado.json()["codigo"] == "validacao"
    assert "documento" in errado.json()["campos"]
    assert _post(moto, {**LUCAS, "documento": "111.111.111-11"}).status_code == 400

    juliana = _criar(moto, JULIANA)
    repetido = _post(moto, {**LUCAS, "documento": "05221833018"})
    assert repetido.status_code == 409
    assert repetido.json()["codigo"] == "CLI-01"
    assert repetido.json()["mensagem"] == "Já existe um cliente com este CPF"
    assert repetido.json()["detalhes"] == {"cliente_id": juliana["id"], "nome": "Juliana Rocha"}

    criada = _criar(moto, PJ)
    assert criada["documento"] == "12345678000195"
    outra = _post(moto, {**PJ, "nome": "Outra", "documento": "12345678000195"})
    assert (outra.status_code, outra.json()["codigo"]) == (409, "CLI-01")
    assert outra.json()["mensagem"] == "Já existe um cliente com este CNPJ"
    assert _post(moto, {**PJ, "documento": "12.345.678/0001-10"}).status_code == 400

    # CEP inválido e categoria fora da lista: 400.
    assert _post(moto, {**LUCAS, "endereco": {"cep": "6032"}}).status_code == 400
    assert _post(moto, {**LUCAS, "cnh": {"categoria": "Z"}}).status_code == 400

    # Trocar o documento pelo PATCH passa pelas mesmas validações.
    lucas = _criar(moto, LUCAS)
    troca = _patch(moto, lucas["id"], {"documento": "05221833018"})
    assert (troca.status_code, troca.json()["codigo"]) == (409, "CLI-01")
    assert _patch(moto, lucas["id"], {"documento": "12345678900"}).status_code == 400


def test_cli_03_ca_014_02_salvar_incompleto(moto):
    lucas = _criar(moto, LUCAS)
    assert lucas["status"] == "incompleto"
    assert lucas["pendencias"] == [
        *DOCUMENTOS,
        "consentimento",
        "cnh",
        "endereco",
        "referencia",
        "nascimento",
    ]
    assert lucas["situacao"] == {
        "codigo": "incompleto",
        "rotulo": "Cadastro incompleto",
        "tom": "alerta",
    }
    assert lucas["cliente_desde"] == "2026-10-07"

    # PJ: o responsável no lugar do nascimento.
    pj = _criar(moto, PJ)
    assert "responsavel" in pj["pendencias"] and "nascimento" not in pj["pendencias"]
    com_responsavel = _patch(
        moto,
        pj["id"],
        {"responsavel": {"nome": "Paulo Lima", "cpf": "963.852.741-28", "celular": "85981110000"}},
    )
    assert com_responsavel.json()["responsavel"] == {
        "nome": "Paulo Lima",
        "cpf": "96385274128",
        "celular": "85981110000",
    }
    assert "responsavel" not in com_responsavel.json()["pendencias"]


def test_cli_03_ca_014_03_completar_leva_a_ativo(moto):
    lucas = _criar(moto, LUCAS)
    dados = {k: v for k, v in JULIANA.items() if k not in ("tipo", "nome", "documento", "celular")}
    resposta = _patch(moto, lucas["id"], dados)
    assert resposta.json()["status"] == "incompleto"
    assert resposta.json()["pendencias"] == list(DOCUMENTOS)

    for tipo in DOCUMENTOS[:-1]:
        assert _enviar(moto, lucas["id"], tipo).json()["status"] == "incompleto"
    ultimo = _enviar(moto, lucas["id"], DOCUMENTOS[-1]).json()
    assert (ultimo["status"], ultimo["pendencias"]) == ("ativo", [])
    assert EventoAuditoria.objects.filter(
        acao="cliente.completar_cadastro", objeto_id=lucas["id"], regra="CLI-03"
    ).exists()

    # Tirar o endereço volta a incompleto.
    sem = _patch(moto, lucas["id"], {"endereco": None})
    assert (sem.json()["status"], sem.json()["pendencias"]) == ("incompleto", ["endereco"])
    assert sem.json()["endereco"] is None

    # Bloqueado que completa o cadastro continua bloqueado.
    assert _acao(moto, "Rodrigo", lucas["id"], "bloquear", "Documento falso").status_code == 200
    volta = _patch(moto, lucas["id"], {"endereco": JULIANA["endereco"]})
    assert (volta.json()["status"], volta.json()["pendencias"]) == ("bloqueado", [])


def test_cli_03_ca_014_04_consentimento(moto, relogio):
    lucas = _criar(moto, LUCAS)
    assert lucas["consentimento_em"] is None
    relogio.em("2026-10-07 10:30")
    sim = _patch(moto, lucas["id"], {"consentimento": True})
    assert sim.json()["consentimento_em"] == "2026-10-07T13:30:00Z"
    relogio.em("2026-10-08 09:00")
    moto._tokens.clear()  # a sessão de 12 horas do dia 07 terminou
    nao = _patch(moto, lucas["id"], {"consentimento": False})
    assert nao.json()["consentimento_em"] == "2026-10-07T13:30:00Z"
    de_novo = _patch(moto, lucas["id"], {"consentimento": True})
    assert de_novo.json()["consentimento_em"] == "2026-10-07T13:30:00Z"


def test_cli_08_ca_014_05_salvar_e_iniciar_locacao(moto):
    """O mesmo POST: o frontend abre a Nova locação com o `id` devolvido."""
    from apps.clientes.api import urls

    criado = _criar(moto, LUCAS)
    assert Cliente.objects.filter(pk=criado["id"]).exists()
    assert not any("iniciar" in str(rota.pattern) for rota in urls.urlpatterns)


def test_cli_08_ca_014_06_quem_cadastra(moto):
    for quem, documento in (
        ("Mariana", "12345678909"),
        ("Rodrigo", "05221833018"),
        ("Bruna", "32137710587"),
    ):
        criado = _criar(moto, {**LUCAS, "documento": documento}, quem)
        assert _patch(moto, criado["id"], {"profissao": "Entregador"}, quem).status_code == 200
    alvo = Cliente.objects.first()
    assert alvo is not None
    for quem in ("João", "Lúcia"):
        assert _post(moto, {**LUCAS, "documento": "74155201658"}, quem).status_code == 403
        assert _patch(moto, alvo.pk, {"profissao": "X"}, quem).status_code == 403
        assert _enviar(moto, alvo.pk, "cnh_frente", quem).status_code == 403


# --- Dados pessoais (AUD-04, AUD-05, AUD-09) ---

CAMPOS_COMPLETOS = {"documento", "cnh", "endereco", "documentos", "referencia", "nascimento"}


def test_aud_04_ca_014_07_mascara_nas_listas(moto):
    _criar(moto, JULIANA)
    _criar(moto, LUCAS)
    _criar(moto, PJ)
    for quem in ("Mariana", "Rodrigo", "Bruna", "João", "Lúcia"):
        resultados = {c["nome"]: c for c in _lista(moto, quem)["resultados"]}
        assert resultados["Juliana Rocha"]["documento_mascarado"] == "***.218.330-**"
        assert resultados["Lucas Ferreira"]["documento_mascarado"] == "***.456.789-**"
        assert resultados["Entregas Já Ltda"]["documento_mascarado"] == "12345678000195"
        for item in resultados.values():
            assert not CAMPOS_COMPLETOS & set(item)


def test_aud_04_ca_014_08_detalhe_completo_so_para_quem_cadastra(moto):
    juliana = _criar(moto, JULIANA)
    for quem in ("Mariana", "Rodrigo", "Bruna"):
        corpo = _get(moto, juliana["id"], quem)
        assert corpo["documento"] == "05221833018"
        assert corpo["cnh"]["numero"] == "04512345678"
        assert corpo["endereco"]["cidade"] == "Fortaleza"
        assert corpo["idade"] == 28
    for quem in ("João", "Lúcia"):
        corpo = _get(moto, juliana["id"], quem)
        assert corpo["documento_mascarado"] == "***.218.330-**"
        assert not CAMPOS_COMPLETOS & set(corpo)
        assert moto.api(quem).get(f"{LISTA}{juliana['id']}/analise/").status_code == 403


def _suporte(moto: MotoRapida, permissao: str):
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
        Empresa.objects.get(pk=moto.empresa.pk),
        diego,
        motivo="Chamado #1042",
        duracao_minutos=30,
        permissao=permissao,
    )
    connection.set_tenant(moto.empresa)
    return cliente_http(HOST, str(token))


def test_aud_09_ca_014_09_suporte_giro_sempre_mascarado(moto, relogio_jwt):
    juliana = _completo(moto, JULIANA)
    for permissao in ("ver", "ver_editar"):
        api = _suporte(moto, permissao)
        detalhe = api.get(f"{LISTA}{juliana['id']}/")
        assert detalhe.status_code == 200, detalhe.json()
        assert detalhe.json()["documento_mascarado"] == "***.218.330-**"
        assert not CAMPOS_COMPLETOS & set(detalhe.json())
        texto = detalhe.content.decode()
        for aberto in ("05221833018", "04512345678", "arquivos.invalid", "Padre Mororó"):
            assert aberto not in texto

        busca = api.get(LISTA, {"busca": "05221833018"})
        assert busca.status_code == 200
        assert [c["documento_mascarado"] for c in busca.json()["resultados"]] == ["***.218.330-**"]
        assert "05221833018" not in busca.content.decode()

    # "Ver e editar" edita o cadastro, e a resposta continua resumida.
    editado = api.patch(f"{LISTA}{juliana['id']}/", {"profissao": "Motogirl"}, format="json")
    assert editado.status_code == 200, editado.json()
    assert "documento" not in editado.json()
    assert Cliente.objects.get(pk=juliana["id"]).profissao == "Motogirl"
    # Nenhuma URL de documento foi gerada para o suporte.
    assert not EventoAuditoria.objects.filter(
        acao="documento_cliente.ver", ator_tipo="suporte"
    ).exists()


def test_aud_05_ca_014_10_documentos_privados(moto):
    juliana = _criar(moto, JULIANA)
    foto = _enviar(moto, juliana["id"], "cnh_frente", arquivo=_arquivo(_jpg(com_gps=True)))
    assert foto.status_code == 201, foto.json()

    # Reprocessada: sem EXIF (nem GPS, nem marca do aparelho).
    documento = DocumentoCliente.ativos.get(cliente_id=juliana["id"], tipo="cnh_frente")
    guardado, tipo_conteudo = arquivos.guardados[documento.arquivo.name]
    assert tipo_conteudo == "image/jpeg"
    assert b"Exif" not in guardado and b"Celular da Bruna" not in guardado
    with Image.open(io.BytesIO(guardado)) as imagem:
        assert dict(imagem.getexif()) == {}
        assert imagem.size == (16, 16)
    assert documento.arquivo.name.startswith(f"empresa_a/clientes/documentocliente/{documento.pk}/")

    # URL de 15 minutos, nova a cada GET, e cada geração auditada com quem viu.
    primeira = _get(moto, juliana["id"], "Rodrigo")["documentos"][0]
    segunda = _get(moto, juliana["id"], "Rodrigo")["documentos"][0]
    assert primeira["tipo"] == "cnh_frente" and primeira["url"] != segunda["url"]
    assert primeira["url_expira_em"] == "2026-10-07T13:15:00Z"
    vistos = EventoAuditoria.objects.filter(
        acao="documento_cliente.ver", objeto_id=documento.pk, ator_id=moto.pessoas["Rodrigo"].pk
    )
    assert vistos.count() == 2
    assert all(v.regra == "AUD-05" for v in vistos)
    # Sem documento, sem URL.
    assert _get(moto, juliana["id"])["documentos"][2] == {
        "tipo": "selfie_documento",
        "enviado_em": None,
        "url": None,
        "url_expira_em": None,
    }

    # Mais de 10 MB, formato falso e imagem quebrada: 400.
    grande = _arquivo(b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024))
    assert _enviar(moto, juliana["id"], "cnh_verso", arquivo=grande).status_code == 400
    falso = SimpleUploadedFile("cnh.pdf", b"MZ\x90\x00programa", content_type="application/pdf")
    assert _enviar(moto, juliana["id"], "cnh_verso", arquivo=falso).status_code == 400
    quebrada = _arquivo(b"\xff\xd8\xff\xe0" + b"nao e imagem")
    assert _enviar(moto, juliana["id"], "cnh_verso", arquivo=quebrada).status_code == 400

    # Reenviar a frente deixa a anterior inativa e guardada.
    assert _enviar(moto, juliana["id"], "cnh_frente").status_code == 201
    todas = DocumentoCliente.objects.filter(cliente_id=juliana["id"], tipo="cnh_frente")
    assert sorted(d.ativo for d in todas) == [False, True]
    assert documento.arquivo.name in arquivos.guardados
    assert EventoAuditoria.objects.filter(
        acao="documento_cliente.substituir", objeto_id=documento.pk
    ).exists()


def test_aud_05_pdf_aceito_como_veio(moto):
    juliana = _criar(moto, JULIANA)
    pdf = b"%PDF-1.4\n% comprovante\n"
    arquivo = SimpleUploadedFile("conta.pdf", pdf, content_type="application/pdf")
    resposta = _enviar(moto, juliana["id"], "comprovante_residencia", arquivo=arquivo)
    assert resposta.status_code == 201
    documento = DocumentoCliente.ativos.get(cliente_id=juliana["id"])
    assert arquivos.guardados[documento.arquivo.name] == (pdf, "application/pdf")


def test_aud_04_ca_014_11_auditoria_sem_dado_pessoal_aberto(moto):
    juliana = _completo(moto, JULIANA)
    novo = {**JULIANA["endereco"], "logradouro": "Av. Duque de Caxias", "numero": "900"}
    _patch(moto, juliana["id"], {"endereco": novo}, "Rodrigo")
    evento = EventoAuditoria.objects.filter(acao="cliente.editar", objeto_id=juliana["id"]).latest(
        "id"
    )
    assert evento.antes == {"logradouro": "***", "numero": "***"}
    assert evento.depois == {"logradouro": "***", "numero": "***"}

    # Reenviar o mesmo CPF não gera "alterado" falso (R-05 da T-050).
    _patch(moto, juliana["id"], {"documento": "052.218.330-18"}, "Rodrigo")
    ultimo = EventoAuditoria.objects.filter(acao="cliente.editar").latest("id")
    assert "documento" not in ultimo.depois

    textos = " ".join(
        str((e.antes, e.depois)) for e in EventoAuditoria.objects.filter(objeto_tipo="cliente")
    )
    for aberto in ("05221833018", "052.218.330-18", "04512345678", "Juliana", "Padre Mororó"):
        assert aberto not in textos


def test_aud_06_auditoria_de_cliente_nao_guarda_nome_nem_documento_completos(moto):
    """Teste obrigatório da ADR 0014 (e R-02 da T-050): o evento de criação do cliente guarda
    nome em iniciais, CPF e CNH omitidos, contato e referência mascarados."""
    juliana = _criar(moto, JULIANA)
    evento = EventoAuditoria.objects.get(acao="cliente.cadastrar", objeto_id=juliana["id"])
    depois = evento.depois
    assert depois["nome"] == "J. R."
    assert depois["documento"] == {"alterado": True}
    assert depois["documento_hash"] == {"alterado": True}
    assert depois["cnh_numero"] == {"alterado": True}
    assert depois["celular"] == "(85) *****-2290"
    assert depois["email"] == "j***@e***.com"
    assert depois["nascimento"] == "1998"
    assert depois["referencia_nome"] == "M. R."
    assert depois["referencia_telefone"] == "(85) *****-0000"
    assert (depois["cidade"], depois["uf"], depois["logradouro"]) == ("Fortaleza", "CE", "***")


def test_cli_01_ca_014_12_busca_por_cpf(moto):
    _criar(moto, JULIANA)
    _criar(moto, LUCAS)
    assert _nomes(_lista(moto, busca="05221833018")) == ["Juliana Rocha"]
    assert _nomes(_lista(moto, busca="052.218")) == []
    assert _nomes(_lista(moto, busca="Juli")) == ["Juliana Rocha"]
    assert _nomes(_lista(moto, busca="98114")) == ["Juliana Rocha"]
    assert _nomes(_lista(moto, busca="12345678909")) == ["Lucas Ferreira"]


# --- Análise do cadastro (CLI-02, CLI-04) ---


def test_cli_02_ca_014_13_itens_da_analise(moto):
    juliana = _completo(moto, JULIANA)
    esperado = [
        {"codigo": "cpf", "situacao": "ok", "rotulo": "CPF válido"},
        {"codigo": "cnh", "situacao": "ok", "rotulo": "CNH categoria A, válida"},
        {"codigo": "lista_bloqueio", "situacao": "ok", "rotulo": "Fora da lista de bloqueio"},
        {"codigo": "historico", "situacao": "pendente", "rotulo": "Sem histórico"},
        {"codigo": "documentos", "situacao": "ok", "rotulo": "Documentos enviados"},
    ]
    assert juliana["analise"]["itens"] == esperado
    rota = moto.api("Bruna").get(f"{LISTA}{juliana['id']}/analise/")
    assert rota.json()["itens"] == esperado

    lucas = _criar(moto, {**LUCAS, **{k: JULIANA[k] for k in ("cnh", "endereco")}})
    _enviar(moto, lucas["id"], "cnh_frente")
    _enviar(moto, lucas["id"], "cnh_verso")
    itens = {i["codigo"]: i for i in _get(moto, lucas["id"])["analise"]["itens"]}
    assert itens["documentos"] == {
        "codigo": "documentos",
        "situacao": "pendente",
        "rotulo": "Faltam 2 documentos",
    }

    # Sem gravar nada: o mesmo resultado (sem documentos ainda).
    antes = (Cliente.objects.count(), EventoAuditoria.objects.count())
    analisar = moto.api("Bruna").post(
        f"{LISTA}analisar/", {**JULIANA, "documento": "74155201658"}, format="json"
    )
    assert analisar.status_code == 200, analisar.json()
    assert analisar.json()["itens"][:4] == esperado[:4]
    assert analisar.json()["itens"][4]["rotulo"] == "Faltam 4 documentos"
    assert (Cliente.objects.count(), EventoAuditoria.objects.count()) == antes

    # Na lista de bloqueio: o CPF já é de cliente bloqueado.
    _acao(moto, "Rodrigo", juliana["id"], "bloquear", "Documento falso")
    repetido = moto.api("Bruna").post(f"{LISTA}analisar/", JULIANA, format="json").json()
    assert repetido["itens"][2] == {
        "codigo": "lista_bloqueio",
        "situacao": "problema",
        "rotulo": "Consta na lista de bloqueio",
    }
    invalido = moto.api("Bruna").post(
        f"{LISTA}analisar/", {**JULIANA, "documento": "12345678900"}, format="json"
    )
    assert invalido.json()["itens"][0] == {
        "codigo": "cpf",
        "situacao": "problema",
        "rotulo": "CPF inválido",
    }


def _com_cnh(moto: MotoRapida, documento: str, categoria: str, validade: str) -> Cliente:
    criado = _completo(
        moto,
        _pessoa(
            f"Cliente {documento[:3]}",
            documento,
            "85980000000",
            cnh={**JULIANA["cnh"], "categoria": categoria, "validade": validade},
        ),
    )
    return Cliente.objects.get(pk=criado["id"])


def test_cli_02_ca_014_14_impedimentos_para_retirada(moto):
    hoje = date(2026, 10, 7)

    def codigos(cliente: Cliente, tipo: str = "moto") -> list[str]:
        return [i["codigo"] for i in selectors.impedimentos_para_retirada(cliente, tipo, hoje)]

    lucas = Cliente.objects.get(pk=_criar(moto, LUCAS)["id"])
    assert "CLI-03" in codigos(lucas)

    so_b = _com_cnh(moto, "32137710587", "B", "2029-05-10")
    assert codigos(so_b, "moto") == ["CLI-02"]
    assert codigos(so_b, "carro") == []
    so_a = _com_cnh(moto, "74155201658", "A", "2029-05-10")
    assert codigos(so_a, "carro") == ["CLI-02"]

    vinte_dias = _com_cnh(moto, "25890144227", "A", "2026-09-17")
    assert codigos(vinte_dias) == []
    assert _get(moto, vinte_dias.pk)["cnh"]["situacao"] == "vencida"
    trinta_e_um = _com_cnh(moto, "36912987451", "A", "2026-09-06")
    assert codigos(trinta_e_um) == ["CLI-02"]
    assert _get(moto, trinta_e_um.pk)["cnh"]["situacao"] == "vencida_impede"
    trinta = _com_cnh(moto, "14778912349", "A", "2026-09-07")
    assert codigos(trinta) == []

    juliana = Cliente.objects.get(pk=_completo(moto, JULIANA)["id"])
    assert codigos(juliana) == []
    assert _get(moto, juliana.pk)["cnh"]["situacao"] == "valida"

    _acao(moto, "Rodrigo", so_a.pk, "bloquear", "Atraso combinado")
    so_a.refresh_from_db()
    assert "CLI-05" in codigos(so_a)
    _acao(moto, "Rodrigo", juliana.pk, "inativar")
    juliana.refresh_from_db()
    assert codigos(juliana) == ["cliente_inativo"]


# --- Bloqueio (CLI-05, APR-05, APR-09) ---


def test_cli_05_ca_014_15_bloqueio_automatico_com_15_dias(moto, relogio):
    """[integração] O financeiro de verdade publica na T-017; aqui o evento é publicado à mão."""
    carlos = _completo(moto, CARLOS)
    vencimento = date(2026, 9, 23)
    eventos.publicar(
        "financeiro.parcela_atrasou",
        cliente_id=carlos["id"],
        dias_atraso=14,
        vencimento=vencimento,
    )
    assert _get(moto, carlos["id"])["status"] == "ativo"

    relogio.em("2026-10-08 09:00")
    moto._tokens.clear()  # a sessão de 12 horas do dia 07 terminou
    eventos.publicar(
        "financeiro.parcela_atrasou",
        cliente_id=carlos["id"],
        dias_atraso=15,
        vencimento=vencimento,
    )
    corpo = _get(moto, carlos["id"])
    assert corpo["status"] == "bloqueado"
    assert corpo["bloqueio"] == {
        "motivo": "atraso",
        "desde": "2026-10-08T12:00:00Z",
        "descricao": "Conta com 15 dias de atraso desde 23/09/2026",
        "desbloqueia_sozinho": True,
    }
    evento = EventoAuditoria.objects.get(acao="cliente.bloquear", objeto_id=carlos["id"])
    assert (evento.ator_tipo, evento.regra) == ("sistema", "CLI-05")

    # Rafael, 25 dias: bloqueado; e o evento repetido não muda nada.
    rafael = _completo(moto, RAFAEL)
    for _ in range(2):
        eventos.publicar("financeiro.parcela_atrasou", cliente_id=rafael["id"], dias_atraso=25)
    assert _get(moto, rafael["id"])["status"] == "bloqueado"
    bloqueios = EventoAuditoria.objects.filter(acao="cliente.bloquear", objeto_id=rafael["id"])
    assert bloqueios.count() == 1


def test_cli_05_ca_014_16_desbloqueio_automatico_ao_quitar(moto):
    """[integração] `financeiro` registra o contador de contas com 15 dias de atraso."""
    rafael = _completo(moto, RAFAEL)
    eventos.publicar("financeiro.parcela_atrasou", cliente_id=rafael["id"], dias_atraso=25)
    atrasadas = {"n": 2}
    leituras.registrar_contador(
        selectors.ALVO, selectors.CONTADOR_ATRASO_PARA_BLOQUEIO, lambda _id: atrasadas["n"]
    )
    try:
        atrasadas["n"] = 1  # pagou uma de duas
        eventos.publicar("financeiro.parcela_paga", parcela_id=1, cliente_id=rafael["id"])
        assert _get(moto, rafael["id"])["status"] == "bloqueado"
        atrasadas["n"] = 0  # quitou
        eventos.publicar("financeiro.parcela_paga", parcela_id=2, cliente_id=rafael["id"])
        assert _get(moto, rafael["id"])["status"] == "ativo"
        assert _get(moto, rafael["id"])["bloqueio"] is None

        # Com pendência de cadastro, volta a incompleto.
        lucas = _criar(moto, LUCAS)
        eventos.publicar("financeiro.parcela_atrasou", cliente_id=lucas["id"], dias_atraso=15)
        assert _get(moto, lucas["id"])["status"] == "bloqueado"
        eventos.publicar("financeiro.parcela_paga", parcela_id=3, cliente_id=lucas["id"])
        assert _get(moto, lucas["id"])["status"] == "incompleto"

        # Bloqueio manual não sai sozinho.
        ana = _completo(moto, ANA)
        _acao(moto, "Rodrigo", ana["id"], "bloquear", "Documento falso")
        eventos.publicar("financeiro.parcela_paga", parcela_id=4, cliente_id=ana["id"])
        assert _get(moto, ana["id"])["status"] == "bloqueado"
    finally:
        leituras.remover_contador(selectors.ALVO, selectors.CONTADOR_ATRASO_PARA_BLOQUEIO)


def test_cli_05_ca_014_17_bloqueio_e_desbloqueio_manuais(moto):
    ana = _completo(moto, ANA)
    bloqueio = _acao(moto, "Rodrigo", ana["id"], "bloquear", "Documento falso")
    assert bloqueio.status_code == 200, bloqueio.json()
    assert bloqueio.json()["status"] == "bloqueado"
    assert bloqueio.json()["bloqueio"]["motivo"] == "manual"
    assert bloqueio.json()["bloqueio"]["descricao"] == "Documento falso"
    assert bloqueio.json()["bloqueio"]["desbloqueia_sozinho"] is False
    assert bloqueio.json()["acao_principal"] is None  # bloqueado sem valor em aberto
    de_novo = _acao(moto, "Rodrigo", ana["id"], "bloquear", "De novo")
    assert (de_novo.status_code, de_novo.json()["codigo"]) == (409, "transicao_cliente")

    # Gerente e administrador desbloqueiam na hora, com auditoria.
    for quem in ("Rodrigo", "Mariana"):
        livre = _acao(moto, quem, ana["id"], "desbloquear", "Documento conferido")
        assert (livre.status_code, livre.json()["status"]) == (200, "ativo")
        evento = EventoAuditoria.objects.filter(
            acao="cliente.desbloquear", objeto_id=ana["id"]
        ).latest("id")
        assert (evento.ator_id, evento.motivo) == (moto.pessoas[quem].pk, "Documento conferido")
        _acao(moto, "Mariana", ana["id"], "bloquear", "Documento falso")

    # A vendedora pede (APR-05), e Ana continua bloqueada.
    pedido = _acao(moto, "Bruna", ana["id"], "desbloquear", "Cliente apresentou o original")
    assert pedido.status_code == 202, pedido.json()
    assert pedido.json()["pedido_aprovacao"]["tipo"] == "APR-05"
    assert pedido.json()["pedido_aprovacao"]["status"] == "pendente"
    assert _get(moto, ana["id"])["status"] == "bloqueado"
    repetido = _acao(moto, "Bruna", ana["id"], "desbloquear", "De novo")
    assert (repetido.status_code, repetido.json()["codigo"]) == (409, "pedido_pendente")

    pedido_id = pedido.json()["pedido_aprovacao"]["id"]
    salvo = PedidoAprovacao.objects.get(pk=pedido_id)
    assert (salvo.origem_tipo, salvo.origem_id) == ("cliente", ana["id"])
    assert {salvo.filial_id} == filiais_permitidas(moto.pessoas["Bruna"])

    # APR-09: quem pediu não aprova o próprio pedido, nem com permissão extra.
    bruna = moto.pessoas["Bruna"]
    bruna.permissoes_extras = ["aprovar_desconto", "cancelar_contrato"]
    bruna.save(update_fields=["permissoes_extras"])
    propria = moto.api("Bruna").post(f"/api/aprovacoes/{pedido_id}/aprovar/", {}, format="json")
    assert propria.status_code in (403, 404)
    with pytest.raises(SemPermissao) as erro:
        aprovacoes_services.aprovar(salvo, bruna)
    assert erro.value.codigo == "APR-09"
    assert _get(moto, ana["id"])["status"] == "bloqueado"

    # Rodrigo aprova: Ana volta a ativo.
    aprovado = moto.api("Rodrigo").post(f"/api/aprovacoes/{pedido_id}/aprovar/", {}, format="json")
    assert aprovado.status_code == 200, aprovado.json()
    assert _get(moto, ana["id"])["status"] == "ativo"
    evento = EventoAuditoria.objects.filter(acao="cliente.desbloquear", objeto_id=ana["id"]).latest(
        "id"
    )
    assert (evento.ator_id, evento.regra) == (moto.pessoas["Rodrigo"].pk, "APR-05")

    # Gerente que desbloqueia direto cancela o pedido pendente.
    _acao(moto, "Rodrigo", ana["id"], "bloquear", "Documento falso")
    outro = _acao(moto, "Bruna", ana["id"], "desbloquear", "Original apresentado").json()
    _acao(moto, "Rodrigo", ana["id"], "desbloquear", "Conferi eu mesmo")
    assert PedidoAprovacao.objects.get(pk=outro["pedido_aprovacao"]["id"]).status == "cancelado"

    # Quem não pode.
    assert _acao(moto, "Bruna", ana["id"], "bloquear").status_code == 403
    for quem in ("João", "Lúcia"):
        assert _acao(moto, quem, ana["id"], "bloquear").status_code == 403
        assert _acao(moto, quem, ana["id"], "desbloquear").status_code == 403
    sem_motivo = moto.api("Rodrigo").post(f"{LISTA}{ana['id']}/bloquear/", {}, format="json")
    assert sem_motivo.status_code == 400
    nao_bloqueada = _acao(moto, "Rodrigo", ana["id"], "desbloquear")
    assert (nao_bloqueada.status_code, nao_bloqueada.json()["codigo"]) == (
        409,
        "transicao_cliente",
    )


# --- Inativar (CLI-09) ---


def test_cli_09_ca_014_18_inativar_e_reativar(moto):
    ana = _completo(moto, ANA)
    inativa = _acao(moto, "Rodrigo", ana["id"], "inativar", "Mudou de cidade")
    assert (inativa.status_code, inativa.json()["status"]) == (200, "inativo")
    assert inativa.json()["situacao"]["rotulo"] == "Inativo"
    assert _nomes(_lista(moto)) == []
    assert _nomes(_lista(moto, situacao="inativos")) == ["Ana Beatriz Lima"]
    cliente = Cliente.objects.get(pk=ana["id"])
    assert selectors.impedimentos_para_nova_locacao(cliente) == [
        {"codigo": "cliente_inativo", "mensagem": "O cliente está inativo."}
    ]
    assert selectors.impedimentos_para_venda(cliente)[0]["codigo"] == "cliente_inativo"

    reativa = _acao(moto, "Rodrigo", ana["id"], "reativar", "Voltou")
    assert (reativa.status_code, reativa.json()["status"]) == (200, "ativo")
    lucas = _criar(moto, LUCAS)
    _acao(moto, "Mariana", lucas["id"], "inativar", "Duplicado")
    assert _acao(moto, "Mariana", lucas["id"], "reativar", "Engano").json()["status"] == (
        "incompleto"
    )

    assert _acao(moto, "Bruna", ana["id"], "inativar").status_code == 403
    assert _acao(moto, "Bruna", ana["id"], "reativar").status_code == 403

    # [integração] Com locação aberta: 422 (contador falso de `locacoes`).
    juliana = _completo(moto, JULIANA)
    leituras.registrar_contador(selectors.ALVO, "locacao_aberta", lambda _id: 1)
    try:
        recusada = _acao(moto, "Rodrigo", juliana["id"], "inativar", "Teste")
        assert recusada.status_code == 422
        assert recusada.json()["codigo"] == "cliente_com_pendencia"
        assert recusada.json()["detalhes"] == {
            "locacao_aberta": True,
            "em_aberto_centavos": 0,
            "venda_aberta": False,
        }
    finally:
        leituras.remover_contador(selectors.ALVO, "locacao_aberta")


# --- Lista (CLI-06, CLI-07) ---


@pytest.fixture
def fornecedores_falsos():
    """Blocos e filtros de locações, financeiro e vendas como os apps de verdade vão registrar
    (ADR 0015), com a situação do seed."""
    por_nome: dict[str, dict[str, Any]] = {
        "Carlos Menezes": {
            "locacao_atual": {"id": 2841, "codigo": "LOC-2841", "alerta": "Parcela atrasada"},
            "financeiro": {"em_aberto_centavos": 29940, "conta_mais_antiga_id": 9001},
        },
        "Rafael Sousa": {
            "locacao_atual": {"id": 2790, "codigo": "LOC-2790", "alerta": None},
            "financeiro": {"em_aberto_centavos": 134700, "conta_mais_antiga_id": 9002},
        },
        "Lucas Ferreira": {"locacao_atual": {"id": 2856, "codigo": "LOC-2856", "alerta": None}},
        "Diego Martins": {
            "locacao_atual": {"id": 2848, "codigo": "LOC-2848", "alerta": None},
            "venda_aberta": {"id": 177, "codigo": "VEN-0177", "veiculo": "CB 300F"},
        },
        "Juliana Rocha": {"locacao_atual": {"id": 2836, "codigo": "LOC-2836", "alerta": None}},
        "Patrícia Gomes": {
            "locacao_atual": {"id": 2812, "codigo": "LOC-2812", "alerta": "Cancelando"}
        },
    }
    registradas = []
    for bloco in ("locacao_atual", "financeiro", "venda_aberta"):

        def montar(cliente: Any, bloco: str = bloco) -> dict[str, Any] | None:
            dados: dict[str, Any] | None = por_nome.get(cliente.nome, {}).get(bloco)
            return dados

        anotacao = leituras.Anotacao(bloco, lambda qs: qs, montar)
        leituras._anotacoes[selectors.ALVO].append(anotacao)
        registradas.append(anotacao)
    com_locacao = [n for n, b in por_nome.items() if "locacao_atual" in b]
    em_aberto = [n for n, b in por_nome.items() if "financeiro" in b]
    leituras.registrar_filtro(
        selectors.ALVO, "com_locacao", lambda qs: qs.filter(nome__in=com_locacao)
    )
    leituras.registrar_filtro(selectors.ALVO, "em_aberto", lambda qs: qs.filter(nome__in=em_aberto))
    yield
    for anotacao in registradas:
        leituras._anotacoes[selectors.ALVO].remove(anotacao)
    leituras.remover_filtro(selectors.ALVO, "com_locacao")
    leituras.remover_filtro(selectors.ALVO, "em_aberto")


def _seed_da_lista(moto: MotoRapida) -> None:
    for dados in (CARLOS, RAFAEL, DIEGO, JULIANA, PATRICIA, ANA):
        _completo(moto, dados)
    _criar(moto, LUCAS)
    rafael = Cliente.objects.get(nome="Rafael Sousa")
    eventos.publicar("financeiro.parcela_atrasou", cliente_id=rafael.pk, dias_atraso=25)


def test_cli_07_ca_014_19_acao_principal(moto):
    """Sem os blocos (T-014): valem as linhas de Lucas e de Ana."""
    _seed_da_lista(moto)
    acoes = {c["nome"]: c["acao_principal"] for c in _lista(moto)["resultados"]}
    lucas = Cliente.objects.get(nome="Lucas Ferreira")
    ana = Cliente.objects.get(nome="Ana Beatriz Lima")
    assert acoes["Lucas Ferreira"] == {
        "codigo": "completar_cadastro",
        "rotulo": "Completar cadastro",
        "alvo": {"tipo": "cliente", "id": lucas.pk},
    }
    assert acoes["Ana Beatriz Lima"] == {
        "codigo": "nova_locacao",
        "rotulo": "Nova locação",
        "alvo": {"tipo": "cliente", "id": ana.pk},
    }
    assert acoes["Rafael Sousa"] is None  # bloqueado, e o valor em aberto ainda não chega


def test_cli_07_ca_014_19_acao_principal_com_os_blocos(moto, fornecedores_falsos):
    """[integração] A ordem completa, com fornecedores falsos no lugar de locações,
    financeiro e vendas."""
    _seed_da_lista(moto)
    acoes = {c["nome"]: c["acao_principal"] for c in _lista(moto)["resultados"]}
    assert acoes["Carlos Menezes"]["codigo"] == "cobrar"
    assert acoes["Carlos Menezes"]["alvo"] == {"tipo": "conta", "id": 9001}
    assert acoes["Rafael Sousa"]["codigo"] == "cobrar"
    assert acoes["Lucas Ferreira"]["codigo"] == "completar_cadastro"
    assert acoes["Diego Martins"] == {
        "codigo": "ver_proposta",
        "rotulo": "Ver proposta",
        "alvo": {"tipo": "venda", "id": 177},
    }
    assert acoes["Juliana Rocha"]["codigo"] == "ver_locacao"
    assert acoes["Patrícia Gomes"]["alvo"] == {"tipo": "locacao", "id": 2812}
    assert acoes["Ana Beatriz Lima"]["codigo"] == "nova_locacao"


def test_cli_06_ca_014_20_situacao_na_lista(moto, fornecedores_falsos):
    """[integração] Rótulos com os fornecedores falsos."""
    _seed_da_lista(moto)
    rotulos = {c["nome"]: c["situacao"]["rotulo"] for c in _lista(moto)["resultados"]}
    assert rotulos == {
        "Rafael Sousa": "Bloqueado",
        "Patrícia Gomes": "Cancelando",
        "Carlos Menezes": "Parcela atrasada",
        "Lucas Ferreira": "Cadastro incompleto",
        "Juliana Rocha": "Em dia",
        "Diego Martins": "Em dia",
        "Ana Beatriz Lima": "Sem locação",
    }


def test_cli_06_ca_014_21_contagens_e_indicadores(moto):
    _seed_da_lista(moto)
    corpo = _lista(moto)
    assert corpo["contagens"] == {
        "todos": 7,
        "com_locacao": None,
        "em_aberto": None,
        "bloqueados": 1,
        "incompletos": 1,
        "inativos": 0,
    }
    assert corpo["indicadores"] == {
        "novos_no_mes_anterior": 0,
        "com_locacao_pct": None,
        "em_aberto_total_centavos": None,
    }
    assert _lista(moto, situacao="com_locacao")["resultados"] == []
    # Clientes de setembro contam como novos do mês anterior.
    for nome in ("Juliana Rocha", "Ana Beatriz Lima"):
        cliente = Cliente.objects.get(nome=nome)
        cliente.cliente_desde = date(2026, 9, 12)
        cliente.save(update_fields=["cliente_desde"])
    assert _lista(moto)["indicadores"]["novos_no_mes_anterior"] == 2


def test_cli_06_ca_014_21_contagens_com_os_filtros(moto, fornecedores_falsos):
    """[integração] Com os filtros de locações e financeiro registrados."""
    _seed_da_lista(moto)
    corpo = _lista(moto)
    assert corpo["contagens"]["com_locacao"] == 6
    assert corpo["contagens"]["em_aberto"] == 2
    assert corpo["indicadores"]["com_locacao_pct"] == "85.71"
    assert _nomes(_lista(moto, situacao="em_aberto")) == ["Carlos Menezes", "Rafael Sousa"]


def test_cli_07_ca_014_22_filtros(moto):
    _seed_da_lista(moto)
    caucaia = _caucaia(moto, "Mariana")
    assert _nomes(_lista(moto, situacao="bloqueados")) == ["Rafael Sousa"]
    ana = Cliente.objects.get(nome="Ana Beatriz Lima")
    _acao(moto, "Rodrigo", ana.pk, "bloquear", "Fraude")
    assert _nomes(_lista(moto, situacao="bloqueados")) == ["Ana Beatriz Lima", "Rafael Sousa"]
    assert _nomes(_lista(moto, situacao="incompletos")) == ["Lucas Ferreira"]

    # O cliente é da empresa: a lista é a mesma nas duas filiais.
    [centro] = filiais_permitidas(moto.pessoas["Rodrigo"])
    da_centro = moto.api("Mariana", HTTP_X_FILIAL=str(centro)).get(LISTA).json()
    da_caucaia = moto.api("Mariana", HTTP_X_FILIAL=str(caucaia.pk)).get(LISTA).json()
    assert _nomes(da_centro) == _nomes(da_caucaia) == _nomes(_lista(moto))
    assert len(da_centro["resultados"]) == 7

    so_pj = _lista(moto, tipo="pj")
    assert so_pj["resultados"] == [] and so_pj["contagens"]["todos"] == 0
    por_nome = [c["nome"] for c in _lista(moto, ordem="nome")["resultados"]]
    assert por_nome == sorted(por_nome)


# --- Isolamento entre empresas ---


def test_cli_01_cliente_da_empresa_a_nao_aparece_na_b(moto):
    juliana = _criar(moto, JULIANA)
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    try:
        assert not Cliente.objects.filter(pk=juliana["id"]).exists()
        assert Cliente.objects.count() == 0
    finally:
        connection.set_tenant(moto.empresa)
    assert Cliente.objects.filter(pk=juliana["id"]).exists()
