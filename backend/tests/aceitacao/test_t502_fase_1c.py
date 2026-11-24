"""T-502 · Fluxo de venda, fase 1c: envio da proposta, link público, metas e resumo (ADR 0042,
itens 8, 13 e 14; `docs/api/vendas.md`).

Cenário da T-015: Moto Rápida, Filial Centro, 07 out 2026, 10:00. A Bruna (vendedora) vende; o
Rodrigo (gerente) define as metas. As vendas concluídas de setembro e outubro de
`dados-de-teste.md` entram direto no banco, já `vendida`: a conclusão pela assinatura e pela
entrada é da fase 1b, e aqui só se leem os números.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django_tenants.utils import schema_context

from apps.aprovacoes import services as aprovacoes_services
from apps.auditoria.models import EventoAuditoria
from apps.clientes import services as clientes_services
from apps.clientes import titular
from apps.contas.models import Usuario
from apps.plataforma.models import Empresa
from apps.relatorios import selectors as relatorios_selectors
from apps.vendas import envio
from apps.vendas.models import MetaVenda, Venda
from comum import arquivos
from comum import relogio as relogio_do_giro
from comum.empresa import nome_da_empresa
from comum.estados import transicionar

from .test_t015_locacoes import Cenario, cenario  # noqa: F401
from .test_t090_contratos import HOST_B, _publica
from .test_t502_fluxo_de_venda import VEN_0177, _cb, _criada, _pedido, _post

FUSO = ZoneInfo("America/Sao_Paulo")
VENDAS = "/api/vendas/"
RESUMO = "/api/vendas/resumo/"
METAS = "/api/vendas/metas/"
PROPOSTA_PUBLICA = "/api/publico/propostas/consultar/"
EMAIL_DO_DIEGO = "diego@exemplo.com"
A_VISTA = {"forma": "a_vista", "desconto_pct": "0.00"}


@pytest.fixture(autouse=True)
def _proposta_publica_ligada(settings):
    """Os casos do link valem com a página `/proposta` no ar (`GIRO_PROPOSTA_PUBLICA`); o
    desligado tem teste próprio."""
    settings.GIRO_PROPOSTA_PUBLICA = True
    cache.clear()


def _com_email(cenario: Cenario, nome: str = "Diego", email: str = EMAIL_DO_DIEGO) -> None:  # noqa: F811
    cliente = cenario.cliente(nome)
    cliente.email = email
    cliente.save(update_fields=["email"])


def _enviada(cenario: Cenario, capturar: Any, **campos: Any) -> dict[str, Any]:  # noqa: F811
    with capturar(execute=True):
        return _criada(cenario, "enviar", **{**VEN_0177, "desconto_pct": "5.00", **campos})


def _copiar(cenario: Cenario, venda_id: int, quem: str = "Bruna") -> Any:  # noqa: F811
    return cenario.moto.api(quem).post(f"{VENDAS}{venda_id}/proposta/link/")


def _token(link: str) -> str:
    prefixo = "https://empresa-a.localhost/proposta#"
    assert link.startswith(prefixo), link
    return link.removeprefix(prefixo)


def _abrir(token: str, host: str | None = None) -> Any:
    return (_publica(host) if host else _publica()).post(
        PROPOSTA_PUBLICA, {"token": token}, format="json"
    )


# --- Envio da proposta (VEN-15, VEN-19) ---


def test_ven_15_proposta_enviada_vai_por_email_com_o_pdf(
    cenario,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    _com_email(cenario)
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    (mensagem,) = mail.outbox
    assert mensagem.to == [EMAIL_DO_DIEGO]
    assert mensagem.subject == f"{nome_da_empresa()}: proposta da {venda['codigo']}"
    assert "Olá, Diego Martins." in mensagem.body
    assert "Honda CB 300F" in mensagem.body and "R$ 21.755,00" in mensagem.body
    assert "Ela vale até 14/10/2026." in mensagem.body
    ((nome, conteudo, tipo),) = mensagem.attachments
    assert (nome, tipo) == (f"proposta-{venda['codigo']}.pdf", "application/pdf")
    assert conteudo.startswith(b"%PDF")
    assert Venda.objects.get(pk=venda["id"]).proposta_pdf


def test_ven_19_reenvio_traz_o_texto_pronto(cenario, django_capture_on_commit_callbacks):  # noqa: F811
    _com_email(cenario)
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    with django_capture_on_commit_callbacks(execute=True):
        resposta = _post(cenario, venda["id"], "enviar")
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["email_enviado"] is True
    assert corpo["texto"] == (
        "Proposta enviada para diego@exemplo.com em 07 out. "
        "Sem resposta do cliente, ela vence em 14 out."
    )
    assert len(mail.outbox) == 2


def test_ven_19_cliente_sem_email_copiar_link(cenario, django_capture_on_commit_callbacks):  # noqa: F811
    """A proposta é salva e conta como enviada; nada sai por e-mail, o PDF fica gravado para o
    "Copiar link"."""
    _com_email(cenario, email="")
    venda = _criada(cenario, "interessado", **{**VEN_0177, "desconto_pct": "5.00"})
    with django_capture_on_commit_callbacks(execute=True):
        resposta = _post(cenario, venda["id"], "enviar")
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["email_enviado"] is False
    assert corpo["texto"] == (
        "A proposta foi salva, mas este cliente não tem e-mail cadastrado. "
        "Copie o link e envie para ele."
    )
    assert corpo["venda"]["status"] == "proposta"
    assert mail.outbox == []
    assert Venda.objects.get(pk=venda["id"]).proposta_pdf


def test_ven_15_envio_antigo_nao_manda_a_proposta_que_mudou(
    cenario,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """A tarefa leva a data do envio: a de um envio mais antigo não manda nada."""
    from apps.vendas.envio import enviar

    _com_email(cenario)
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    enviar(venda["id"], "2026-10-01T00:00:00+00:00")
    assert len(mail.outbox) == 1


# --- Link público da proposta (VEN-15, S-15) ---


def test_ven_15_copiar_link_abre_o_pdf(cenario, django_capture_on_commit_callbacks):  # noqa: F811
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    resposta = _copiar(cenario, venda["id"])
    assert resposta.status_code == 200, resposta.json()
    assert resposta["Cache-Control"] == "no-store"
    assert resposta.json()["aviso"] == "O link anterior deixa de valer."
    token = _token(resposta.json()["link"])

    aberto = _abrir(token)
    assert aberto.status_code == 200, aberto.json()
    assert (aberto["Cache-Control"], aberto["X-Robots-Tag"]) == ("no-store", "noindex")
    proposta = aberto.json()["proposta"]
    assert proposta["codigo"] == venda["codigo"]
    assert proposta["cliente_primeiro_nome"] == "Diego"
    assert proposta["veiculo"] == "Honda CB 300F"
    assert proposta["vence_em"] == "2026-10-14"
    assert proposta["pdf_url"].startswith("https://")
    assert set(aberto.json()) == {"empresa", "proposta"}  # nada além do necessário
    assert _abrir(token).status_code == 200  # não é de uso único
    salva = Venda.objects.get(pk=venda["id"])
    assert salva.token_proposta_hash and token not in salva.token_proposta_hash
    copiou = EventoAuditoria.objects.get(acao="venda.copiar_link_proposta")
    assert (copiou.regra, copiou.categoria) == ("S-15", "seguranca")
    assert token not in str(copiou.depois)
    # Uma abertura por dia na auditoria.
    assert EventoAuditoria.objects.filter(acao="venda.proposta_aberta").count() == 1


def test_ven_15_link_novo_anula_o_anterior(cenario, django_capture_on_commit_callbacks):  # noqa: F811
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    primeiro = _token(_copiar(cenario, venda["id"]).json()["link"])
    segundo = _token(_copiar(cenario, venda["id"]).json()["link"])
    assert _abrir(primeiro).status_code == 404
    assert _abrir(segundo).status_code == 200


def test_ven_15_link_vence_em_7_dias_e_com_a_venda_perdida(
    cenario,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
):
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    token = _token(_copiar(cenario, venda["id"]).json()["link"])
    relogio.em("2026-10-14 10:01")
    assert _abrir(token).status_code == 410
    relogio.em("2026-10-07 11:00")
    assert _abrir(token).status_code == 200
    perdida = _post(cenario, venda["id"], "perder", motivo="Comprou em outra loja")
    assert perdida.status_code == 200, perdida.json()
    assert _abrir(token).status_code == 410


def test_ven_15_link_recusas(cenario, settings, django_capture_on_commit_callbacks):  # noqa: F811
    interessado = _criada(cenario, "interessado", **VEN_0177 | {"desconto_pct": "5.00"})
    resposta = _copiar(cenario, interessado["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "transicao_venda")
    assert _abrir("token-que-nao-existe").status_code == 404
    assert _abrir("").status_code == 400
    venda = _enviada(cenario, django_capture_on_commit_callbacks, veiculo_id=_cb(cenario, 1).pk)
    token = _token(_copiar(cenario, venda["id"]).json()["link"])
    # O vendedor de outra venda não copia; o financeiro e o vistoriador também não.
    assert _copiar(cenario, venda["id"], "Lúcia").status_code in (403, 404)
    settings.GIRO_PROPOSTA_PUBLICA = False
    desligado = _copiar(cenario, venda["id"])
    assert (desligado.status_code, desligado.json()["codigo"]) == (
        409,
        "proposta_publica_desligada",
    )
    assert _abrir(token).status_code == 404


def test_ven_15_link_da_empresa_a_nao_abre_na_b(cenario, django_capture_on_commit_callbacks):  # noqa: F811
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    token = _token(_copiar(cenario, venda["id"]).json()["link"])
    try:
        assert _abrir(token, HOST_B).status_code == 404
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))


# --- Vendas concluídas de setembro e outubro (dados-de-teste.md, VEN-12, FIN-09, FIN-10) ---


def _momento(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=FUSO)


def _venda(
    cenario: Cenario,  # noqa: F811
    valor: int,
    status: str,
    *,
    criada: str,
    proposta: str | None = None,
    negociacao: str | None = None,
    vendida: str | None = None,
    veiculo: int = 0,
    quem: str = "Bruna",
    contato: str | None = None,
) -> Venda:
    veiculo_da_venda = _cb(cenario, veiculo)
    venda = Venda.objects.create(
        filial=cenario.frota.centro,
        cliente=cenario.cliente("Diego"),
        veiculo=veiculo_da_venda,
        vendedor=cenario.pessoas[quem],
        preco_tabela_centavos=valor,
        preco_final_centavos=valor,
        forma="a_vista",
        entrada_centavos=valor,
        status=status,
        entrou_proposta_em=_momento(proposta) if proposta else None,
        entrou_negociacao_em=_momento(negociacao) if negociacao else None,
        vendida_em=_momento(vendida) if vendida else None,
        ultimo_contato_em=_momento(contato or criada),
    )
    Venda.objects.filter(pk=venda.pk).update(criado_em=_momento(criada))
    return venda


@pytest.fixture
def vendas(cenario) -> dict[str, Venda]:  # noqa: F811
    """Setembro: 4 vendidas, R$ 55.000,00 (a Bruna 3 × R$ 12.000,00; R$ 19.000,00 do Rodrigo,
    no lugar do Felipe). Outubro até 07 out, 12 criadas: as 4 vendidas da Bruna, R$ 31.200,00
    (as de FIN-10); a VEN-0177 (R$ 21.068,00) em `aguardando_aprovacao`; R$ 13.200,00 em
    `negociacao`; R$ 21.800,00 em `proposta`; uma perdida que passou pela aprovação; 4
    interessados. Funil 12, 6, 3, 4; conversão 4 ÷ 12 = 33%."""
    criadas = {}
    for i, dia in enumerate(("01", "02", "03")):
        criadas[f"set{i}"] = _venda(
            cenario,
            1200000,
            "vendida",
            criada=f"2026-08-2{i} 10:00",
            proposta=f"2026-08-2{i} 10:00",
            vendida=f"2026-09-{dia} 10:00",
        )
    criadas["set3"] = _venda(
        cenario,
        1900000,
        "vendida",
        criada="2026-08-25 10:00",
        proposta="2026-08-25 10:00",
        vendida="2026-09-04 10:00",
        quem="Rodrigo",
    )
    for i, valor in enumerate((600000, 720000, 800000, 1000000)):
        criadas[f"out{i}"] = _venda(
            cenario,
            valor,
            "vendida",
            criada=f"2026-10-0{i + 1} 09:00",
            proposta=f"2026-10-0{i + 1} 09:00",
            vendida=f"2026-10-0{i + 1} 15:00",
        )
    criadas["ven_0177"] = _venda(
        cenario,
        2106800,
        "aguardando_aprovacao",
        criada="2026-10-05 10:00",
        negociacao="2026-10-05 10:00",
        veiculo=1,
        contato="2026-10-07 09:00",
    )
    criadas["negociacao"] = _venda(
        cenario,
        1320000,
        "negociacao",
        criada="2026-10-02 10:00",
        proposta="2026-10-02 10:00",
        negociacao="2026-10-04 10:00",
        veiculo=2,
        contato="2026-10-04 10:00",
    )
    criadas["proposta"] = _venda(
        cenario,
        2180000,
        "proposta",
        criada="2026-10-03 10:00",
        proposta="2026-10-03 10:00",
        veiculo=3,
        contato="2026-10-03 10:00",
    )
    criadas["perdida"] = _venda(
        cenario,
        1500000,
        "perdida",
        criada="2026-10-01 10:00",
        negociacao="2026-10-01 11:00",
        veiculo=4,
    )
    for i in range(4):
        criadas[f"interessado{i}"] = _venda(
            cenario,
            1000000,
            "interessado",
            criada=f"2026-10-0{i + 1} 08:00",
            contato=f"2026-10-0{i + 1} 08:00",
        )
    return criadas


def _resumo(cenario: Cenario, quem: str = "Rodrigo", **params: Any) -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api(quem).get(RESUMO, params)
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def test_ven_08_funil_e_conversao(cenario, vendas):  # noqa: F811
    corpo = _resumo(cenario)
    assert corpo["funil"] == {"interessados": 12, "proposta": 6, "negociacao": 3, "vendido": 4}
    assert corpo["conversao"] == {"vendidas": 4, "criadas": 12, "pct": 33}
    assert corpo["subtitulo"] == "Vendas de outubro · Filial Centro"


def test_ven_12_vendido_e_ticket_de_outubro(cenario, vendas):  # noqa: F811
    vendido = _resumo(cenario)["vendido"]
    assert (vendido["quantidade"], vendido["soma_centavos"], vendido["ticket_centavos"]) == (
        4,
        3120000,
        780000,
    )
    assert vendido["mes_anterior"]["ticket_centavos"] == 1375000
    setembro = _resumo(cenario, mes="2026-09")
    assert setembro["vendido"]["soma_centavos"] == 5500000
    assert setembro["vendido"]["mes_anterior"]["quantidade"] == 0
    assert _resumo(cenario, mes="2026-11")["vendido"]["vazio"] == "Sem vendas em novembro."


def test_ven_12_ticket_medio_do_inicio_le_as_vendas_concluidas(cenario, vendas):  # noqa: F811
    """O bloco da T-487 (`/api/painel/inicio/`) com as vendas de verdade: outubro 4 vendas,
    R$ 31.200,00, ticket R$ 7.800,00; setembro R$ 13.750,00; −43,27%. Uma venda de setembro de
    R$ 12.000,00 cancelada em 05 out: setembro 3 vendas, R$ 43.000,00, R$ 14.333,33; −45,58%."""
    escopo = relatorios_selectors.Escopo(filiais=frozenset({cenario.frota.centro.pk}), todas=False)
    bloco = relatorios_selectors._ticket_medio(escopo)
    assert (bloco["vendas"], bloco["soma_centavos"], bloco["ticket_centavos"]) == (
        4,
        3120000,
        780000,
    )
    assert bloco["resumo"] == "4 vendas · R$ 31.200,00"
    assert bloco["comparacao"] == "−43,27% em relação a setembro (R$ 13.750,00)"
    # VEN-07 (fase 2): a cancelada sai do mês dela; aqui, pela máquina de estados.
    transicionar(vendas["set0"], "cancelada", acao="venda.cancelar", regra="VEN-07")
    bloco = relatorios_selectors._ticket_medio(escopo)
    assert bloco["mes_anterior"]["ticket_centavos"] == 1433333
    assert bloco["variacao_pct"] == Decimal("-45.58")


def test_ven_19_em_negociacao_e_aguardando(cenario, vendas):  # noqa: F811
    corpo = _resumo(cenario)
    assert corpo["em_negociacao"] == {
        "quantidade": 3,
        "soma_centavos": 5606800,
        "aguardando_aprovacao": 1,
    }
    assert corpo["transferencias_pendentes"] == 8  # as 8 vendidas, nenhuma transferida


def test_ven_16_propostas_para_retornar(cenario, vendas):  # noqa: F811
    """As abertas da mais antiga para a mais recente pelo último contato, com o celular do
    "Chamar no WhatsApp"."""
    retornar = _resumo(cenario)["propostas_para_retornar"]
    assert [p["venda_id"] for p in retornar] == [
        vendas["interessado0"].pk,
        vendas["interessado1"].pk,
        vendas["interessado2"].pk,
        vendas["proposta"].pk,
        vendas["interessado3"].pk,
        vendas["negociacao"].pk,
        vendas["ven_0177"].pk,
    ]
    assert retornar[0]["celular"] == "85983332211"
    lista = cenario.moto.api("Rodrigo").get(VENDAS, {"aba": "abertas", "ordem": "ultimo_contato"})
    assert lista.status_code == 200, lista.json()
    itens = lista.json()["resultados"]
    assert [i["id"] for i in itens] == [p["venda_id"] for p in retornar]
    assert itens[0]["comprador_celular"] == "85983332211"


# --- Meta (VEN-09) ---


def test_ven_09_meta_da_vendedora_62_pct_faltam_24_dias(cenario, vendas):  # noqa: F811
    assert _resumo(cenario, "Bruna")["meta"]["texto"] == "Sem meta em outubro."
    resposta = cenario.moto.api("Rodrigo").put(
        METAS,
        {
            "filial_id": cenario.frota.centro.pk,
            "mes": "2026-10",
            "metas": [{"vendedor_id": cenario.pessoas["Bruna"].pk, "valor_centavos": 5000000}],
        },
        format="json",
    )
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["soma_centavos"] == 5000000
    assert resposta.json()["vendedores"] == [
        {
            "vendedor": {"id": cenario.pessoas["Bruna"].pk, "nome": cenario.pessoas["Bruna"].nome},
            "valor_centavos": 5000000,
        }
    ]
    meta = _resumo(cenario, "Bruna")["meta"]
    assert (meta["valor_centavos"], meta["vendido_centavos"], meta["pct"]) == (
        5000000,
        3120000,
        62,
    )
    assert meta["faltam_dias"] == 24
    assert meta["texto"] == "62% de R$ 50.000,00 · faltam 24 dias"
    # A meta da filial é a soma das metas dos vendedores.
    assert _resumo(cenario)["meta"]["valor_centavos"] == 5000000
    evento = EventoAuditoria.objects.get(acao="meta_venda.definir")
    assert (evento.regra, evento.categoria) == ("VEN-09", "configuracoes")


def test_ven_09_tirar_meta_e_quem_define(cenario):  # noqa: F811
    bruna = cenario.pessoas["Bruna"].pk
    corpo = {
        "filial_id": cenario.frota.centro.pk,
        "mes": "2026-10",
        "metas": [{"vendedor_id": bruna, "valor_centavos": 5000000}],
    }
    assert cenario.moto.api("Mariana").put(METAS, corpo, format="json").status_code == 200
    assert cenario.moto.api("Bruna").put(METAS, corpo, format="json").status_code == 403
    assert cenario.moto.api("Bruna").get(METAS).status_code == 403
    rodrigo = {
        **corpo,
        "metas": [{"vendedor_id": cenario.pessoas["Rodrigo"].pk, "valor_centavos": 100}],
    }
    errado = cenario.moto.api("Rodrigo").put(METAS, rodrigo, format="json")
    assert errado.status_code == 400
    assert errado.json()["campos"]["metas"] == ["Escolha vendedores ativos desta filial."]
    tirar = {**corpo, "metas": [{"vendedor_id": bruna, "valor_centavos": None}]}
    resposta = cenario.moto.api("Rodrigo").put(METAS, tirar, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["soma_centavos"] is None
    assert not MetaVenda.objects.exists()
    tirou = EventoAuditoria.objects.get(acao="meta_venda.tirar")
    assert tirou.antes == {"valor_centavos": 5000000}
    quadro = cenario.moto.api("Rodrigo").get(METAS, {"mes": "2026-10"}).json()
    assert quadro["texto"] == (
        "Defina a meta de cada vendedor da Filial Centro. Deixe em branco para ficar sem meta."
    )


# --- O que a vendedora vê (USR-08) e o início dela ---


def test_usr_08_vendedora_ve_so_os_numeros_dela(cenario, vendas):  # noqa: F811
    corpo = _resumo(cenario, "Bruna", mes="2026-09")
    assert corpo["vendido"]["soma_centavos"] == 3600000  # sem a venda do Rodrigo
    assert _resumo(cenario, "Rodrigo", mes="2026-09")["vendido"]["soma_centavos"] == 5500000


def test_ven_08_inicio_da_vendedora_com_meta_funil_e_propostas(cenario, vendas):  # noqa: F811
    cache.clear()
    inicio = cenario.moto.api("Bruna").get("/api/painel/inicio/")
    assert inicio.status_code == 200, inicio.json()
    corpo = inicio.json()
    assert corpo["meta"]["texto"] == "Sem meta em outubro."
    assert corpo["funil"]["vendido"] == 4
    assert corpo["funil"]["conversao"]["pct"] == 33
    assert corpo["propostas"]["abertas"] == 3
    assert corpo["propostas"]["para_retornar"][0]["venda_id"] == vendas["interessado0"].pk
    cache.clear()
    contadores = cenario.moto.api("Bruna").get("/api/painel/contadores/").json()["contadores"]
    assert contadores.get("propostas") in (3, None)  # só vem se o menu da pessoa tem "Propostas"


# --- A comissão no cálculo (FIN-09) ---


def test_fin_09_percentual_da_comissao_no_calculo(cenario):  # noqa: F811
    corpo = cenario.moto.api("Bruna").post(
        "/api/vendas/simular/", {"veiculo_id": _cb(cenario).pk, **VEN_0177}, format="json"
    )
    assert corpo.status_code == 200, corpo.json()
    assert (corpo.json()["comissao_pct"], corpo.json()["comissao_centavos"]) == ("3.00", 63204)
    venda = _criada(cenario, "interessado", **VEN_0177 | {"desconto_pct": "5.00"})
    assert venda["calculo"]["comissao_pct"] == "3.00"


def test_ven_isolamento_do_resumo_e_das_metas(cenario, vendas):  # noqa: F811
    MetaVenda.objects.create(
        vendedor=cenario.pessoas["Bruna"],
        filial=cenario.frota.centro,
        mes=relogio_do_giro.hoje().replace(day=1),
        valor_centavos=5000000,
        definida_por=cenario.pessoas["Rodrigo"],
    )
    empresa_b = Empresa.objects.get(schema_name="empresa_b")
    connection.set_tenant(empresa_b)
    try:
        assert not Venda.objects.exists()
        assert not MetaVenda.objects.exists()
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))


# --- VEN-13: a aprovada que vinha de interessado é enviada sozinha (decisão de 18 nov, #665) ---


def test_ven_13_aprovada_de_interessado_e_enviada(
    cenario,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
):
    """De `interessado`, o pedido de aprovação tomou o lugar do "Salvar e enviar": aprovado às
    11:00, a proposta sai por e-mail com o PDF e a data da aprovação é a do envio (vence em 14
    out). Sem e-mail, vale o "Cliente sem e-mail" da VEN-19: só o PDF. A que vinha de `proposta`
    não é reenviada (o vendedor usa "Enviar")."""
    _com_email(cenario)
    criada = _criada(cenario, "pedir_aprovacao", **VEN_0177)
    assert mail.outbox == []
    relogio.em("2026-10-07 11:00")
    with django_capture_on_commit_callbacks(execute=True):
        aprovacoes_services.aprovar(_pedido(criada["id"]), cenario.pessoas["Rodrigo"])
    venda = Venda.objects.get(pk=criada["id"])
    assert (venda.status, venda.proposta_enviada_em) == ("proposta", relogio.agora)
    assert venda.proposta_pdf
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [EMAIL_DO_DIEGO]
    assert mail.outbox[0].attachments[0][0] == f"proposta-{venda.codigo}.pdf"
    assert envio.texto_do_envio(venda) == (
        "Proposta enviada para diego@exemplo.com em 07 out. "
        "Sem resposta do cliente, ela vence em 14 out."
    )

    # Sem e-mail: a proposta conta como enviada na aprovação e só o PDF é gravado.
    _com_email(cenario, email="")
    sem_email = _criada(cenario, "pedir_aprovacao", **{**VEN_0177, "veiculo": _cb(cenario, 1)})
    with django_capture_on_commit_callbacks(execute=True):
        aprovacoes_services.aprovar(_pedido(sem_email["id"]), cenario.pessoas["Rodrigo"])
    venda = Venda.objects.get(pk=sem_email["id"])
    assert (venda.status, venda.proposta_enviada_em) == ("proposta", relogio.agora)
    assert venda.proposta_pdf
    assert len(mail.outbox) == 1
    assert envio.texto_do_envio(venda) == (
        "A proposta foi salva, mas este cliente não tem e-mail cadastrado. "
        "Copie o link e envie para ele."
    )

    # A que vinha de `proposta` o cliente já recebeu: aprovada, não sai de novo.
    _com_email(cenario)
    enviada = _enviada(cenario, django_capture_on_commit_callbacks, veiculo=_cb(cenario, 2))
    assert len(mail.outbox) == 2
    with django_capture_on_commit_callbacks(execute=True):
        pedido = _post(cenario, enviada["id"], "pedir-aprovacao", desconto_pct="8.00")
        assert pedido.status_code == 200, pedido.json()
        aprovacoes_services.aprovar(_pedido(enviada["id"]), cenario.pessoas["Rodrigo"])
    assert Venda.objects.get(pk=enviada["id"]).status == "proposta"
    assert len(mail.outbox) == 2


# --- S-15: revisão da Segurança no #650 ---


def test_s_15_editar_a_proposta_anula_o_link_e_o_pdf(cenario, django_capture_on_commit_callbacks):  # noqa: F811
    """Trocar o cliente ou os valores em `proposta` anula o token e o PDF de antes: o link não
    entrega ao cliente novo o PDF com o nome do anterior. O link novo grava o PDF de agora."""
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    token = _token(_copiar(cenario, venda["id"]).json()["link"])
    assert _abrir(token).status_code == 200
    pdf_antes = Venda.objects.get(pk=venda["id"]).proposta_pdf.name
    outro = cenario.cliente("Carlos")
    editada = cenario.moto.api("Bruna").patch(
        f"{VENDAS}{venda['id']}/", {"cliente_id": outro.pk, "desconto_pct": "4.00"}, format="json"
    )
    assert editada.status_code == 200, editada.json()
    salva = Venda.objects.get(pk=venda["id"])
    assert (salva.token_proposta_hash, salva.token_proposta_expira_em) == (None, None)
    assert not salva.proposta_pdf
    assert _abrir(token).status_code == 404
    novo = _token(_copiar(cenario, venda["id"]).json()["link"])
    aberto = _abrir(novo)
    assert aberto.status_code == 200, aberto.json()
    assert aberto.json()["proposta"]["cliente_primeiro_nome"] == outro.nome.split()[0]
    salva.refresh_from_db()
    assert salva.proposta_pdf and salva.proposta_pdf.name != pdf_antes
    assert outro.nome in envio.corpo(salva)


def test_aud_06_anonimizar_apaga_o_pdf_da_proposta_e_anula_o_link(
    cenario,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """Padrão A do dono (`pontos-em-aberto.md`, #665) e item 3 da Segurança no #650: a
    anonimização do titular (AUD-06) apaga o PDF da proposta de todas as vendas dele, com as
    versões antigas, e anula o link; a venda continua, com o cliente anonimizado."""
    paula = clientes_services.cadastrar(
        {
            "tipo": "pf",
            "nome": "Paula Souza",
            "documento": "52998224725",
            "celular": "85988880000",
            "email": "paula@exemplo.test",
        }
    )
    venda = _enviada(cenario, django_capture_on_commit_callbacks, cliente_id=paula.pk)
    primeiro_pdf = Venda.objects.get(pk=venda["id"]).proposta_pdf.name
    token = _token(_copiar(cenario, venda["id"]).json()["link"])
    pdf_do_link = Venda.objects.get(pk=venda["id"]).proposta_pdf.name
    assert primeiro_pdf != pdf_do_link  # o link grava o PDF de agora
    assert arquivos.provedor().existe(primeiro_pdf) and arquivos.provedor().existe(pdf_do_link)
    perdida = _post(cenario, venda["id"], "perder", motivo="Desistiu da compra")
    assert perdida.status_code == 200, perdida.json()

    with schema_context("public"):
        dono = Usuario.objects.create_user(
            "dono-1c@giro.test",
            "senha-longa-2026",
            nome="Ana Dono",
            funcao_plataforma="dono",
            status="ativo",
        )
    empresa = Empresa.objects.get(schema_name="empresa_a")
    pedido = titular.Pedido(dono=dono, motivo="Chamado 4522: pedido da titular")
    apagados = titular.anonimizar(empresa, paula.pk, pedido, "Paula Souza")
    connection.set_tenant(empresa)

    assert apagados >= 2
    assert not arquivos.provedor().existe(primeiro_pdf)
    assert not arquivos.provedor().existe(pdf_do_link)
    salva = Venda.objects.get(pk=venda["id"])
    assert not salva.proposta_pdf
    assert (salva.token_proposta_hash, salva.token_proposta_expira_em) == (None, None)
    assert salva.cliente_id == paula.pk  # a venda fica, com o cliente anonimizado
    assert salva.cliente is not None and salva.cliente.anonimizado_em is not None
    assert _abrir(token).status_code == 404
