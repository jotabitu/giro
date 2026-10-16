"""T-288 · Movimentações: backend (docs/qa/criterios/T-246.md, CA-246-01 a 19; T-300).

Moto Rápida em 07 out 2026, 10:00, Filial Centro, com a frota e os clientes do cenário da T-015.
Locais de apoio criados no teste: "Lava Rápido Aldeota", "Despachante Rocha" e "Moto Peças CE".
"""

import io
from datetime import date
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from PIL import Image

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.filiais import services as filiais
from apps.financeiro.models import Despesa
from apps.locacoes import leituras as locacoes_leituras
from apps.movimentacoes import leituras as movimentacoes_leituras
from apps.movimentacoes.models import LocalApoio, Movimentacao
from apps.plataforma.models import Empresa
from apps.veiculos import selectors as veiculos_selectors
from apps.veiculos.models import Categoria, DocumentoVeiculo, TransferenciaVeiculo, Veiculo

from .frota import montar_frota
from .test_t012_filiais import MotoRapida
from .test_t013_veiculos import _caucaia
from .test_t015_locacoes import Cenario

LISTA = "/api/movimentacoes/"


@pytest.fixture
def cenario(empresa_a, planos, relogio) -> Cenario:
    locacoes_leituras.registrar()
    movimentacoes_leituras.registrar()
    moto = MotoRapida(empresa_a, planos["Profissional"])
    return Cenario(moto, montar_frota(moto))


def _local(cenario: Cenario, nome: str, tipo: str, quem: str = "Rodrigo") -> int:
    resposta = cenario.moto.api(quem).post(
        f"{LISTA}locais/", {"nome": nome, "tipo": tipo}, format="json"
    )
    assert resposta.status_code == 201, resposta.json()
    return int(resposta.json()["id"])


def _veiculo(cenario: Cenario, placa: str) -> Veiculo:
    return Veiculo.objects.get(placa=placa)


def _corpo(cenario: Cenario, placa: str = "SAK1D39", **campos: Any) -> dict[str, Any]:
    return {
        "veiculo_id": _veiculo(cenario, placa).pk,
        "paradas": [],
        "destino_filial_id": cenario.frota.centro.pk,
        "categoria_destino_id": None,
        "levado_por_id": cenario.pessoas["João"].pk,
        "sair_agora": True,
        "agendada_para": None,
        "vistoria_rapida": False,
        **campos,
    }


def _criar(cenario: Cenario, quem: str = "Rodrigo", **campos: Any) -> Any:
    return cenario.moto.api(quem).post(LISTA, _corpo(cenario, **campos), format="json")


def _criada(cenario: Cenario, quem: str = "Rodrigo", **campos: Any) -> dict[str, Any]:
    resposta = _criar(cenario, quem, **campos)
    assert resposta.status_code == 201, resposta.json()
    return dict(resposta.json())


def _post(cenario: Cenario, quem: str, rota: str, corpo: Any = None, **extra: Any) -> Any:
    formato = extra.pop("format", "json")
    return cenario.moto.api(quem).post(f"{LISTA}{rota}", corpo or {}, format=formato)


def _lavagem(cenario: Cenario, valor: int = 3500) -> list[dict[str, Any]]:
    local = _local(cenario, "Lava Rápido Aldeota", "lava_jato")
    return [{"local_id": local, "servico": "Lavagem completa", "valor_previsto_centavos": valor}]


def _foto() -> SimpleUploadedFile:
    saida = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(saida, format="JPEG")
    return SimpleUploadedFile("foto.jpg", saida.getvalue(), content_type="image/jpeg")


def _pdf() -> SimpleUploadedFile:
    return SimpleUploadedFile("nota.pdf", b"%PDF-1.4 nota", content_type="application/pdf")


def _parada(dados: dict[str, Any]) -> int:
    return int(dados["paradas"][0]["id"])


def _passar_pela_parada(
    cenario: Cenario, mov: dict[str, Any], valor: int, quem: str = "João", nota: bool = True
) -> dict[str, Any]:
    parada = _parada(mov)
    chegou = _post(cenario, quem, f"{mov['id']}/paradas/{parada}/chegada/")
    assert chegou.status_code == 200, chegou.json()
    assert chegou.json()["status"] == "no_local"
    corpo: dict[str, Any] = {"valor_pago_centavos": valor}
    if nota:
        corpo["nota"] = _pdf()
    saiu = _post(cenario, quem, f"{mov['id']}/paradas/{parada}/saida/", corpo, format="multipart")
    assert saiu.status_code == 200, saiu.json()
    return dict(saiu.json())


# --- CA-246-01 a 03: ida ao lava-jato e volta ---


def test_mov_01_mov_03_ca_246_01_ida_ao_lava_jato(cenario):
    mov = _criada(cenario, paradas=_lavagem(cenario))
    assert (mov["codigo"], mov["status"]) == ("MOV-0001", "em_transito")
    assert mov["rota"] == "Centro → Lava Rápido Aldeota → Centro"
    assert (mov["km_saida"], mov["proxima_etapa"]) == (3120, f"parada:{_parada(mov)}")
    sak = _veiculo(cenario, "SAK1D39")
    assert sak.status == "em_movimentacao"
    assert sak.historico.last().origem_codigo == "MOV-0001"
    # Some da Nova locação e não pode ser reservado.
    resposta = cenario.criar(veiculo=sak)
    assert cenario.confirmar(resposta["id"]).status_code in (409, 422)
    ficha = cenario.moto.api("Rodrigo").get(f"/api/veiculos/{sak.pk}/").json()
    assert ficha["movimentacao_aberta"] == {
        "id": mov["id"],
        "codigo": "MOV-0001",
        "status": "em_transito",
        "rotulo": "Em movimentação",
        "tom": "info",
    }
    assert ficha["situacao"]["rotulo"] == "Em movimentação"
    assert ficha["acoes"]["movimentar"] is False
    assert ficha["acoes"]["motivo_movimentar"] == "O veículo já está na MOV-0001."
    assert (ficha["acoes"]["registrar_km"], ficha["acoes"]["transferir"]) == (False, False)
    assert ficha["movimentacoes"]["em_andamento"]["codigo"] == "MOV-0001"


def test_mov_04_fin_05_ca_246_02_parada_com_despesa(cenario):
    mov = _criada(cenario, paradas=_lavagem(cenario))
    saiu = _passar_pela_parada(cenario, mov, 3500)
    assert not [c for c in str(saiu).split("'") if c.endswith("_centavos")]  # USR-09
    saiu = cenario.moto.api("Rodrigo").get(f"{LISTA}{mov['id']}/").json()
    assert (saiu["status"], saiu["proxima_etapa"], saiu["custo_centavos"]) == (
        "em_transito",
        "destino",
        3500,
    )
    despesa = Despesa.objects.get(pk=saiu["paradas"][0]["despesa"]["id"])
    assert (despesa.valor_centavos, despesa.status, despesa.categoria) == (
        3500,
        "a_pagar",
        "outros",
    )
    assert despesa.veiculo_id == _veiculo(cenario, "SAK1D39").pk
    assert despesa.filial_id == cenario.frota.centro.pk
    assert (despesa.vencimento, despesa.data) == (date(2026, 10, 7), date(2026, 10, 7))
    assert despesa.descricao == "MOV-0001 · Lavagem completa · Lava Rápido Aldeota"
    assert (despesa.origem_tipo, despesa.origem_codigo) == ("movimentacao", "MOV-0001")
    lida = cenario.moto.api("Lúcia").get(f"/api/financeiro/despesas/{despesa.pk}/").json()
    assert lida["sem_nota"] is False
    assert lida["origem"] == {"tipo": "movimentacao", "id": mov["id"], "codigo": "MOV-0001"}


def test_mov_05_vei_01_ca_246_03_chegada_no_destino(cenario):
    mov = _criada(cenario, paradas=_lavagem(cenario))
    _passar_pela_parada(cenario, mov, 3500)
    menor = _post(cenario, "João", f"{mov['id']}/chegada/", {"km": 3100})
    assert menor.status_code == 422 and menor.json()["codigo"] == "VEI-01"
    chegou = _post(cenario, "João", f"{mov['id']}/chegada/", {"km": 3146})
    assert chegou.status_code == 200, chegou.json()
    assert chegou.json()["status"] == "concluida"
    assert chegou.json()["chegada"]["km"] == 3146
    sak = _veiculo(cenario, "SAK1D39")
    assert (sak.status, sak.km_atual) == ("disponivel", 3146)
    assert sak.leituras_km.last().origem_codigo == "MOV-0001"


# --- CA-246-04, 05, 06, 19: quem não se movimenta e a agendada ---


@pytest.mark.parametrize("placa", ["QXA4B21", "RHT9F02"])
def test_mov_03_ca_246_04_alugado_e_reservado_nao_se_movimentam(cenario, placa):
    resposta = _criar(cenario, placa=placa)
    assert resposta.status_code == 409 and resposta.json()["codigo"] == "MOV-03"


def test_mov_03_ca_246_04_uma_aberta_por_veiculo(cenario):
    _criada(cenario)
    segunda = _criar(cenario)
    assert segunda.status_code == 409
    assert segunda.json()["mensagem"] == "O veículo já está na MOV-0001."


def test_mov_03_ca_246_05_agendada_e_veiculo_reservado_no_meio(cenario):
    mov = _criada(cenario, sair_agora=False, agendada_para="2026-10-08T11:00:00Z")
    assert mov["status"] == "agendada"
    assert _veiculo(cenario, "SAK1D39").status == "disponivel"
    cenario.confirmada(inicio="2026-10-09T12:00:00Z")  # a Bruna reserva o SAK1D39
    iniciar = _post(cenario, "Rodrigo", f"{mov['id']}/iniciar/")
    assert iniciar.status_code == 409 and iniciar.json()["codigo"] == "MOV-03"
    assert Movimentacao.objects.get(pk=mov["id"]).status == "agendada"
    reagendada = cenario.moto.api("Rodrigo").patch(
        f"{LISTA}{mov['id']}/",
        {**_corpo(cenario), "agendada_para": "2026-10-10T11:00:00Z"},
        format="json",
    )
    assert reagendada.status_code == 200, reagendada.json()
    cancelada = _post(cenario, "Rodrigo", f"{mov['id']}/cancelar/", {"motivo": "Reservado"})
    assert cancelada.json()["status"] == "cancelada"
    de_novo = _post(cenario, "Rodrigo", f"{mov['id']}/cancelar/", {"motivo": "De novo"})
    assert de_novo.status_code == 409 and de_novo.json()["codigo"] == "transicao_movimentacao"


def test_mov_03_ca_246_06_depois_de_sair_nao_cancela(cenario):
    mov = _criada(cenario, paradas=_lavagem(cenario))
    assert mov["acoes"]["cancelar"] is False
    resposta = _post(cenario, "Rodrigo", f"{mov['id']}/cancelar/", {"motivo": "Desisti"})
    assert resposta.status_code == 409
    assert resposta.json()["detalhes"] == {"de": "em_transito", "para": "cancelada"}


def test_mov_03_ca_246_19_veiculo_com_retirada_hoje(cenario):
    locacao = cenario.confirmada()  # começa hoje: o SAK1D39 segue disponível
    assert _veiculo(cenario, "SAK1D39").status == "disponivel"
    resposta = _criar(cenario)
    assert resposta.status_code == 409
    assert resposta.json()["mensagem"] == f"O veículo está reservado na {locacao['codigo']}."
    ficha = cenario.moto.api("Rodrigo").get(f"/api/veiculos/{cenario.sak.pk}/").json()
    assert (
        ficha["acoes"]["motivo_movimentar"] == f"O veículo está reservado na {locacao['codigo']}."
    )


# --- CA-246-07, 08: oficina e despesa acima do limite ---


def test_mov_04_ca_246_07_oficina_mantem_em_manutencao(cenario):
    oficina = _local(cenario, "Moto Peças CE", "oficina")
    paradas = [
        {"local_id": oficina, "servico": "Troca do kit relação", "valor_previsto_centavos": 18000}
    ]
    mov = _criada(cenario, placa="PMZ3E17", paradas=paradas)
    assert mov["paradas"][0]["categoria"] == "manutencao"
    pmz = _veiculo(cenario, "PMZ3E17")
    assert pmz.status == "em_manutencao"
    lista = cenario.moto.api("Rodrigo").get("/api/veiculos/?em_movimentacao=true").json()
    assert [v["placa"] for v in lista["resultados"]] == ["PMZ3E17"]
    assert lista["resultados"][0]["movimentacao_aberta"]["rotulo"] == "Em movimentação"
    saiu = _passar_pela_parada(cenario, mov, 18000)
    despesa = Despesa.objects.get(pk=saiu["paradas"][0]["despesa"]["id"])
    assert (despesa.valor_centavos, despesa.status, despesa.categoria) == (
        18000,
        "a_pagar",
        "manutencao",
    )
    _post(cenario, "João", f"{mov['id']}/chegada/", {"km": pmz.km_atual + 5})
    assert _veiculo(cenario, "PMZ3E17").status == "em_manutencao"


def test_mov_04_apr_03_ca_246_08_despesa_acima_de_500(cenario):
    despachante = _local(cenario, "Despachante Rocha", "despachante")
    paradas = [
        {"local_id": despachante, "servico": "Licenciamento", "valor_previsto_centavos": 65000}
    ]
    mov = _criada(cenario, paradas=paradas)
    saiu = _passar_pela_parada(cenario, mov, 65000)
    despesa = Despesa.objects.get(pk=saiu["paradas"][0]["despesa"]["id"])
    assert despesa.status == "aguardando_aprovacao"
    assert PedidoAprovacao.objects.filter(pk=despesa.pedido_aprovacao_id, tipo="APR-03").exists()


# --- CA-246-09, 10: transferência e documento vencido ---


def test_mov_05_mov_06_vei_04_ca_246_09_transferencia_na_chegada(cenario):
    caucaia = _caucaia(cenario.moto, "Rodrigo")
    so_da_centro = Categoria.objects.create(
        nome="Street Centro", tipo_veiculo="moto", filial=cenario.frota.centro
    )
    Veiculo.objects.filter(placa="SAK1D39").update(categoria=so_da_centro)
    sem_categoria = _criar(cenario, paradas=_lavagem(cenario), destino_filial_id=caucaia.pk)
    assert sem_categoria.status_code == 400
    assert sem_categoria.json()["campos"]["categoria_destino_id"] == [
        "Escolha a categoria do veículo na Filial Caucaia."
    ]
    street = cenario.frota.categorias["Street 150–160"]
    local = LocalApoio.objects.get().pk
    mov = _criada(
        cenario,
        paradas=[
            {"local_id": local, "servico": "Lavagem completa", "valor_previsto_centavos": 3500}
        ],
        destino_filial_id=caucaia.pk,
        categoria_destino_id=street.pk,
    )
    assert (mov["transferencia"], mov["vistoria_rapida"]) == (True, True)
    assert mov["rota"] == "Centro → Lava Rápido Aldeota → Filial Caucaia"
    _passar_pela_parada(cenario, mov, 3500)

    rota = f"{mov['id']}/chegada/"
    faltando = _post(
        cenario, "João", rota, {"km": 3150, "recebido_por_id": cenario.pessoas["Rodrigo"].pk}
    )
    assert faltando.status_code == 400
    assert faltando.json()["campos"] == {
        "combustivel": ["Informe o combustível."],
        "fotos": ["Faltam 4 fotos."],
    }
    for posicao in ("frente", "traseira", "lado_esquerdo"):
        foto = _post(
            cenario,
            "João",
            f"{rota}fotos/",
            {"posicao": posicao, "arquivo": _foto()},
            format="multipart",
        )
        assert foto.status_code == 201, foto.json()
    tres = _post(
        cenario,
        "João",
        rota,
        {"km": 3150, "combustivel": "cheio", "recebido_por_id": cenario.pessoas["Rodrigo"].pk},
    )
    assert tres.json()["campos"] == {"fotos": ["Falta 1 foto."]}
    _post(
        cenario,
        "João",
        f"{rota}fotos/",
        {"posicao": "lado_direito", "arquivo": _foto()},
        format="multipart",
    )

    recebedores = cenario.moto.api("João").get(f"{LISTA}{mov['id']}/recebedores/").json()
    nomes = [p["nome"] for p in recebedores["resultados"]]
    assert "Lúcia" not in " ".join(nomes)  # o financeiro não recebe (T-302)
    lucia = _post(
        cenario,
        "João",
        rota,
        {"km": 3150, "combustivel": "cheio", "recebido_por_id": cenario.pessoas["Lúcia"].pk},
    )
    assert lucia.status_code == 400 and "recebido_por_id" in lucia.json()["campos"]

    chegou = _post(
        cenario,
        "João",
        rota,
        {"km": 3150, "combustivel": "cheio", "recebido_por_id": cenario.pessoas["Rodrigo"].pk},
    )
    assert chegou.status_code == 200, chegou.json()
    assert len(chegou.json()["chegada"]["fotos"]) == 4
    sak = _veiculo(cenario, "SAK1D39")
    assert (sak.status, sak.filial_id, sak.categoria_id) == ("disponivel", caucaia.pk, street.pk)
    transferencia = TransferenciaVeiculo.objects.get(veiculo=sak)
    assert (transferencia.filial_origem_id, transferencia.filial_destino_id) == (
        cenario.frota.centro.pk,
        caucaia.pk,
    )


def test_mov_05_vei_03_ca_246_10_documento_vencido_no_caminho(cenario, relogio):
    sak = _veiculo(cenario, "SAK1D39")
    DocumentoVeiculo.objects.create(veiculo=sak, tipo="crlv", validade=date(2026, 10, 8))
    mov = _criada(cenario)
    relogio.em("2026-10-08 09:00")
    chegou = _post(cenario, "João", f"{mov['id']}/chegada/", {"km": 3130})
    assert chegou.status_code == 200, chegou.json()
    sak.refresh_from_db()
    assert (sak.status, sak.motivo_status) == ("indisponivel", "CRLV vencido")


# --- CA-246-11, 17: quem pode ---


def test_mov_02_ca_246_11_quem_pode(cenario):
    assert _criar(cenario, "Bruna").status_code == 403
    assert _criar(cenario, "João").status_code == 403
    assert _criar(cenario, "Lúcia").status_code == 403
    mov = _criada(cenario, "Mariana", paradas=_lavagem(cenario))
    # Quem leva registra as chegadas; a Lúcia não.
    assert (
        _post(cenario, "Lúcia", f"{mov['id']}/paradas/{_parada(mov)}/chegada/").status_code == 403
    )
    assert _post(cenario, "João", f"{mov['id']}/paradas/{_parada(mov)}/chegada/").status_code == 200

    caucaia = _caucaia(cenario.moto)
    filiais.definir_filiais_do_usuario(cenario.pessoas["Rodrigo"].pk, [caucaia.pk])
    gerente_da_caucaia = _criar(cenario, "Rodrigo", placa="PMZ3E17")
    assert gerente_da_caucaia.status_code in (400, 403)


def test_mov_02_ca_246_17_quem_leva_acha_a_chegada(cenario, settings):
    settings.GIRO_MODULOS_ATIVOS = [*settings.GIRO_MODULOS_ATIVOS, "movimentacoes"]

    def menu(nome: str) -> list[str]:
        nav = cenario.moto.api(nome).get("/api/auth/eu/").json()["navegacao"]
        return [i["chave"] for g in nav["menu_completo"] for i in g["itens"]]

    assert "movimentacoes" not in menu("João")
    assert "movimentacoes" in menu("Rodrigo")
    mov = _criada(cenario)
    assert "movimentacoes" in menu("João")
    eu = cenario.moto.api("João").get("/api/auth/eu/").json()
    assert eu["pode"]["movimentacoes"] == "levar"
    quadro = cenario.moto.api("João").get(f"{LISTA}quadro/").json()
    em_transito = next(c for c in quadro["colunas"] if c["status"] == "em_transito")
    assert [i["codigo"] for i in em_transito["itens"]] == ["MOV-0001"]
    assert em_transito["itens"][0]["acoes"]["registrar_chegada"] is True
    assert cenario.moto.api("Bruna").get(f"{LISTA}{mov['id']}/").status_code == 404
    _post(cenario, "João", f"{mov['id']}/chegada/", {"km": 3130})
    assert "movimentacoes" not in menu("João")

    pessoas = (
        cenario.moto.api("Rodrigo")
        .get(f"{LISTA}pessoas/?filial={cenario.frota.centro.pk}")
        .json()["resultados"]
    )
    assert "financeiro" not in {p["perfil"] for p in pessoas}
    assert any(p["eu"] for p in pessoas)
    lucia = _criar(cenario, levado_por_id=cenario.pessoas["Lúcia"].pk)
    assert lucia.status_code == 400 and "levado_por_id" in lucia.json()["campos"]
    assert (
        cenario.moto.api("Bruna")
        .get(f"{LISTA}pessoas/?filial={cenario.frota.centro.pk}")
        .status_code
        == 403
    )
    assert cenario.moto.api("Rodrigo").get(f"{LISTA}pessoas/").status_code == 400


# --- CA-246-12, 13: ocupação e auditoria ---


def test_mov_03_vei_06_ca_246_12_ocupacao(cenario, relogio):
    sak = _veiculo(cenario, "SAK1D39")
    relogio.em("2026-10-07 00:00")
    _criada(cenario)
    relogio.em("2026-10-08 00:00")
    ocupacao = veiculos_selectors.ocupacao(sak, dias=1)
    assert ocupacao["pct"] == "0.00"


def test_mov_01_ca_246_13_auditoria(cenario):
    mov = _criada(cenario, paradas=_lavagem(cenario))
    _passar_pela_parada(cenario, mov, 0)
    _post(cenario, "João", f"{mov['id']}/chegada/", {"km": 3130})
    acoes = list(
        EventoAuditoria.objects.filter(objeto_id=mov["id"], acao__startswith="movimentacao.")
        .order_by("id")
        .values_list("acao", flat=True)
    )
    assert acoes == [
        "movimentacao.criar",
        "movimentacao.iniciar",
        "movimentacao.chegar_parada",
        "movimentacao.sair_parada",
        "movimentacao.concluir",
    ]
    criar = EventoAuditoria.objects.get(objeto_id=mov["id"], acao="movimentacao.criar")
    assert criar.objeto_codigo == "MOV-0001"
    assert criar.depois["veiculo_id"] == _veiculo(cenario, "SAK1D39").pk
    # Valor zero não gera despesa.
    assert Movimentacao.objects.get(pk=mov["id"]).paradas.get().despesa_id is None


# --- CA-246-14, 15: sem nota e locais de apoio ---


def test_mov_04_fin_06_ca_246_14_parada_sem_nota(cenario):
    mov = _criada(cenario, paradas=_lavagem(cenario))
    saiu = _passar_pela_parada(cenario, mov, 3500, nota=False)
    despesa_id = saiu["paradas"][0]["despesa"]["id"]
    assert saiu["paradas"][0]["despesa"]["sem_nota"] is True
    lucia = cenario.moto.api("Lúcia")
    assert lucia.get(f"/api/financeiro/despesas/{despesa_id}/").json()["sem_nota"] is True
    anexada = lucia.post(
        f"/api/financeiro/despesas/{despesa_id}/nota/", {"nota": _pdf()}, format="multipart"
    )
    assert anexada.status_code == 200, anexada.json()
    assert anexada.json()["sem_nota"] is False
    de_novo = lucia.post(
        f"/api/financeiro/despesas/{despesa_id}/nota/", {"nota": _pdf()}, format="multipart"
    )
    assert de_novo.status_code == 409 and de_novo.json()["codigo"] == "nota_existente"
    assert EventoAuditoria.objects.filter(acao="despesa.anexar_nota", objeto_id=despesa_id).exists()


def test_mov_01_ca_246_15_local_de_apoio(cenario):
    local = _local(cenario, "Lava Rápido Aldeota", "lava_jato")
    repetido = cenario.moto.api("Rodrigo").post(
        f"{LISTA}locais/", {"nome": "  lava rapido   ALDEOTA ", "tipo": "lava_jato"}, format="json"
    )
    assert repetido.status_code == 409
    assert repetido.json()["detalhes"] == {"local_id": local, "ativo": True}
    assert (
        cenario.moto.api("Bruna")
        .post(f"{LISTA}locais/", {"nome": "Outro", "tipo": "outro"}, format="json")
        .status_code
        == 403
    )
    mov = _criada(
        cenario, paradas=[{"local_id": local, "servico": "Lavagem", "valor_previsto_centavos": 0}]
    )
    assert _post(cenario, "Rodrigo", f"locais/{local}/inativar/").status_code == 403
    assert _post(cenario, "Mariana", f"locais/{local}/inativar/").json()["ativo"] is False
    ativos = cenario.moto.api("Rodrigo").get(f"{LISTA}locais/").json()["resultados"]
    assert ativos == []
    outro = _criar(cenario, placa="PMZ3E17", paradas=[{"local_id": local, "servico": "X"}])
    assert outro.status_code == 400 and "paradas[0].local_id" in outro.json()["campos"]
    lida = cenario.moto.api("Rodrigo").get(f"{LISTA}{mov['id']}/").json()
    assert lida["paradas"][0]["local"] == {
        "id": local,
        "nome": "Lava Rápido Aldeota",
        "tipo": "lava_jato",
        "ativo": False,
    }
    assert LocalApoio.objects.filter(pk=local).exists()


# --- CA-246-18: concluídas do quadro ---


def _em(cenario: Cenario, relogio: Any, quando: str) -> None:
    relogio.em(quando)
    cenario.moto._tokens.clear()  # o token de ontem já expirou


def test_mov_01_ca_246_18_concluidas_so_de_hoje(cenario, relogio):
    _em(cenario, relogio, "2026-10-06 09:00")
    ontem = _criada(cenario)
    _post(cenario, "João", f"{ontem['id']}/chegada/", {"km": 3125})
    _em(cenario, relogio, "2026-10-07 08:00")
    hoje = _criada(cenario)
    _em(cenario, relogio, "2026-10-07 08:30")
    _post(cenario, "João", f"{hoje['id']}/chegada/", {"km": 3130})

    def concluidas() -> dict[str, Any]:
        quadro = cenario.moto.api("Rodrigo").get(f"{LISTA}quadro/").json()
        return next(c for c in quadro["colunas"] if c["status"] == "concluida")

    coluna = concluidas()
    assert (coluna["total"], [i["codigo"] for i in coluna["itens"]]) == (1, ["MOV-0002"])
    lista = (
        cenario.moto.api("Rodrigo")
        .get(f"{LISTA}?status=concluida&periodo_inicio=2026-10-06&periodo_fim=2026-10-06")
        .json()
    )
    assert [m["codigo"] for m in lista["resultados"]] == ["MOV-0001"]
    _em(cenario, relogio, "2026-10-08 09:00")
    assert concluidas()["total"] == 0


# --- T-300: veículos movimentáveis; baixa recusada com movimentação aberta ---


def test_mov_03_movimentavel_exclui_alugado_e_reservado(cenario):
    _criada(cenario, placa="PMZ3E17")
    placas = {
        v["placa"]
        for v in cenario.moto.api("Rodrigo")
        .get("/api/veiculos/?movimentavel=true&tamanho=100")
        .json()["resultados"]
    }
    assert "SAK1D39" in placas
    assert not {"QXA4B21", "RHT9F02", "PMZ3E17"} & placas
    assert (
        cenario.moto.api("Bruna").get("/api/veiculos/?movimentavel=true").json()["resultados"] == []
    )


def _baixar(cenario: Cenario, placa: str = "SAK1D39") -> Any:
    sak = _veiculo(cenario, placa)
    return cenario.moto.api("Mariana").post(
        f"/api/veiculos/{sak.pk}/baixar/",
        {"motivo": "roubo", "descricao": "na BR-116"},
        format="json",
    )


def test_mov_03_baixa_cancela_movimentacao_iniciada(cenario):
    """T-310, T-311 (CA-246-22): sem 409; a iniciada vira cancelada e a despesa da parada fica."""
    mov = _criada(cenario, paradas=_lavagem(cenario))
    _passar_pela_parada(cenario, mov, 3500)
    ficha = cenario.moto.api("Mariana").get(f"/api/veiculos/{cenario.sak.pk}/").json()
    assert (ficha["acoes"]["baixar"], ficha["acoes"]["aviso_baixar"]) == (
        True,
        "A MOV-0001 será cancelada.",
    )
    resposta = _baixar(cenario)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["movimentacao_aberta"] is None
    cancelada = Movimentacao.objects.get(pk=mov["id"])
    assert (cancelada.status, cancelada.motivo_cancelamento) == (
        "cancelada",
        "Veículo baixado: roubo",
    )
    assert cancelada.paradas.get().despesa is not None
    evento = EventoAuditoria.objects.get(objeto_id=mov["id"], acao="movimentacao.cancelar")
    assert evento.motivo == "Veículo baixado: roubo"
    lida = cenario.moto.api("Rodrigo").get(f"{LISTA}{mov['id']}/").json()
    assert (lida["status"], lida["motivo_cancelamento"]) == ("cancelada", "Veículo baixado: roubo")
    assert lida["cancelada_em"] is not None


def test_mov_03_baixa_na_transferencia_nao_transfere(cenario):
    """CA-246-23: o veículo baixado fica na filial de saída, sem TransferenciaVeiculo."""
    caucaia = _caucaia(cenario.moto, "Rodrigo")
    mov = _criada(cenario, destino_filial_id=caucaia.pk)
    assert _baixar(cenario).status_code == 200
    sak = _veiculo(cenario, "SAK1D39")
    assert (sak.status, sak.filial_id) == ("baixado", cenario.frota.centro.pk)
    assert not TransferenciaVeiculo.objects.filter(veiculo=sak).exists()
    assert Movimentacao.objects.get(pk=mov["id"]).status == "cancelada"


def test_mov_03_baixa_cancela_agendada(cenario):
    mov = _criada(cenario, placa="PMZ3E17", sair_agora=False, agendada_para="2026-10-08T11:00:00Z")
    assert _baixar(cenario, "PMZ3E17").status_code == 200
    agendada = Movimentacao.objects.get(pk=mov["id"])
    assert (agendada.status, agendada.motivo_cancelamento) == (
        "cancelada",
        "Veículo baixado: roubo",
    )


def test_mov_03_falha_no_assinante_desfaz_a_baixa(cenario, monkeypatch):
    mov = _criada(cenario)

    def quebra(*_: Any, **__: Any) -> None:
        raise RuntimeError("falhou")

    monkeypatch.setattr("apps.movimentacoes.services.cancelar_pela_baixa", quebra)
    with pytest.raises(RuntimeError):
        _baixar(cenario)
    assert _veiculo(cenario, "SAK1D39").status == "em_movimentacao"
    assert Movimentacao.objects.get(pk=mov["id"]).status == "em_transito"


def test_mov_05_km_manual_recusado_em_movimentacao(cenario):
    _criada(cenario)
    sak = _veiculo(cenario, "SAK1D39")
    resposta = cenario.moto.api("João").post(
        f"/api/veiculos/{sak.pk}/km/", {"km": 3200}, format="json"
    )
    assert resposta.status_code == 409 and resposta.json()["codigo"] == "MOV-05"


def test_mov_isolamento_entre_empresas(cenario):
    _criada(cenario)
    _local(cenario, "Lava Rápido Aldeota", "lava_jato")
    assert Movimentacao.objects.count() == 1
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not Movimentacao.objects.exists()
    assert not LocalApoio.objects.exists()


def test_mov_05_aut_06_documento_vence_em_movimentacao(cenario):
    """MOV-05: no dia do vencimento, o veículo em movimentação não muda; os gerentes recebem a
    tarefa urgente, e a chegada decide."""
    from apps.veiculos import services as veiculos_services

    _criada(cenario)
    sak = _veiculo(cenario, "SAK1D39")
    DocumentoVeiculo.objects.create(veiculo=sak, tipo="crlv", validade=date(2026, 10, 7))
    contagem = veiculos_services.aplicar_vencimento_de_documentos(date(2026, 10, 7))
    assert (contagem["indisponiveis"], contagem["tarefas"]) == (0, 1)
    assert _veiculo(cenario, "SAK1D39").status == "em_movimentacao"
