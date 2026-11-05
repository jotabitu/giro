# ruff: noqa: F811 - as fixtures importadas voltam como parâmetro dos testes
"""T-411 · Copiar o link nas ações que enviam ao cliente (`docs/api/copiar-link.md`).

Contrato para assinar (`POST /api/locacoes/{id}/contrato/link/`), recibo da devolução
(`POST /api/devolucoes/{id}/recibo/link/` e a página pública `/recibo`), cobrança da parcela
(`acoes.copiar_cobranca`) e fatura da assinatura (sem links para o suporte). Com a revisão de
segurança `tarefas/handoffs/T-411-seguranca.md`: M-01, M-02, B-01, B-02 e B-03.

Cenários: o da T-090 (LOC-2856 do Lucas, 07 out 2026 10:00) para o contrato; o da T-016 para a
devolução; a carteira da T-017 para a cobrança; a empresa criada pelo serviço para a fatura.
"""

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
from django.core import mail
from django.db import connection
from django_tenants.utils import schema_context, tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.clientes.models import Cliente
from apps.clientes.titular import _anular_links
from apps.contas.models import Usuario
from apps.contratos import services as contratos
from apps.contratos.models import CanalDoToken, Contrato
from apps.contratos.tasks import contratos_preparar_e_enviar
from apps.financeiro import services as financeiro
from apps.financeiro.models import CobrancaExterna, ContaReceber
from apps.locacoes import selectors as locacoes_selectors
from apps.locacoes.models import Locacao
from apps.plataforma import selectors as plataforma_selectors
from apps.plataforma import services as plataforma
from apps.plataforma.models import (
    Empresa,
    FaturaAssinatura,
    FormaAssinatura,
    FormaPagamentoAssinatura,
)
from apps.plataforma.services import abrir_acesso_suporte
from apps.vistorias.models import Devolucao
from comum import relogio as relogio_do_giro
from comum.erros import Conflito
from comum.estados import transicionar
from comum.limites import LinkContratoPorUsuario, LinkReciboPorDevolucao
from integracoes.pagamentos import falso as pagamentos
from integracoes.pagamentos.base import CartaoGuardado
from integracoes.whatsapp.falso import caixa_de_saida

from .conftest import cliente as cliente_http
from .test_t012_filiais import HOST
from .test_t015_locacoes import LISTA
from .test_t016_vistorias import (  # noqa: F401 - fixtures
    DEVOLUCOES,
    _abrir_devolucao,
    _chegada,
    _encerrar,
    _forma,
    _lucas_ativo,
    cenario,
    lucas,
)
from .test_t017_financeiro import CONTAS, _carlos, com_carteira  # noqa: F401 - fixture
from .test_t090_contratos import (  # noqa: F401 - fixture
    ASSINAR,
    CONSULTAR,
    HOST_B,
    _assinar,
    _contrato,
    _gerar,
    _publica,
    _tarefas,
    _token,
    moto,
)

RECIBO_PUBLICO = "/api/publico/recibos/consultar/"
IP_DO_BALCAO = "200.150.10.77"


def _suporte(empresa: Any, permissao: str = "ver_editar") -> Any:
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
        Empresa.objects.get(pk=empresa.pk),
        diego,
        motivo="Chamado #1042",
        duracao_minutos=30,
        permissao=permissao,
    )
    connection.set_tenant(empresa)
    return cliente_http(HOST, str(token))


def _do_link(link: str, pagina: str) -> str:
    prefixo = f"https://empresa-a.localhost/{pagina}#"
    assert link.startswith(prefixo), link
    return link.removeprefix(prefixo)


# --- Contrato para assinar (S-15, LOC-15) ---


def _copiar_contrato(moto: Any, locacao_id: int, quem: str = "Bruna", ip: str = IP_DO_BALCAO):
    api = moto.moto.api(quem, HTTP_X_FORWARDED_FOR=ip)
    return api.post(f"{LISTA}{locacao_id}/contrato/link/")


def _enviado(moto: Any, capturar: Any) -> dict[str, Any]:
    locacao = moto.confirmada()
    assert _gerar(moto, capturar, locacao["id"]).status_code == 202
    return dict(locacao)


def test_s_15_copiar_link_contrato_invalida_o_anterior(moto, django_capture_on_commit_callbacks):
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    do_whatsapp = _token()
    contrato = _contrato(locacao["id"])
    enviado_em, mensagens = contrato.enviado_em, len(caixa_de_saida)

    resposta = _copiar_contrato(moto, locacao["id"])
    assert resposta.status_code == 200, resposta.json()
    assert resposta["Cache-Control"] == "no-store"
    corpo = resposta.json()
    copiado = _do_link(corpo["link"], "assinar")
    assert corpo["expira_em"] == "2026-10-14T13:00:00Z"  # 7 dias (S-15)
    assert corpo["aviso"] == "O link anterior deixa de valer."
    assert corpo["contrato"]["status"] == "enviado"
    assert corpo["contrato"]["pdf_disponivel"] is True
    # Não envia nada e não mexe no status nem no envio.
    assert len(caixa_de_saida) == mensagens
    contrato.refresh_from_db()
    assert (contrato.status, contrato.enviado_em) == ("enviado", enviado_em)
    assert contrato.token_assinatura_hash == contratos.hash_do_token(copiado)

    assert _publica().post(CONSULTAR, {"token": do_whatsapp}, format="json").status_code == 404
    assert _publica().post(CONSULTAR, {"token": copiado}, format="json").status_code == 200
    assert _assinar(copiado, capturar=django_capture_on_commit_callbacks).status_code == 200
    # O link não volta em nenhum GET.
    detalhe = moto.moto.api("Bruna").get(f"{LISTA}{locacao['id']}/").content.decode()
    assert copiado not in detalhe


def test_s_15_copiar_link_contrato_estados(moto, django_capture_on_commit_callbacks):
    sem = moto.confirmada()
    resposta = _copiar_contrato(moto, sem["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "sem_contrato")
    assert resposta.json()["mensagem"] == "Esta locação ainda não tem contrato. Gere o contrato."

    # Em preparo: o contrato existe, mas a tarefa do PDF ainda não rodou.
    with django_capture_on_commit_callbacks(execute=False):
        moto.moto.api("Bruna").post(f"{LISTA}{sem['id']}/contrato/")
    resposta = _copiar_contrato(moto, sem["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "contrato_em_preparo")
    assert moto.detalhe(sem["id"])["acoes"]["copiar_link_contrato"] is False

    # Com o PDF pronto e ainda `gerado` (nada enviado), copia e continua `gerado`.
    em_preparo = _contrato(sem["id"])
    marca, _ = contratos.selectors.marca_e_host()
    contratos.gravar_pdf(em_preparo, marca)
    assert moto.detalhe(sem["id"])["acoes"]["copiar_link_contrato"] is True
    assert _copiar_contrato(moto, sem["id"]).status_code == 200
    assert _contrato(sem["id"]).status == "gerado"

    # Assinado.
    copiado = _do_link(_copiar_contrato(moto, sem["id"]).json()["link"], "assinar")
    assert _assinar(copiado, capturar=django_capture_on_commit_callbacks).status_code == 200
    resposta = _copiar_contrato(moto, sem["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "contrato_assinado")
    assert resposta.json()["mensagem"] == (
        "Este contrato já foi assinado. Para mandar o PDF assinado, use Reenviar."
    )
    assert moto.detalhe(sem["id"])["acoes"]["copiar_link_contrato"] is False

    # Cancelado (a rota não chega a ele, porque o vigente some; o serviço recusa).
    outra = moto.confirmada(veiculo=moto.veiculo("Urbana 110–125"))
    assert _gerar(moto, django_capture_on_commit_callbacks, outra["id"]).status_code == 202
    cancelado = contratos.cancelar(_contrato(outra["id"]), "Teste")
    with pytest.raises(Conflito) as erro:
        contratos.gerar_link(cancelado, moto.moto.pessoas["Bruna"])
    assert erro.value.codigo == "contrato_cancelado"


def test_s_15_copiar_link_contrato_titular_anonimizado(moto, django_capture_on_commit_callbacks):
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    copiado = _do_link(_copiar_contrato(moto, locacao["id"]).json()["link"], "assinar")
    contrato = _contrato(locacao["id"])
    cliente = Cliente.objects.get(pk=contrato.cliente_id)
    Cliente.objects.filter(pk=cliente.pk).update(anonimizado_em=relogio_do_giro.agora())
    _anular_links(cliente)
    # O link copiado antes deixa de abrir (404), e copiar de novo responde 409.
    assert _publica().post(CONSULTAR, {"token": copiado}, format="json").status_code == 404
    resposta = _copiar_contrato(moto, locacao["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "titular_anonimizado")
    assert resposta.json()["mensagem"] == "Os dados deste cliente foram anonimizados."
    assert moto.detalhe(locacao["id"])["acoes"]["copiar_link_contrato"] is False


def test_s_15_copiar_link_contrato_perfis_e_suporte(moto, django_capture_on_commit_callbacks):
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    for quem in ("João", "Lúcia"):
        resposta = _copiar_contrato(moto, locacao["id"], quem)
        assert (resposta.status_code, resposta.json()["codigo"]) == (403, "permissao")
    for quem in ("Mariana", "Rodrigo", "Bruna"):
        assert _copiar_contrato(moto, locacao["id"], quem).status_code == 200
    assert moto.detalhe(locacao["id"])["acoes"]["copiar_link_contrato"] is True

    hash_antes = _contrato(locacao["id"]).token_assinatura_hash
    for permissao in ("ver", "ver_editar"):
        suporte = _suporte(moto.moto.empresa, permissao)
        resposta = suporte.post(f"{LISTA}{locacao['id']}/contrato/link/")
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "PLT-07"
        assert resposta.json()["mensagem"] == "No modo suporte você não gera link para o cliente."
    assert _contrato(locacao["id"]).token_assinatura_hash == hash_antes
    suporte = SimpleNamespace(perfil="administrador", e_suporte=True)
    acoes = locacoes_selectors.acoes(
        Locacao.objects.get(pk=locacao["id"]), suporte, _contrato(locacao["id"])
    )
    assert acoes["copiar_link_contrato"] is False


def test_s_15_copiar_link_contrato_limite_por_hora(moto, django_capture_on_commit_callbacks):
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    for _ in range(5):
        assert _copiar_contrato(moto, locacao["id"]).status_code == 200
    hash_antes = _contrato(locacao["id"]).token_assinatura_hash
    estourou = _copiar_contrato(moto, locacao["id"], "Rodrigo")
    assert (estourou.status_code, estourou.json()["codigo"]) == (429, "muitas_requisicoes")
    # O 429 não gera link nem invalida o anterior.
    assert _contrato(locacao["id"]).token_assinatura_hash == hash_antes
    # Os 20 por pessoa contam pela pessoa, não pelo contrato.
    requisicao: Any = SimpleNamespace(user=SimpleNamespace(pk=7, is_authenticated=True))
    chave = LinkContratoPorUsuario().get_cache_key(requisicao, SimpleNamespace(kwargs={"pk": 1}))
    assert chave == "throttle_link_contrato_usuario_7"


def test_s_15_copiar_link_contrato_evento_sem_token(moto, django_capture_on_commit_callbacks):
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    resposta = _copiar_contrato(moto, locacao["id"])
    copiado = _do_link(resposta.json()["link"], "assinar")
    evento = EventoAuditoria.objects.get(acao="contrato.copiar_link")
    assert evento.categoria == "seguranca"
    assert evento.ator_nome == "Bruna"
    assert evento.depois == {"token_assinatura_expira_em": "2026-10-14T10:00:00-03:00"}
    for registro in EventoAuditoria.objects.all():
        texto = str(registro.antes) + str(registro.depois)
        assert copiado not in texto
        assert contratos.hash_do_token(copiado) not in texto
        assert IP_DO_BALCAO not in texto  # `token_assinatura_gerado_ip` fica fora


def test_loc_15_assinatura_por_link_copiado_registra_canal(
    moto, django_capture_on_commit_callbacks
):
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    assert _contrato(locacao["id"]).token_assinatura_canal == "whatsapp_email"
    copiado = _do_link(_copiar_contrato(moto, locacao["id"]).json()["link"], "assinar")
    contrato = _contrato(locacao["id"])
    assert contrato.token_assinatura_canal == "copiado"
    assert contrato.token_assinatura_gerado_por_id == moto.moto.pessoas["Bruna"].pk
    assert contrato.token_assinatura_gerado_ip == IP_DO_BALCAO

    # O cliente assina no celular, na rede da loja: o mesmo IP de quem copiou. Nada bloqueia.
    assert _assinar(copiado, capturar=django_capture_on_commit_callbacks).status_code == 200
    contrato.refresh_from_db()
    assert contrato.status == "assinado"
    assert contrato.token_assinatura_canal == "copiado"  # fica para a prova
    evento = EventoAuditoria.objects.get(acao="contratos.contrato_assinado")
    assert evento.depois["token_assinatura_canal"] == "copiado"
    assert evento.depois["mesmo_ip_de_quem_copiou"] is True
    assert contratos.texto_do_canal(contrato, "America/Fortaleza") == (
        "Link entregue por cópia, gerado por Bruna em 07/10/2026, 10:00"
    )
    assert contrato.pdf_assinado.open().read().startswith(b"%PDF-")


def test_loc_15_assinatura_pelo_whatsapp_registra_canal(moto, django_capture_on_commit_callbacks):
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    assert _assinar(_token(), capturar=django_capture_on_commit_callbacks).status_code == 200
    contrato = _contrato(locacao["id"])
    evento = EventoAuditoria.objects.get(acao="contratos.contrato_assinado")
    assert evento.depois == {"token_assinatura_canal": "whatsapp_email"}
    assert contratos.texto_do_canal(contrato, "America/Fortaleza") == (
        "Link enviado por WhatsApp ou e-mail ao cliente"
    )


def test_s_15_reenvio_em_fila_nao_mata_link_copiado(
    moto, relogio, django_capture_on_commit_callbacks
):
    """B-02: o reenvio entra na fila, alguém copia o link antes de a tarefa rodar, e a tarefa
    (ou a repetição dela) termina sem trocar o token copiado e sem enviar."""
    locacao = _enviado(moto, django_capture_on_commit_callbacks)
    mensagens = len(caixa_de_saida)
    with django_capture_on_commit_callbacks(execute=False) as na_fila:
        resposta = moto.moto.api("Bruna").post(f"{LISTA}{locacao['id']}/contrato/reenviar/")
    assert resposta.status_code == 202
    relogio.em("2026-10-07 10:05")
    copiado = _do_link(_copiar_contrato(moto, locacao["id"]).json()["link"], "assinar")
    try:
        for tarefa in na_fila:
            tarefa()
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert len(caixa_de_saida) == mensagens
    assert _contrato(locacao["id"]).token_assinatura_hash == contratos.hash_do_token(copiado)
    assert _publica().post(CONSULTAR, {"token": copiado}, format="json").status_code == 200

    # A tarefa de preparo repetida com um `gerado` de PDF pronto também não troca o token.
    outra = moto.confirmada(veiculo=moto.veiculo("Urbana 110–125"))
    with django_capture_on_commit_callbacks(execute=False):
        moto.moto.api("Bruna").post(f"{LISTA}{outra['id']}/contrato/")
    contrato = _contrato(outra["id"])
    contratos.gravar_pdf(contrato, contratos.selectors.marca_e_host()[0])
    na_fila_em = relogio_do_giro.agora().isoformat()
    relogio.em("2026-10-07 10:10")
    copiado = _do_link(_copiar_contrato(moto, outra["id"]).json()["link"], "assinar")
    try:
        contratos_preparar_e_enviar("empresa_a", contrato.pk, enfileirado_em=na_fila_em)
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    contrato.refresh_from_db()
    assert contrato.status == "gerado"
    assert contrato.token_assinatura_hash == contratos.hash_do_token(copiado)


# --- Recibo da devolução (DEV-02, S-15, B-03) ---


def _concluida(cenario: Any, capturar: Any) -> dict[str, Any]:
    criada = _lucas_ativo(cenario)
    devolucao = _abrir_devolucao(cenario, criada["id"])
    _chegada(cenario, devolucao, 3200, "tres_quartos")
    assert _forma(cenario, devolucao["id"]).status_code == 200
    try:
        with capturar(execute=True):
            assert _encerrar(cenario, devolucao["id"]).status_code == 200
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    return devolucao


def _copiar_recibo(cenario: Any, devolucao_id: int, quem: str = "Bruna") -> Any:
    return cenario.moto.api(quem).post(f"{DEVOLUCOES}{devolucao_id}/recibo/link/")


def _abrir_recibo(token: str, host: str = HOST, ip: str = IP_DO_BALCAO) -> Any:
    return _publica(host, ip).post(RECIBO_PUBLICO, {"token": token}, format="json")


def test_dev_02_copiar_link_recibo_abre_o_pdf(cenario, lucas, django_capture_on_commit_callbacks):
    devolucao = _concluida(cenario, django_capture_on_commit_callbacks)
    mensagens = len(caixa_de_saida)
    resposta = _copiar_recibo(cenario, devolucao["id"])
    assert resposta.status_code == 200, resposta.json()
    assert resposta["Cache-Control"] == "no-store"
    corpo = resposta.json()
    token = _do_link(corpo["link"], "recibo")
    assert corpo["aviso"] == "O link anterior deixa de valer."
    assert corpo["devolucao"]["id"] == devolucao["id"]
    assert corpo["devolucao"]["status"] == "concluida"
    assert len(caixa_de_saida) == mensagens  # não envia nada

    aberto = _abrir_recibo(token)
    assert aberto.status_code == 200, aberto.json()
    assert aberto["Cache-Control"] == "no-store"
    assert aberto["X-Robots-Tag"] == "noindex"
    recibo = aberto.json()["recibo"]
    assert recibo["codigo"] == "LOC-2856"
    assert recibo["cliente_primeiro_nome"] == "Lucas"
    assert recibo["pdf_url"].startswith("https://")
    assert aberto.json()["empresa"]["nome_exibicao"]
    # Não é de uso único.
    assert _abrir_recibo(token).status_code == 200
    salvo = Devolucao.objects.get(pk=devolucao["id"])
    assert salvo.token_recibo_hash and token not in salvo.token_recibo_hash


def test_dev_02_copiar_link_recibo_invalida_o_anterior(
    cenario,
    lucas,
    django_capture_on_commit_callbacks,
):
    devolucao = _concluida(cenario, django_capture_on_commit_callbacks)
    primeiro = _do_link(_copiar_recibo(cenario, devolucao["id"]).json()["link"], "recibo")
    segundo = _do_link(_copiar_recibo(cenario, devolucao["id"]).json()["link"], "recibo")
    assert _abrir_recibo(primeiro).status_code == 404
    assert _abrir_recibo(segundo).status_code == 200


def test_dev_02_copiar_link_recibo_rascunho_e_perfis(
    cenario,
    lucas,
    django_capture_on_commit_callbacks,
):
    criada = _lucas_ativo(cenario)
    rascunho = _abrir_devolucao(cenario, criada["id"])
    resposta = _copiar_recibo(cenario, rascunho["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "devolucao_em_rascunho")
    assert resposta.json()["mensagem"] == "O recibo sai quando a devolução é encerrada."
    ver = cenario.moto.api("Bruna").get(f"{DEVOLUCOES}{rascunho['id']}/").json()
    assert ver["acoes"] == {"copiar_link_recibo": False}

    _chegada(cenario, rascunho, 3200, "tres_quartos")
    assert _forma(cenario, rascunho["id"]).status_code == 200
    try:
        with django_capture_on_commit_callbacks(execute=True):
            assert _encerrar(cenario, rascunho["id"]).status_code == 200
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    ver = cenario.moto.api("Bruna").get(f"{DEVOLUCOES}{rascunho['id']}/").json()
    assert ver["acoes"] == {"copiar_link_recibo": True}

    for quem in ("João", "Lúcia"):
        assert _copiar_recibo(cenario, rascunho["id"], quem).status_code == 403
    for quem in ("Mariana", "Rodrigo"):
        assert _copiar_recibo(cenario, rascunho["id"], quem).status_code == 200
    hash_antes = Devolucao.objects.get(pk=rascunho["id"]).token_recibo_hash
    suporte = _suporte(cenario.moto.empresa)
    resposta = suporte.post(f"{DEVOLUCOES}{rascunho['id']}/recibo/link/")
    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "PLT-07")
    assert resposta.json()["mensagem"] == "No modo suporte você não gera link para o cliente."
    assert suporte.get(f"{DEVOLUCOES}{rascunho['id']}/").json()["acoes"] == {
        "copiar_link_recibo": False
    }
    assert Devolucao.objects.get(pk=rascunho["id"]).token_recibo_hash == hash_antes


def test_dev_02_copiar_link_recibo_limite_por_hora(
    cenario,
    lucas,
    django_capture_on_commit_callbacks,
):
    devolucao = _concluida(cenario, django_capture_on_commit_callbacks)
    for _ in range(5):
        assert _copiar_recibo(cenario, devolucao["id"]).status_code == 200
    hash_antes = Devolucao.objects.get(pk=devolucao["id"]).token_recibo_hash
    estourou = _copiar_recibo(cenario, devolucao["id"], "Rodrigo")
    assert (estourou.status_code, estourou.json()["codigo"]) == (429, "muitas_requisicoes")
    assert Devolucao.objects.get(pk=devolucao["id"]).token_recibo_hash == hash_antes
    requisicao: Any = SimpleNamespace()
    chave = LinkReciboPorDevolucao().get_cache_key(requisicao, SimpleNamespace(kwargs={"pk": 9}))
    assert chave == "throttle_link_recibo_devolucao_9"


def test_dev_02_copiar_link_recibo_evento_sem_token(
    cenario,
    lucas,
    django_capture_on_commit_callbacks,
):
    devolucao = _concluida(cenario, django_capture_on_commit_callbacks)
    token = _do_link(_copiar_recibo(cenario, devolucao["id"]).json()["link"], "recibo")
    evento = EventoAuditoria.objects.get(acao="devolucao.copiar_link_recibo")
    assert evento.categoria == "seguranca"
    assert set(evento.depois) == {"token_recibo_expira_em"}
    for registro in EventoAuditoria.objects.all():
        texto = str(registro.antes) + str(registro.depois)
        assert token not in texto
        assert "token_recibo_hash" not in registro.depois or registro.depois[
            "token_recibo_hash"
        ] == {"alterado": True}


def test_dev_02_recibo_publico_vencido_e_desconhecido(
    cenario,
    lucas,
    relogio,
    django_capture_on_commit_callbacks,
):
    devolucao = _concluida(cenario, django_capture_on_commit_callbacks)
    token = _do_link(_copiar_recibo(cenario, devolucao["id"]).json()["link"], "recibo")
    assert _abrir_recibo("nao-existe").status_code == 404

    salvo = Devolucao.objects.get(pk=devolucao["id"])
    assert salvo.token_recibo_expira_em is not None
    relogio.em("2026-10-14 13:01")  # depois dos 7 dias da cópia (S-15)
    assert relogio_do_giro.agora() > salvo.token_recibo_expira_em
    vencido = _abrir_recibo(token)
    assert (vencido.status_code, vencido.json()["codigo"]) == (410, "link_expirado")
    assert vencido.json()["mensagem"] == "Este link venceu. Peça um novo à locadora."

    # Anonimizado: o link anulado dá 404, e copiar de novo, 409.
    cenario.moto._tokens.clear()
    token = _do_link(_copiar_recibo(cenario, devolucao["id"]).json()["link"], "recibo")
    locacao = Locacao.objects.get(pk=devolucao["locacao"]["id"])
    cliente = Cliente.objects.get(pk=locacao.cliente_id)
    Cliente.objects.filter(pk=cliente.pk).update(anonimizado_em=relogio_do_giro.agora())
    _anular_links(cliente)
    assert _abrir_recibo(token).status_code == 404
    resposta = _copiar_recibo(cenario, devolucao["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "titular_anonimizado")


def test_dev_02_recibo_publico_nao_cruza_empresas(
    cenario,
    lucas,
    django_capture_on_commit_callbacks,
):
    devolucao = _concluida(cenario, django_capture_on_commit_callbacks)
    token = _do_link(_copiar_recibo(cenario, devolucao["id"]).json()["link"], "recibo")
    assert _abrir_recibo(token, HOST_B).status_code == 404
    assert _abrir_recibo(token).status_code == 200


def test_dev_02_recibo_publico_limites_proprios(cenario):
    """Escopos próprios: esgotar o recibo não gasta o limite da assinatura (B-03)."""
    for i in range(10):
        assert _abrir_recibo(f"t{i}", ip="200.150.10.99").status_code == 404
    estourou = _abrir_recibo("t", ip="200.150.10.99")
    assert (estourou.status_code, estourou.json()["codigo"]) == (429, "muitas_requisicoes")
    assinatura = _publica(ip="200.150.10.99").post(CONSULTAR, {"token": "t"}, format="json")
    assert assinatura.status_code == 404


def test_dev_02_recibo_aberto_um_por_dia(
    cenario,
    lucas,
    relogio,
    django_capture_on_commit_callbacks,
):
    devolucao = _concluida(cenario, django_capture_on_commit_callbacks)
    token = _do_link(_copiar_recibo(cenario, devolucao["id"]).json()["link"], "recibo")
    for _ in range(3):
        assert _abrir_recibo(token).status_code == 200
    abertos = EventoAuditoria.objects.filter(acao="devolucao.recibo_aberto")
    assert abertos.count() == 1
    evento = abertos.get()
    assert (evento.ator_tipo, evento.ip) == ("sistema", "200.150.10.0")  # IP /24
    assert evento.aparelho == "Chrome 129 no Android"
    assert evento.objeto_id == devolucao["id"]

    relogio.em("2026-10-08 09:00")
    assert _abrir_recibo(token).status_code == 200
    assert _abrir_recibo(token).status_code == 200
    assert abertos.count() == 2


# --- Cobrança da parcela (AUT-03, AUD-09) ---


def _cobranca(conta: ContaReceber, tipo: str, vence_em: date, **campos: Any) -> CobrancaExterna:
    return CobrancaExterna.objects.create(
        conta_receber=conta,
        tipo=tipo,
        externo_id=f"pay_t411_{conta.pk}_{tipo}_{vence_em:%d}",
        valor_centavos=30609,
        vence_em=vence_em,
        gerada_no_dia=vence_em,
        **campos,
    )


def _conta(cenario: Any, conta: ContaReceber, api: Any = None) -> dict[str, Any]:
    resposta = (api or cenario.moto.api("Lúcia")).get(f"{CONTAS}{conta.pk}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def test_aut_03_copiar_cobranca_so_com_a_cobranca_do_dia(cenario, com_carteira):
    carlos = _carlos(com_carteira)
    assert _conta(cenario, carlos)["acoes"]["copiar_cobranca"] is False  # sem cobrança

    ontem = _cobranca(carlos, "pix", date(2026, 10, 6), pix_copia_e_cola="000201ontem")
    assert _conta(cenario, carlos)["acoes"]["copiar_cobranca"] is False  # a de ontem
    transicionar(ontem, "vencida")

    _cobranca(carlos, "pix", date(2026, 10, 7), pix_copia_e_cola="000201hoje")
    corpo = _conta(cenario, carlos)
    assert corpo["acoes"]["copiar_cobranca"] is True
    assert corpo["cobranca_aberta"]["pix_copia_e_cola"] == "000201hoje"
    # Não depende do perfil: quem vê a conta copia o que já está na tela.
    assert _conta(cenario, carlos, cenario.moto.api("Bruna"))["acoes"]["copiar_cobranca"] is True

    financeiro.marcar_paga(ContaReceber.objects.get(pk=carlos.pk), forma="pix")
    assert _conta(cenario, carlos)["acoes"]["copiar_cobranca"] is False


def test_aud_09_suporte_nao_recebe_boleto_url(cenario, com_carteira):
    carlos = _carlos(com_carteira)
    _cobranca(
        carlos,
        "boleto",
        date(2026, 10, 10),
        linha_digitavel="23793381286000000000000000000000000000000000000",
        url="https://parceiro.exemplo/boleto/pay_t411",
    )
    da_lucia = _conta(cenario, carlos)["cobranca_aberta"]
    assert da_lucia["boleto_url"] == "https://parceiro.exemplo/boleto/pay_t411"

    for permissao in ("ver_editar",):
        suporte = _suporte(cenario.moto.empresa, permissao)
        corpo = _conta(cenario, carlos, suporte)
        assert corpo["cobranca_aberta"]["boleto_url"] is None
        assert corpo["cobranca_aberta"]["linha_digitavel"].startswith("2379")
        assert corpo["acoes"]["copiar_cobranca"] is False
        lista = suporte.get(CONTAS, {"busca": "Carlos"}).content.decode()
        assert "parceiro.exemplo/boleto" not in lista


# --- Fatura da assinatura (AUD-09, PLT-13) ---


@pytest.fixture
def empresa_criada(criar_empresa):
    pagamentos.limpar()
    yield criar_empresa()
    pagamentos.limpar()


def test_aud_09_suporte_nao_recebe_link_da_fatura(empresa_criada):
    fatura = FaturaAssinatura.objects.get(empresa=empresa_criada, codigo="FAT-0001")
    fatura.cobranca_externa_id = "pay_t411_fatura"
    fatura.cobranca_tipo = "boleto"
    fatura.cobranca_boleto_url = "https://parceiro.exemplo/boleto/fatura"
    fatura.cobranca_url_pagina = "https://parceiro.exemplo/pagar/fatura"
    fatura.cobranca_linha_digitavel = "23793381286000000000000000000000000000000000001"
    fatura.save()
    administradora = SimpleNamespace(perfil="administrador")
    suporte = SimpleNamespace(perfil="administrador", e_suporte=True)

    contexto = plataforma_selectors.contexto_das_faturas(empresa_criada, administradora)
    cobranca = plataforma_selectors.detalhe_da_fatura(fatura, contexto)["cobranca"]
    assert cobranca["url_boleto"] == "https://parceiro.exemplo/boleto/fatura"
    assert cobranca["url_pagina"] == "https://parceiro.exemplo/pagar/fatura"

    contexto = plataforma_selectors.contexto_das_faturas(empresa_criada, suporte)
    cobranca = plataforma_selectors.detalhe_da_fatura(fatura, contexto)["cobranca"]
    assert (cobranca["url_boleto"], cobranca["url_pagina"]) == (None, None)
    assert cobranca["linha_digitavel"].startswith("2379")


def test_plt_13_cartao_novo_avisa_o_administrador(
    empresa_criada, django_capture_on_commit_callbacks
):
    forma = FormaPagamentoAssinatura.objects.get(empresa=empresa_criada)
    forma.forma = FormaAssinatura.CARTAO
    forma.save(update_fields=["forma"])
    with tenant_context(empresa_criada):
        Usuario.objects.create_user(
            "rodrigo@motorapida.com.br", "senha-forte-123", nome="Rodrigo", perfil="administrador"
        )
        administradores = list(
            Usuario.objects.filter(perfil="administrador", status="ativo")
            .order_by("pk")
            .values_list("email", flat=True)
        )
    assert administradores

    # O primeiro cartão é a própria escolha da forma: não avisa.
    with django_capture_on_commit_callbacks(execute=True):
        plataforma._guardar_cartao(empresa_criada, CartaoGuardado("tok_um", "visa", "4242"))
    assert mail.outbox == []
    # O mesmo cartão de novo também não.
    with django_capture_on_commit_callbacks(execute=True):
        plataforma._guardar_cartao(empresa_criada, CartaoGuardado("tok_um", "visa", "4242"))
    assert mail.outbox == []

    fatura = FaturaAssinatura.objects.get(empresa=empresa_criada, codigo="FAT-0001")
    with django_capture_on_commit_callbacks(execute=True):
        plataforma._guardar_cartao(
            empresa_criada,
            CartaoGuardado("tok_dois", "mastercard", "5454", titular="ANA SOUZA"),
            fatura,
        )
    assert [m.to for m in mail.outbox] == [[e] for e in administradores]
    assert mail.outbox[0].subject == "O cartão da assinatura mudou"
    endereco = plataforma.endereco_da_assinatura(empresa_criada)
    assert mail.outbox[0].body == (
        "O cartão das próximas faturas da empresa Moto Rápida mudou para Mastercard final 5454, "
        "no nome de ANA SOUZA, no pagamento da FAT-0001 em 07 out 2026. Se ninguém da empresa "
        f"fez essa troca, troque a forma de pagamento em Assinatura: {endereco}."
    )
    assert endereco.endswith("/admin/assinatura")
    # Sem o titular devolvido pelo parceiro, a frase sai sem "no nome de".
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        plataforma._guardar_cartao(empresa_criada, CartaoGuardado("tok_tres", "elo", "1111"))
    assert mail.outbox[0].body.startswith(
        "O cartão das próximas faturas da empresa Moto Rápida mudou para Elo final 1111. Se ninguém"
    )
    eventos = EventoAuditoria.objects.filter(acao="assinatura.cartao_guardado").order_by("id")
    evento = list(eventos)[-2]
    assert evento.depois["cartao_bandeira"] == "mastercard"
    assert evento.depois["cartao_final"] == "5454"
    assert evento.depois["cartao_titular"] == "ANA SOUZA"
    assert all("tok_" not in str(e.antes) + str(e.depois) for e in eventos)


def test_contrato_do_modelo_guarda_o_canal():
    assert set(CanalDoToken.values) == {"whatsapp_email", "copiado"}
    assert Contrato._meta.get_field("token_assinatura_canal").max_length == 15
