"""T-090 · Contratos: modelos, PDF, assinatura e aditivo (CA-015-11 a 13, `docs/api/contratos.md`).

Cenário da T-015: Moto Rápida em 07 out 2026, 10:00, com o modelo "Locação semanal" publicado e
a LOC-2856 do Lucas Ferreira (SAK1D39) como a próxima locação. As tarefas (PDF e envio) rodam
depois do commit, capturadas com `django_capture_on_commit_callbacks`.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.contratos import pdf, selectors
from apps.contratos import services as contratos
from apps.contratos.models import Contrato, ModeloContrato
from apps.locacoes import contrato as contrato_da_locacao
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes.models import Locacao
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import Empresa, UsoEmpresa
from comum.conexao import conexao
from integracoes.whatsapp.falso import caixa_de_saida

from .conftest import cliente
from .frota import montar_frota
from .test_t012_filiais import HOST, MotoRapida
from .test_t015_locacoes import LISTA, Cenario

MODELOS = "/api/contratos/modelos/"
CONSULTAR = "/api/publico/assinaturas/consultar/"
ASSINAR = "/api/publico/assinaturas/assinar/"
HOST_B = "empresa-b.localhost"


@pytest.fixture
def moto(empresa_a, planos, relogio) -> Cenario:
    """O cenário da T-015, com a marca da locadora no nome da empresa e o WhatsApp vazio.
    O cliente de teste chega pelo proxy confiável, com o IP no `X-Forwarded-For`."""
    locacoes_leituras.registrar()
    empresa_a.nome_exibicao = "Moto Rápida"
    empresa_a.save(update_fields=["nome_exibicao"])
    base = MotoRapida(empresa_a, planos["Profissional"])
    caixa_de_saida.clear()
    return Cenario(base, montar_frota(base))


@contextmanager
def _tarefas(capturar: Any) -> Iterator[None]:
    """Roda as tarefas do commit. A tarefa entra e sai do schema da empresa e deixa a conexão
    no public; o teste volta para a empresa A, como depois de uma requisição."""
    with capturar(execute=True):
        yield
    conexao().set_tenant(Empresa.objects.get(schema_name="empresa_a"))


def _publica(host: str = HOST, ip: str = "200.150.10.77") -> Any:
    api = cliente(host)
    api.credentials(HTTP_X_FORWARDED_FOR=ip, HTTP_USER_AGENT="Chrome 129 no Android")
    return api


def _gerar(moto: Cenario, capturar: Any, locacao_id: int, quem: str = "Bruna") -> Any:
    with _tarefas(capturar):
        return moto.moto.api(quem).post(f"{LISTA}{locacao_id}/contrato/")


def _token(indice: int = -1) -> str:
    return caixa_de_saida[indice].texto.split("/assinar#", 1)[1].split(" ", 1)[0]


def _assinar(token: str, nome: str = "Lucas Ferreira", capturar: Any = None) -> Any:
    corpo = {"token": token, "aceite": True, "nome_completo": nome}
    if capturar is None:
        return _publica().post(ASSINAR, corpo, format="json")
    with _tarefas(capturar):
        return _publica().post(ASSINAR, corpo, format="json")


def _contrato(locacao_id: int) -> Contrato:
    return Contrato.objects.get(origem_tipo="locacao", origem_id=locacao_id, tipo="contrato")


# --- CA-015-11 · Gerar e enviar ---


def test_fin_03_ca_015_11_gerar_e_enviar_contrato(moto, django_capture_on_commit_callbacks):
    locacao = moto.confirmada()
    assert locacao["codigo"] == "LOC-2856" and locacao["status"] == "aguardando_retirada"

    resposta = _gerar(moto, django_capture_on_commit_callbacks, locacao["id"])
    assert resposta.status_code == 202, resposta.json()
    assert resposta.json() == {"contrato_id": resposta.json()["contrato_id"], "status": "gerado"}

    contrato = _contrato(locacao["id"])
    assert contrato.status == "enviado"
    assert (contrato.modelo_id, contrato.versao_modelo) == (moto.modelo.pk, 1)
    assert contrato.versao_texto_html == "<p>Lucas Ferreira</p>"
    assert contrato.pdf.open().read().startswith(b"%PDF-")
    assert len(contrato.hash_pdf) == 64
    # O link sai por WhatsApp com a marca da locadora; o token vai no fragmento e o banco
    # guarda só o hash (S-15).
    mensagem = caixa_de_saida[-1]
    assert mensagem.celular == "85988771203"
    assert mensagem.texto.startswith("Moto Rápida:")
    assert "https://empresa-a.localhost/assinar#" in mensagem.texto
    assert "giro" not in mensagem.texto.lower().replace("empresa-a.localhost", "")
    assert contrato.token_assinatura_hash == contratos.hash_do_token(_token())

    detalhe = moto.detalhe(locacao["id"])
    assert detalhe["contrato"]["status"] == "enviado"
    assert detalhe["contrato"]["versao"] == 1 and detalhe["contrato"]["pdf_disponivel"] is True
    assert detalhe["acoes"]["reenviar_contrato"] is True
    assert detalhe["acoes"]["imprimir_contrato"] is True
    pdf_url = moto.moto.api("Bruna").get(f"{LISTA}{locacao['id']}/contrato/pdf/").json()
    assert pdf_url["url"].startswith("https://") and pdf_url["url_expira_em"]

    segundo = _gerar(moto, django_capture_on_commit_callbacks, locacao["id"])
    assert (segundo.status_code, segundo.json()["codigo"]) == (409, "contrato_existente")
    assert Contrato.objects.count() == 1


def test_ca_015_11_contrato_recusado_com_desconto_pendente_ou_fora_de_hora(
    moto, django_capture_on_commit_callbacks
):
    urbana = moto.veiculo("Urbana 110–125")
    com_desconto = moto.confirmada(desconto_pct="7.00", veiculo=urbana)
    assert com_desconto["desconto"]["status"] == "pendente"
    resposta = _gerar(moto, django_capture_on_commit_callbacks, com_desconto["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "desconto_pendente")

    rascunho = moto.criar()
    resposta = _gerar(moto, django_capture_on_commit_callbacks, rascunho["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "contrato_fora_de_hora")
    assert not Contrato.objects.exists()


def test_ca_015_11_perfis_do_contrato(moto, django_capture_on_commit_callbacks):
    locacao = moto.confirmada()
    assert (
        _gerar(moto, django_capture_on_commit_callbacks, locacao["id"], "João").status_code == 403
    )
    assert (
        _gerar(moto, django_capture_on_commit_callbacks, locacao["id"], "Lúcia").status_code == 403
    )
    assert (
        _gerar(moto, django_capture_on_commit_callbacks, locacao["id"], "Rodrigo").status_code
        == 202
    )
    pdf_do_vistoriador = moto.moto.api("João").get(f"{LISTA}{locacao['id']}/contrato/pdf/")
    assert pdf_do_vistoriador.status_code == 403


# --- CA-015-12 · Link de assinatura ---


def test_s_15_ca_015_12_link_de_assinatura(moto, relogio, django_capture_on_commit_callbacks):
    locacao = moto.confirmada()
    _gerar(moto, django_capture_on_commit_callbacks, locacao["id"])
    token = _token()
    contrato = _contrato(locacao["id"])
    assert contrato.token_assinatura_expira_em == relogio.agora + contratos.VALIDADE_DO_LINK

    relogio.em("2026-10-14 09:00")
    consulta = _publica().post(CONSULTAR, {"token": token}, format="json")
    assert consulta.status_code == 200, consulta.json()
    corpo = consulta.json()
    assert corpo["empresa"]["nome_exibicao"] == "Moto Rápida"
    assert corpo["contrato"]["codigo"] == "LOC-2856"
    assert corpo["contrato"]["titulo"] == "Contrato de locação semanal"
    assert corpo["contrato"]["cliente_nome"] == "Lucas Ferreira"
    assert corpo["contrato"]["status"] == "enviado"
    assert corpo["contrato"]["pdf_url"].startswith("https://")
    assert corpo["contrato"]["pdf_url_expira_em"] == "2026-10-14T12:15:00Z"  # 15 min (AUD-05)

    relogio.em("2026-10-15 10:00")
    vencido = _publica().post(CONSULTAR, {"token": token}, format="json")
    assert vencido.status_code == 410
    assert vencido.json()["codigo"] == "link_expirado"
    assert vencido.json()["mensagem"] == "Este link venceu. Peça um novo à locadora."
    assert _assinar(token).json()["codigo"] == "link_expirado"

    relogio.em("2026-10-08 18:00")
    errado = _assinar(token, "Lucas F.")
    assert (errado.status_code, errado.json()["codigo"]) == (400, "nome_nao_confere")
    assert errado.json()["mensagem"] == "Digite seu nome completo como está no cadastro"

    assinado = _assinar(token, "  lúcas   FERREIRA ", django_capture_on_commit_callbacks)
    assert assinado.status_code == 200, assinado.json()
    assert assinado.json() == {"status": "assinado", "assinado_em": "2026-10-08T21:00:00Z"}

    contrato.refresh_from_db()
    assert contrato.status == "assinado"
    assert contrato.assinado_ip == "200.150.10.77"
    assert contrato.assinatura_aparelho == "Chrome 129 no Android"
    assert contrato.pdf_assinado.open().read().startswith(b"%PDF-")
    assert len(contrato.hash_pdf_assinado) == 64
    assert contrato.hash_pdf_assinado != contrato.hash_pdf
    # A locação recebe a condição pelo evento `contratos.contrato_assinado`.
    assert Locacao.objects.get(pk=locacao["id"]).contrato_assinado_em == contrato.assinado_em
    # Na auditoria, o IP vai mascarado (/24) e o token não aparece.
    evento = EventoAuditoria.objects.filter(acao="contrato.assinado").get()
    assert evento.depois["assinado_ip"] == "200.150.10.0/24"
    assert "token_assinatura_hash" not in evento.depois

    de_novo = _assinar(token)
    assert (de_novo.status_code, de_novo.json()["codigo"]) == (410, "contrato_ja_assinado")
    consulta = _publica().post(CONSULTAR, {"token": token}, format="json")
    assert consulta.json()["codigo"] == "contrato_ja_assinado"


def test_s_15_ca_015_12_reenviar_invalida_o_link_anterior(moto, django_capture_on_commit_callbacks):
    locacao = moto.confirmada()
    _gerar(moto, django_capture_on_commit_callbacks, locacao["id"])
    antigo = _token()
    with _tarefas(django_capture_on_commit_callbacks):
        resposta = moto.moto.api("Bruna").post(f"{LISTA}{locacao['id']}/contrato/reenviar/")
    assert resposta.status_code == 202, resposta.json()
    novo = _token()
    assert novo != antigo and len(caixa_de_saida) == 2

    assert _publica().post(CONSULTAR, {"token": antigo}, format="json").status_code == 404
    assert _publica().post(CONSULTAR, {"token": novo}, format="json").status_code == 200
    assert _assinar(antigo).status_code == 404
    assert _assinar(novo, capturar=django_capture_on_commit_callbacks).status_code == 200

    # Depois de assinado, reenviar manda o PDF assinado, sem link de assinatura.
    with _tarefas(django_capture_on_commit_callbacks):
        moto.moto.api("Bruna").post(f"{LISTA}{locacao['id']}/contrato/reenviar/")
    assert "/assinar#" not in caixa_de_saida[-1].texto
    assert "assinado" in caixa_de_saida[-1].texto


def test_s_15_token_desconhecido_e_limite_por_ip(moto):
    assert _publica().post(CONSULTAR, {"token": "nao-existe"}, format="json").status_code == 404
    respostas = [
        _publica(ip="200.150.10.99").post(CONSULTAR, {"token": f"t{i}"}, format="json")
        for i in range(10)
    ]
    assert {r.status_code for r in respostas} == {404}
    estourou = _publica(ip="200.150.10.99").post(CONSULTAR, {"token": "t"}, format="json")
    assert (estourou.status_code, estourou.json()["codigo"]) == (429, "muitas_requisicoes")


def test_s_15_limite_por_token(moto):
    for i in range(20):
        ip = f"200.150.{i}.1"
        assert _publica(ip=ip).post(CONSULTAR, {"token": "mesmo"}, format="json").status_code == 404
    estourou = _publica(ip="200.151.0.1").post(CONSULTAR, {"token": "mesmo"}, format="json")
    assert estourou.status_code == 429


def test_s_15_token_da_empresa_a_nao_abre_na_b(moto, django_capture_on_commit_callbacks):
    """Isolamento: o token é procurado só no schema do host."""
    locacao = moto.confirmada()
    _gerar(moto, django_capture_on_commit_callbacks, locacao["id"])
    resposta = _publica(HOST_B).post(CONSULTAR, {"token": _token()}, format="json")
    assert resposta.status_code == 404


# --- CA-015-13 · Modelo ---


def test_s_09_ca_015_13_modelo_de_contrato(moto, django_capture_on_commit_callbacks):
    api = moto.moto.api("Mariana")
    invalido = api.post(
        MODELOS,
        {"nome": "Teste", "finalidade": "locacao", "texto": "<p>{{cliente.salario}}</p>"},
        format="json",
    )
    assert invalido.status_code == 400
    assert invalido.json()["codigo"] == "marcador_invalido"
    assert invalido.json()["mensagem"] == "Campo desconhecido: {{cliente.salario}}"
    assert invalido.json()["campos"] == {"texto": ["Campo desconhecido: {{cliente.salario}}"]}

    sujo = (
        '<p onclick="roubar()" style="color:red">Oi, {{cliente.nome}}</p>'
        '<script>alert(1)</script><img src="http://169.254.169.254/latest">'
        '<table><tr><td colspan="2" onmouseover="x">A</td></tr></table>'
    )
    criado = api.post(
        MODELOS, {"nome": "Limpo", "finalidade": "locacao", "texto": sujo}, format="json"
    )
    assert criado.status_code == 201, criado.json()
    assert criado.json()["texto"] == (
        '<p>Oi, {{cliente.nome}}</p><table><tbody><tr><td colspan="2">A</td></tr></tbody></table>'
    )
    assert criado.json()["status"] == "rascunho" and criado.json()["versao_publicada"] is None

    # Contrato gerado com a versão 1; editar o modelo publicado cria a versão 2 e o contrato
    # mantém o texto da versão dele (LOC-15).
    locacao = moto.confirmada()
    _gerar(moto, django_capture_on_commit_callbacks, locacao["id"])
    editado = api.patch(
        f"{MODELOS}{moto.modelo.pk}/", {"texto": "<p>Novo, {{cliente.nome}}</p>"}, format="json"
    )
    assert editado.status_code == 200, editado.json()
    assert editado.json()["versao_publicada"] == 1 and editado.json()["tem_rascunho"] is True
    moto.modelo.refresh_from_db()
    assert moto.modelo.texto == "<p>{{cliente.nome}}</p>" and moto.modelo.publicado is True
    publicado = api.post(f"{MODELOS}{editado.json()['id']}/publicar/")
    assert publicado.status_code == 200, publicado.json()
    assert publicado.json()["versao_publicada"] == 2
    assert [v["versao"] for v in publicado.json()["versoes"]] == [2, 1]
    contrato = _contrato(locacao["id"])
    assert (contrato.versao_modelo, contrato.versao_texto_html) == (1, "<p>Lucas Ferreira</p>")

    # Arquivar o último modelo de locação publicado: 422 IMP-04.
    ultimo = api.post(f"{MODELOS}{moto.modelo.pk}/arquivar/")
    assert ultimo.status_code == 422
    assert ultimo.json()["codigo"] == "IMP-04"
    assert ultimo.json()["mensagem"] == (
        "A empresa precisa de ao menos um modelo de locação publicado"
    )
    assert api.post(f"{MODELOS}{criado.json()['id']}/publicar/").status_code == 200
    arquivado = api.post(f"{MODELOS}{moto.modelo.pk}/arquivar/")
    assert arquivado.status_code == 200 and arquivado.json()["arquivado"] is True
    assert ModeloContrato.objects.filter(grupo=moto.modelo.grupo, arquivado=False).count() == 0


def test_fin_03_ca_015_13_sem_clausula_nao_cobra_juros(moto, django_capture_on_commit_callbacks):
    """O modelo do cenário não usa `{{cobranca.*}}`: contrato sem cláusula, sem juros."""
    sem = moto.confirmada()
    _gerar(moto, django_capture_on_commit_callbacks, sem["id"])
    assert _contrato(sem["id"]).clausula_juros is False
    assert selectors.permite_juros("locacao", sem["id"]) is False

    api = moto.moto.api("Mariana")
    pronto = api.post(MODELOS, {"a_partir_de": "locacao_semanal_moto"}, format="json").json()
    assert set(pronto["marcadores_usados"]) >= {
        "cobranca.multa_atraso_pct",
        "cobranca.juros_mes_pct",
    }
    api.post(f"{MODELOS}{pronto['id']}/publicar/")
    com = moto.confirmada(veiculo=moto.veiculo("Urbana 110–125"))
    _gerar(moto, django_capture_on_commit_callbacks, com["id"])
    contrato = _contrato(com["id"])
    assert contrato.clausula_juros is True
    assert selectors.permite_juros("locacao", com["id"]) is True
    assert "multa de 2,00% e juros de 1,00% ao mês" in contrato.versao_texto_html
    assert selectors.permite_juros("locacao", 999999) is False


def test_s_09_pdf_nao_busca_url_externa():
    """`test_pdf_nao_busca_url_externa` (S-09): o buscador só entrega o logo da empresa."""
    pedidas: list[str] = []
    buscar = pdf.buscador(pdf.Marca(nome="Moto Rápida"))

    def espiao(url: str, *args: Any, **kwargs: Any) -> Any:
        pedidas.append(url)
        return buscar(url)

    for url in (
        "http://169.254.169.254/latest/meta-data/",
        "https://exemplo.com/x.png",
        "file:///etc/passwd",
        "data:image/png;base64,AAAA",
        pdf.URL_DO_LOGO,  # a empresa sem logo também recusa
    ):
        with pytest.raises(pdf.UrlRecusada):
            buscar(url)

    from weasyprint import HTML  # type: ignore[import-untyped]

    corpo = (
        '<p>x</p><img src="http://169.254.169.254/latest/meta-data/">'
        '<p style="background: url(file:///etc/passwd)">y</p>'
    )
    conteudo = HTML(
        string=pdf.documento(corpo, pdf.Marca(nome="Moto Rápida")), url_fetcher=espiao
    ).write_pdf()
    assert conteudo.startswith(b"%PDF-")
    assert set(pedidas) == {"http://169.254.169.254/latest/meta-data/", "file:///etc/passwd"}

    com_logo = pdf.buscador(pdf.Marca(nome="M", logo_svg=b"<svg/>"))
    assert com_logo(pdf.URL_DO_LOGO).read() == b"<svg/>"


def test_s_09_contrato_marcador_fora_da_lista_recusado(moto):
    """`test_contrato_marcador_fora_da_lista_recusado` (S-09): ao salvar e ao publicar."""
    api = moto.moto.api("Mariana")
    rascunho = api.patch(
        f"{MODELOS}{moto.modelo.pk}/", {"texto": "<p>{{ locacao.codigo }}</p>"}, format="json"
    )
    assert rascunho.status_code == 200
    # Um rascunho antigo, gravado direto, com marcador fora da lista não publica.
    ModeloContrato.objects.filter(pk=rascunho.json()["id"]).update(texto="<p>{{veiculo.dono}}</p>")
    publicar = api.post(f"{MODELOS}{rascunho.json()['id']}/publicar/")
    assert (publicar.status_code, publicar.json()["codigo"]) == (400, "marcador_invalido")
    # O valor do marcador entra escapado: o nome do cliente não vira HTML.
    assert (
        contratos.marcadores.substituir(
            "<p>{{cliente.nome}}</p>", {"cliente.nome": "<script>x</script>"}
        )
        == "<p>&lt;script&gt;x&lt;/script&gt;</p>"
    )


# --- API dos modelos ---


def test_modelos_api_lista_marcadores_prontos_e_previa(moto, django_capture_on_commit_callbacks):
    api = moto.moto.api("Mariana")
    lista = api.get(MODELOS).json()["resultados"]
    assert [(m["nome"], m["status"], m["versao_publicada"]) for m in lista] == [
        ("Locação semanal", "publicado", 1)
    ]
    marcadores = api.get("/api/contratos/marcadores/").json()["resultados"]
    assert {"chave": "cliente.nome", "rotulo": "Nome do cliente", "exemplo": "Lucas Ferreira"} in (
        marcadores
    )
    prontos = api.get("/api/contratos/modelos-prontos/").json()["resultados"]
    assert len(prontos) == 6 and prontos[1]["chave"] == "locacao_semanal_moto"

    exemplo = api.post(f"{MODELOS}{moto.modelo.pk}/previa/", {}, format="json")
    assert exemplo.json() == {"html": "<p>Lucas Ferreira</p>"}
    locacao = moto.confirmada(cliente="Juliana")
    real = api.post(
        f"{MODELOS}{moto.modelo.pk}/previa/", {"locacao_id": locacao["id"]}, format="json"
    )
    assert real.status_code == 200 and "Juliana" in real.json()["html"]
    assert not Contrato.objects.exists()  # a prévia não grava nada
    sem_locacao = api.post(f"{MODELOS}{moto.modelo.pk}/previa/", {"locacao_id": 999}, format="json")
    assert sem_locacao.status_code == 404

    # Só o administrador cuida dos modelos.
    assert moto.moto.api("Rodrigo").get(MODELOS).status_code == 403
    assert (
        moto.moto.api("Bruna").post(MODELOS, {"a_partir_de": "x"}, format="json").status_code == 403
    )


def test_imp_04_publicar_o_primeiro_modelo_conclui_o_passo_contrato(moto):
    api = moto.moto.api("Mariana")
    novo = api.post(MODELOS, {"a_partir_de": "locacao_mensal_carro"}, format="json").json()
    assert novo["nome"] == "Locação mensal de carro"
    api.post(f"{MODELOS}{novo['id']}/publicar/")
    uso = UsoEmpresa.objects.get(empresa=moto.moto.empresa)
    assert "contrato" in uso.passos_implantacao


# --- LOC-08 · Aditivo de renovação ---


def test_loc_08_aditivo_sem_assinatura_em_7_dias_avisa_os_gerentes(
    moto, relogio, django_capture_on_commit_callbacks
):
    locacao = moto.confirmada()
    with _tarefas(django_capture_on_commit_callbacks):
        aditivo = contrato_da_locacao.gerar_aditivo(Locacao.objects.get(pk=locacao["id"]))
    aditivo.refresh_from_db()
    assert (aditivo.tipo, aditivo.status, aditivo.titulo) == (
        "aditivo",
        "enviado",
        "Aditivo de renovação",
    )
    assert "LOC-2856" in aditivo.versao_texto_html and aditivo.modelo_id is None

    relogio.em("2026-10-13 10:00")
    assert contratos.avisar_aditivos_sem_assinatura() == 0
    relogio.em("2026-10-14 10:00")
    assert contratos.avisar_aditivos_sem_assinatura() == 1
    assert contratos.avisar_aditivos_sem_assinatura() == 0  # idempotente
    aviso = Notificacao.objects.get(tipo="aditivo_sem_assinatura")
    assert aviso.destinatario_id == moto.pessoas["Rodrigo"].pk
    assert aviso.titulo == "Aditivo da LOC-2856 sem assinatura há 7 dias"
    assert aviso.link == f"/locacoes/{locacao['id']}"


def test_loc_08_aditivo_assinado_nao_conta_como_contrato(moto, django_capture_on_commit_callbacks):
    """Só o contrato é condição da ativação; o aditivo assinado não mexe na locação."""
    locacao = moto.confirmada()
    with _tarefas(django_capture_on_commit_callbacks):
        contrato_da_locacao.gerar_aditivo(Locacao.objects.get(pk=locacao["id"]))
    assert _assinar(_token(), capturar=django_capture_on_commit_callbacks).status_code == 200
    assert Locacao.objects.get(pk=locacao["id"]).contrato_assinado_em is None
