"""T-250 · Decisões de 15 out (docs/qa/criterios/T-248.md): filtro de filial na lista de
Clientes (CLI-10), administrador decide o próprio pedido (APR-09) e copiar link do convite
(USR-01)."""

import logging
from typing import Any

import pytest
from django.core import mail
from django.db import IntegrityError, connection, transaction

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria import textos
from apps.auditoria.models import EventoAuditoria
from apps.contas import services
from apps.contas.models import Usuario
from apps.filiais.models import Filial
from apps.financeiro.models import Despesa
from apps.locacoes.models import Locacao
from comum import aprovacoes
from integracoes.whatsapp.falso import caixa_de_saida

from .frota import criar_veiculo
from .test_t011_contas import (
    ACEITAR,
    CONSULTAR,
    SENHA,
    USUARIOS,
    _api_de,
    _convidar,
    _get,
    _post,
    _token_do_convite,
    _uso_de_usuarios,
    adm,  # noqa: F401 - fixture
    moto,  # noqa: F401 - fixture
)
from .test_t013_veiculos import _caucaia
from .test_t014_clientes import _suporte
from .test_t015_locacoes import LISTA as LOCACOES
from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t017_financeiro import _despesa
from .test_t081_aprovacoes import decisoes  # noqa: F401 - fixture

CLIENTES = "/api/clientes/"


# --- Filtro de filial na lista de Clientes (CLI-10) ---


def _lista(cenario: Any, quem: str = "Mariana", **params: Any) -> Any:  # noqa: F811
    return cenario.moto.api(quem, **params.pop("cabecalhos", {})).get(CLIENTES, params)


def _nomes(resposta: Any) -> list[str]:
    assert resposta.status_code == 200, resposta.json()
    return sorted(c["nome"] for c in resposta.json()["resultados"])


def _locacao_na(cenario: Any, filial: Any, cliente: str, numero: int) -> Locacao:  # noqa: F811
    """Rascunho de locação do cliente na filial (o estado não importa para o filtro)."""
    veiculo = criar_veiculo(numero, cenario.sak.categoria, filial)
    api = cenario.moto.api("Mariana", HTTP_X_FILIAL=str(filial.pk))
    resposta = api.post(LOCACOES, cenario.corpo(cliente, veiculo), format="json")
    assert resposta.status_code == 201, resposta.json()
    locacao = Locacao.objects.get(pk=resposta.json()["id"])
    assert locacao.filial_id == filial.pk
    return locacao


def test_cli_10_lista_filtra_por_filial(cenario):  # noqa: F811
    centro = cenario.frota.centro
    todos = _nomes(_lista(cenario))
    # CA-248-02: sem locação, só em "Todas as filiais".
    assert _nomes(_lista(cenario, filial=centro.pk)) == []
    _locacao_na(cenario, centro, "Carlos", 901)
    _locacao_na(cenario, centro, "Lucas", 902)
    na_centro = _nomes(_lista(cenario, filial=centro.pk))
    assert na_centro == sorted([cenario.cliente("Carlos").nome, cenario.cliente("Lucas").nome])
    assert _nomes(_lista(cenario)) == todos

    # CA-248-03: Juliana só na Caucaia; Carlos nas duas, uma vez em cada.
    caucaia = _caucaia(cenario.moto)
    _locacao_na(cenario, caucaia, "Juliana", 903)
    _locacao_na(cenario, caucaia, "Carlos", 904)
    juliana, carlos = cenario.cliente("Juliana").nome, cenario.cliente("Carlos").nome
    assert _nomes(_lista(cenario, filial=caucaia.pk)) == sorted([juliana, carlos])
    assert juliana not in _nomes(_lista(cenario, filial=centro.pk))

    # Contagens e indicadores dentro do filtro; sem o filtro, a empresa toda (CA-248-01).
    corpo = _lista(cenario, filial=caucaia.pk).json()
    assert corpo["contagens"]["todos"] == 2
    assert _lista(cenario).json()["contagens"]["todos"] == len(todos)

    # CA-248-05: combina com a busca.
    assert _nomes(_lista(cenario, filial=caucaia.pk, busca=juliana.split()[0])) == [juliana]


def test_cli_10_lista_ignora_o_seletor(cenario):  # noqa: F811
    """CA-248-06: o X-Filial do topo não filtra a lista."""
    caucaia = _caucaia(cenario.moto)
    _locacao_na(cenario, caucaia, "Juliana", 905)
    todos = _nomes(_lista(cenario))
    assert _nomes(_lista(cenario, cabecalhos={"HTTP_X_FILIAL": str(caucaia.pk)})) == todos


def test_cli_10_filial_sem_acesso(cenario):  # noqa: F811
    """CA-248-07: filial fora do escopo, desativada ou inexistente dão o mesmo 403 USR-07."""
    caucaia = _caucaia(cenario.moto)
    _locacao_na(cenario, caucaia, "Juliana", 906)
    juliana = cenario.cliente("Juliana").nome
    # Rodrigo só na Centro: "Todas" mostra a Juliana; a Caucaia, 403.
    assert juliana in _nomes(_lista(cenario, "Rodrigo"))
    negada = _lista(cenario, "Rodrigo", filial=caucaia.pk)
    assert negada.status_code == 403
    assert negada.json()["codigo"] == "USR-07"
    assert negada.json()["mensagem"] == "Você não tem acesso a esta filial"
    inexistente = _lista(cenario, "Rodrigo", filial=99999)
    assert (inexistente.status_code, inexistente.json()) == (403, negada.json())
    # Mariana e Lúcia veem a Caucaia sem estar ligadas a ela.
    for quem in ("Mariana", "Lúcia"):
        assert _nomes(_lista(cenario, quem, filial=caucaia.pk)) == [juliana]
    # Valor que não é número: 400.
    assert _lista(cenario, filial="centro").status_code == 400

    # Desativada (FIL-06): sai do filtro, e a Juliana continua em "Todas".
    # Atalho do teste: o veto da desativação (FIL-06) é da T-012; aqui só importa o escopo.
    Filial.objects.filter(pk=caucaia.pk).update(ativo=False)
    desativada = _lista(cenario, filial=caucaia.pk)
    assert (desativada.status_code, desativada.json()["codigo"]) == (403, "USR-07")
    assert juliana in _nomes(_lista(cenario))


# --- Administrador decide o próprio pedido (APR-09) ---

APROVACOES = "/api/aprovacoes/"


def _despesa_de(cenario: Any, quem: str) -> dict[str, Any]:  # noqa: F811
    """R$ 1.200,00 na Filial Centro: nasce `aguardando_aprovacao` com o pedido APR-03 (FIN-05)."""
    centro = {"HTTP_X_FILIAL": str(cenario.frota.centro.pk)}
    resposta = _despesa(
        cenario, quem, centro, descricao="Revisão do QXA-4B21", valor_centavos=120000
    )
    assert resposta.status_code == 201, resposta.json()
    assert resposta.json()["status"] == "aguardando_aprovacao"
    return dict(resposta.json())


def _pedido_da_despesa(despesa: dict[str, Any]) -> PedidoAprovacao:
    return PedidoAprovacao.objects.get(origem_tipo="despesa", origem_id=despesa["id"])


def _decidir(cenario: Any, quem: str, pedido: PedidoAprovacao, acao: str, **corpo: Any) -> Any:  # noqa: F811
    return cenario.moto.api(quem).post(f"{APROVACOES}{pedido.pk}/{acao}/", corpo, format="json")


def _pendentes(cenario: Any, quem: str) -> list[int]:  # noqa: F811
    resposta = cenario.moto.api(quem).get(APROVACOES)
    assert resposta.status_code == 200, resposta.json()
    return [p["id"] for p in resposta.json()["resultados"]]


def _evento(pedido: PedidoAprovacao, acao: str) -> EventoAuditoria:
    return EventoAuditoria.objects.get(acao=f"pedido_aprovacao.{acao}", objeto_id=pedido.pk)


def test_apr_09_administrador_aprova_o_proprio_pedido(cenario, decisoes):  # noqa: F811
    """CA-248-08: o pedido nasce pendente, aparece nos números e em "Meus pedidos" da Mariana
    com `pode_decidir`, e ela aprova; o evento marca "Aprovou o próprio pedido"."""
    despesa = _despesa_de(cenario, "Mariana")
    pedido = _pedido_da_despesa(despesa)
    assert pedido.status == "pendente"
    for quem in ("Mariana", "Rodrigo"):
        assert pedido.pk in _pendentes(cenario, quem), quem
    meus = cenario.moto.api("Mariana").get(APROVACOES, {"minhas": "true"}).json()["resultados"]
    assert [(p["id"], p["pode_decidir"]) for p in meus] == [(pedido.pk, True)]

    resposta = _decidir(cenario, "Mariana", pedido, "aprovar")
    assert resposta.status_code == 200, resposta.json()
    assert (resposta.json()["status"], resposta.json()["proprio_pedido"]) == ("aprovado", True)
    assert Despesa.objects.get(pk=despesa["id"]).status == "a_pagar"
    evento = _evento(pedido, "aprovar")
    assert evento.depois["decidido_pelo_solicitante"] is True
    assert textos.texto(evento, {}).resumo == "Aprovou o próprio pedido"
    assert decisoes[-1]["proprio_pedido"] is True


def test_apr_09_administrador_recusa_o_proprio_pedido(cenario, decisoes):  # noqa: F811
    """CA-248-09: recusar o próprio pedido exige motivo e marca o evento; se o Rodrigo decide
    antes, o evento não tem a marca e a Mariana recebe 409."""
    pedido = _pedido_da_despesa(_despesa_de(cenario, "Mariana"))
    assert _decidir(cenario, "Mariana", pedido, "recusar").status_code == 400  # APR-07
    resposta = _decidir(cenario, "Mariana", pedido, "recusar", motivo="Orçamento alto")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["proprio_pedido"] is True
    evento = _evento(pedido, "recusar")
    assert textos.texto(evento, {}).resumo == "Recusou o próprio pedido"
    assert textos.texto(evento, {}).detalhe == "Orçamento alto"

    outro = _pedido_da_despesa(_despesa_de(cenario, "Mariana"))
    aprovado = _decidir(cenario, "Rodrigo", outro, "aprovar")
    assert (aprovado.status_code, aprovado.json()["proprio_pedido"]) == (200, False)
    assert "decidido_pelo_solicitante" not in _evento(outro, "aprovar").depois
    assert decisoes[-1]["proprio_pedido"] is False
    tarde = _decidir(cenario, "Mariana", outro, "aprovar")
    assert (tarde.status_code, tarde.json()["codigo"]) == (409, "transicao_pedido")


def test_apr_09_gerente_nao_aprova_o_proprio_pedido(cenario):  # noqa: F811
    """CA-248-10: o pedido do Rodrigo fica fora dos números dele, sem `pode_decidir`, e 403."""
    pedido = _pedido_da_despesa(_despesa_de(cenario, "Rodrigo"))
    assert pedido.pk not in _pendentes(cenario, "Rodrigo")
    meus = cenario.moto.api("Rodrigo").get(APROVACOES, {"minhas": "true"}).json()["resultados"]
    assert [(p["id"], p["pode_decidir"]) for p in meus] == [(pedido.pk, False)]
    for acao, corpo in (("aprovar", {}), ("recusar", {"motivo": "Não"})):
        resposta = _decidir(cenario, "Rodrigo", pedido, acao, **corpo)
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "APR-09"
        assert resposta.json()["mensagem"] == "Outra pessoa precisa decidir este pedido"
    aprovado = _decidir(cenario, "Mariana", pedido, "aprovar")
    assert (aprovado.status_code, aprovado.json()["proprio_pedido"]) == (200, False)


def test_apr_09_permissao_extra_nao_abre_a_excecao(cenario):  # noqa: F811
    """CA-248-11: a Bruna com `aprovar_desconto` (USR-03) não decide o próprio desconto."""
    bruna = cenario.pessoas["Bruna"]
    bruna.permissoes_extras = ["aprovar_desconto"]
    bruna.save(update_fields=["permissoes_extras"])
    pedido_id = aprovacoes.pedir(
        tipo="APR-01",
        origem_tipo="locacao",
        origem_id=801,
        origem_codigo=None,
        filial_id=cenario.frota.centro.pk,
        solicitante=bruna,
        titulo="Desconto de 8%",
        detalhe="Semanal Street",
    ).id
    pedido = PedidoAprovacao.objects.get(pk=pedido_id)
    resposta = _decidir(cenario, "Bruna", pedido, "aprovar")
    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "APR-09")
    assert _decidir(cenario, "Rodrigo", pedido, "aprovar").status_code == 200


def test_apr_09_check_exige_a_marca(cenario):  # noqa: F811
    """O banco não deixa `aprovador = solicitante` sem a marca, nem a marca sem a igualdade."""
    pedido = _pedido_da_despesa(_despesa_de(cenario, "Rodrigo"))
    rodrigo, mariana = cenario.pessoas["Rodrigo"], cenario.pessoas["Mariana"]
    linha = PedidoAprovacao.objects.filter(pk=pedido.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        linha.update(aprovador=rodrigo)
    with pytest.raises(IntegrityError), transaction.atomic():
        linha.update(aprovador=mariana, decidido_pelo_solicitante=True)
    linha.update(aprovador=rodrigo, decidido_pelo_solicitante=True)  # com a marca, passa


# --- Copiar link do convite (USR-01) ---

CARLA = {
    "email": "carla@motorapida.com.br",
    "nome": "Carla Rocha",
    "perfil": "vendedor",
}


def _carla(rapida: Any, api: Any, capturar: Any) -> Any:
    """CA-248-12: a Mariana convida a Carla em 07 out; o convite vence em 14 out."""
    resposta = _convidar(api, rapida, capturar, **CARLA, filiais=[rapida.centro.pk])
    assert resposta.status_code == 201, resposta.json()
    assert resposta.json()["convite_expira_em"].startswith("2026-10-14")
    assert resposta.json()["acoes"] == {
        "reenviar_convite": True,
        "copiar_link_convite": True,
        "cancelar_convite": True,
    }
    return Usuario.objects.get(email=CARLA["email"])


def _copiar(rapida: Any, api: Any, usuario: Any) -> Any:
    return _post(api, f"{USUARIOS}{usuario.pk}/link-convite/", rapida.empresa)


def _token(resposta: Any) -> str:
    assert resposta.status_code == 200, resposta.json()
    return str(resposta.json()["link"].split("/convite#", 1)[1])


def _vale(rapida: Any, token: str) -> bool:
    publica = rapida.cliente(ip="189.2.2.2")
    return bool(_post(publica, CONSULTAR, rapida.empresa, {"token": token}).status_code == 200)


def test_usr_01_copiar_link_invalida_o_anterior(adm, relogio, django_capture_on_commit_callbacks):  # noqa: F811
    """CA-248-12 e 13: o link copiado vence em 7 dias, não sai por e-mail nem WhatsApp, derruba
    o anterior e não muda status nem plano; o reenvio derruba o link copiado."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    carla = _carla(adm, api, django_capture_on_commit_callbacks)
    do_email = _token_do_convite(mail.outbox[-1])
    enviados = (len(mail.outbox), len(caixa_de_saida))
    assert _uso_de_usuarios(adm) == 6

    relogio.em("2026-10-09 10:00")
    api = adm.logar("Mariana")
    with django_capture_on_commit_callbacks(execute=True):
        resposta = _copiar(adm, api, carla)
    connection.set_tenant(adm.empresa)
    copiado = _token(resposta)
    corpo = resposta.json()
    assert resposta["Cache-Control"] == "no-store"
    assert corpo["link"].startswith("https://") and "/convite#" in corpo["link"]
    assert corpo["expira_em"].startswith("2026-10-16")
    assert corpo["aviso"] == "O link anterior deixa de valer."
    assert corpo["usuario"]["status"] == "convite_pendente"
    assert corpo["usuario"]["convite_expira_em"].startswith("2026-10-16")
    assert (len(mail.outbox), len(caixa_de_saida)) == enviados  # nada enviado
    assert _uso_de_usuarios(adm) == 6
    assert not _vale(adm, do_email)
    assert _vale(adm, copiado)

    # CA-248-13: copiar de novo derruba o primeiro copiado; o reenvio derruba o copiado.
    segundo = _token(_copiar(adm, api, carla))
    assert not _vale(adm, copiado) and _vale(adm, segundo)
    with django_capture_on_commit_callbacks(execute=True):
        assert api.post(f"{USUARIOS}{carla.pk}/reenviar-convite/").status_code == 200
    connection.set_tenant(adm.empresa)
    assert not _vale(adm, segundo)
    reenviado = _token_do_convite(mail.outbox[-1])
    aceito = _post(adm.cliente(), ACEITAR, adm.empresa, {"token": reenviado, "senha": SENHA})
    assert aceito.status_code == 200, aceito.json()

    # O link nunca volta na leitura do usuário.
    detalhe = _get(api, f"{USUARIOS}{carla.pk}/", adm.empresa)
    assert "link" not in detalhe.json() and "convite#" not in str(detalhe.json())


def test_usr_01_copiar_link_convite_vencido(adm, relogio, django_capture_on_commit_callbacks):  # noqa: F811
    """CA-248-14: em 15 out o convite de 07 out venceu; o link copiado vence em 22 out e
    cria a senha."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    carla = _carla(adm, api, django_capture_on_commit_callbacks)
    relogio.em("2026-10-15 10:00")
    api = adm.logar("Mariana")
    resposta = _copiar(adm, api, carla)
    assert resposta.json()["expira_em"].startswith("2026-10-22")
    assert resposta.json()["usuario"]["status"] == "convite_pendente"
    aceito = _post(adm.cliente(), ACEITAR, adm.empresa, {"token": _token(resposta), "senha": SENHA})
    assert aceito.status_code == 200, aceito.json()


def test_usr_01_copiar_link_so_administrador(adm, relogio, django_capture_on_commit_callbacks):  # noqa: F811
    """CA-248-15: gerente e os outros perfis, 403; suporte Giro, 403 PLT-07; ativo e
    desativado, 409."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    carla = _carla(adm, api, django_capture_on_commit_callbacks)
    outros = {nome: adm.logar(nome) for nome in ("Rodrigo", "Bruna")}
    outros |= {nome: _api_de(adm, nome) for nome in ("João", "Lúcia")}
    for nome, outro in outros.items():
        assert _copiar(adm, outro, carla).status_code == 403, nome
    for permissao in ("ver", "ver_editar"):
        suporte = _suporte(adm, permissao)
        negado = _copiar(adm, suporte, carla)
        assert (negado.status_code, negado.json()["codigo"]) == (403, "PLT-07"), permissao
    assert not EventoAuditoria.objects.filter(acao="usuario.copiar_link_convite").exists()

    for nome in ("Bruna", "Felipe"):
        recusado = _copiar(adm, api, adm.pessoas[nome])
        assert (recusado.status_code, recusado.json()["codigo"]) == (409, "transicao_usuario")
        assert recusado.json()["mensagem"] == "Só dá para copiar o link de um convite pendente."
        acoes = _get(api, f"{USUARIOS}{adm.pessoas[nome].pk}/", adm.empresa).json()["acoes"]
        assert not any(acoes.values()), nome


def test_usr_01_copiar_link_limite_por_hora(adm, relogio, django_capture_on_commit_callbacks):  # noqa: F811
    """CA-248-15: 5 por hora por pessoa convidada; o 6º responde 429 e o último link segue
    valendo (nada gerado nem invalidado)."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    carla = _carla(adm, api, django_capture_on_commit_callbacks)
    tokens = [_token(_copiar(adm, api, carla)) for _ in range(5)]
    estourou = _copiar(adm, api, carla)
    assert (estourou.status_code, estourou.json()["codigo"]) == (429, "muitas_requisicoes")
    assert _vale(adm, tokens[-1])
    assert EventoAuditoria.objects.filter(acao="usuario.copiar_link_convite").count() == 5


def test_usr_01_copiar_link_limite_por_administrador(adm, relogio):  # noqa: F811
    """20 por hora por administrador, somando pessoas diferentes."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    pessoas = [
        services.convidar(email=f"pessoa{n}@motorapida.com.br", perfil="administrador")
        for n in range(5)
    ]
    for _ in range(4):
        for pessoa in pessoas:
            assert _copiar(adm, api, pessoa).status_code == 200
    estourou = _copiar(adm, api, pessoas[0])
    assert (estourou.status_code, estourou.json()["codigo"]) == (429, "muitas_requisicoes")


def test_usr_01_copiar_link_evento_sem_token(
    adm,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
    caplog,
):
    """CA-248-16: evento `seguranca` com quem copiou, de quem é e o vencimento, sem o link."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    carla = _carla(adm, api, django_capture_on_commit_callbacks)
    caplog.set_level(logging.DEBUG)
    resposta = _copiar(adm, api, carla)
    token = _token(resposta)
    evento = EventoAuditoria.objects.get(acao="usuario.copiar_link_convite")
    assert evento.categoria == "seguranca"
    assert (evento.ator_id, evento.objeto_id) == (adm.pessoas["Mariana"].pk, carla.pk)
    assert list(evento.depois) == ["convite_expira_em"]
    assert evento.depois["convite_expira_em"].startswith("2026-10-14")
    gravado = str(evento.antes) + str(evento.depois) + evento.motivo
    assert token not in gravado and "convite#" not in gravado
    assert token not in caplog.text
    assert textos.texto(evento, {}).resumo == "Copiou o link do convite"
