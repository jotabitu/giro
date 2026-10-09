"""T-012 · Filiais (critérios em docs/qa/criterios/T-012.md).

Roda na `empresa_a` (host `empresa-a.localhost`) com o plano Profissional e as pessoas do seed.
"""

import threading
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.db import connection, connections

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.filiais import selectors, services
from apps.filiais.models import Filial, UsuarioFilial
from apps.plataforma.models import Empresa, UsoEmpresa
from comum import leituras
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens
from comum.erros import ErroDeRegra

from .apoio import FUSO
from .conftest import cliente

HOST = "empresa-a.localhost"
SP = ZoneInfo(FUSO)
DIA_UTIL = [{"abre": "08:00", "fecha": "18:00"}]
HORARIO_CENTRO: dict[str, Any] = {
    **{dia: DIA_UTIL for dia in ("seg", "ter", "qua", "qui", "sex")},
    "sab": [{"abre": "08:00", "fecha": "12:00"}],
    "dom": [],
}
CENTRO: dict[str, Any] = {
    "nome": "Filial Centro",
    "matriz": False,
    "cnpj": "12.345.678/0001-95",
    "endereco": {
        "cep": "60325-000",
        "logradouro": "Av. Bezerra de Menezes",
        "numero": "1200",
        "complemento": None,
        "bairro": "São Gerardo",
        "cidade": "Fortaleza",
        "uf": "CE",
    },
    "contato": {"telefone": "8532123344", "whatsapp": None, "email": "centro@motorapida.com.br"},
    "horario": HORARIO_CENTRO,
}
PESSOAS = {
    "Mariana": ("mariana@motorapida.com.br", "administrador"),
    "Rodrigo": ("rodrigo@motorapida.com.br", "gerente"),
    "Bruna": ("bruna@motorapida.com.br", "vendedor"),
    "João": ("joao@motorapida.com.br", "vistoriador"),
    "Lúcia": ("lucia@motorapida.com.br", "financeiro"),
}


def _filial(
    nome: str, cidade: str = "Caucaia", cep: str = "61600000", **extra: Any
) -> dict[str, Any]:
    return {
        **CENTRO,
        "nome": nome,
        "cnpj": None,
        "contato": None,
        "endereco": {**CENTRO["endereco"], "cidade": cidade, "cep": cep},
        **extra,
    }


def _momento(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=SP)


class MotoRapida:
    """A empresa de teste com o plano Profissional, as pessoas e (opcional) a Filial Centro."""

    def __init__(self, empresa: Empresa, profissional: Any) -> None:
        empresa.plano = profissional
        empresa.save(update_fields=["plano"])
        UsoEmpresa.objects.update_or_create(empresa=empresa, defaults={"filiais": 0})
        self.empresa = empresa
        self.pessoas = {
            nome: Usuario.objects.create_user(email, "senha-forte-123", nome=nome, perfil=perfil)
            for nome, (email, perfil) in PESSOAS.items()
        }
        self._tokens: dict[str, str] = {}

    def api(self, nome: str = "Mariana", **cabecalhos: str):
        if nome not in self._tokens:
            # Como quem já passou pelas 2 etapas (o login é testado na T-011).
            refresh = emitir_tokens(self.pessoas[nome], AMR_SENHA_E_CODIGO)
            self._tokens[nome] = str(refresh.access_token)
        api = cliente(HOST, self._tokens[nome])
        if cabecalhos:
            api.credentials(HTTP_AUTHORIZATION=f"Bearer {self._tokens[nome]}", **cabecalhos)
        return api

    def criar(self, dados: dict[str, Any], nome: str = "Mariana"):
        return self.api(nome).post("/api/filiais/", dados, format="json")

    def centro(self) -> Filial:
        resposta = self.criar(CENTRO)
        assert resposta.status_code == 201, resposta.json()
        filial = Filial.objects.get(pk=resposta.json()["id"])
        for nome in ("Rodrigo", "Bruna", "João", "Lúcia"):
            services.definir_filiais_do_usuario(self.pessoas[nome].pk, [filial.pk])
        return filial

    def plano(self) -> dict[str, Any]:
        return self.api().get("/api/filiais/").json()["plano"]


@pytest.fixture
def moto(empresa_a, planos) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


# --- Cadastro ---


def test_fil_01_ca_012_01_primeira_filial_e_matriz(moto):
    resposta = moto.criar(CENTRO)
    assert resposta.status_code == 201
    assert resposta.json()["matriz"] is True
    filial = Filial.objects.get(pk=resposta.json()["id"])
    assert UsuarioFilial.objects.filter(usuario=moto.pessoas["Mariana"], filial=filial).exists()
    assert "filial" in UsoEmpresa.objects.get(empresa=moto.empresa).passos_implantacao


def test_fil_01_ca_012_02_representacao(moto):
    centro = moto.centro()
    corpo = moto.api().get(f"/api/filiais/{centro.pk}/").json()
    assert corpo["horario_resumo"] == "seg a sex 8h–18h · sáb 8h–12h"
    assert corpo["endereco_resumo"] == "Av. Bezerra de Menezes, 1200 · Fortaleza, CE"
    assert [g["nome"] for g in corpo["gerentes"]] == ["Rodrigo"]
    assert corpo["cnpj"] == "12345678000195"
    assert set(corpo) == {
        "id",
        "nome",
        "matriz",
        "ativo",
        "cnpj",
        "inscricao_estadual",
        "inscricao_municipal",
        "endereco",
        "contato",
        "preco_litro_centavos",
        "horario",
        "horario_resumo",
        "endereco_resumo",
        "gerentes",
        "feriados_proximos",
        "feriados_ano_seguinte_pendentes",
        "criado_em",
    }  # sem vagas, tabela de preço, conta de recebimento, centro de custo, nota, frota, status


def test_plt_03_ca_012_03_uso_do_plano_na_lista(moto):
    moto.centro()
    assert moto.plano() == {
        "usado": 1,
        "limite": 3,
        "aviso": False,
        "bloqueado": False,
        "nome_plano": "Profissional",
    }


def test_plt_03_ca_012_04_segunda_e_terceira_filial_ate_o_limite(moto):
    moto.centro()
    assert moto.criar(_filial("Filial Caucaia")).status_code == 201
    assert (moto.plano()["usado"], moto.plano()["aviso"]) == (2, False)
    assert moto.criar(_filial("Filial Messejana", "Fortaleza", "60840280")).status_code == 201
    plano = moto.plano()
    assert (plano["usado"], plano["aviso"], plano["bloqueado"]) == (3, True, True)

    aldeota = moto.criar(_filial("Filial Aldeota", "Fortaleza"))
    assert aldeota.status_code == 422
    assert aldeota.json()["codigo"] == "PLT-03"
    assert aldeota.json()["detalhes"] == {"item": "filiais", "usado": 3, "limite": 3}
    assert (
        aldeota.json()["mensagem"]
        == "Seu plano permite até 3 filiais. Para abrir outra, mude de plano."
    )
    assert not Filial.objects.filter(nome="Filial Aldeota").exists()
    assert moto.plano()["usado"] == 3


def test_fil_01_ca_012_05_nome_unico_sem_diferenca_de_maiusculas(moto):
    moto.centro()
    resposta = moto.criar(_filial("filial centro"))
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "filial_nome_em_uso"


def test_fil_01_ca_012_06_validacoes(moto):
    moto.centro()
    sem_domingo = {k: v for k, v in HORARIO_CENTRO.items() if k != "dom"}
    casos = {
        "cnpj com dígito errado": _filial("A", cnpj="12.345.678/0002-00"),
        "cep com 7 dígitos": _filial("B", cep="6032500"),
        "uf XX": _filial("C", endereco={**CENTRO["endereco"], "uf": "XX"}),
        "horário sem domingo": _filial("D", horario=sem_domingo),
        "segunda invertida": _filial(
            "E", horario={**HORARIO_CENTRO, "seg": [{"abre": "18:00", "fecha": "08:00"}]}
        ),
        "sábado com 3 intervalos": _filial(
            "F",
            horario={
                **HORARIO_CENTRO,
                "sab": [
                    {"abre": "07:00", "fecha": "08:00"},
                    {"abre": "09:00", "fecha": "10:00"},
                    {"abre": "11:00", "fecha": "12:00"},
                ],
            },
        ),
        "intervalos sobrepostos": _filial(
            "G",
            horario={
                **HORARIO_CENTRO,
                "ter": [{"abre": "08:00", "fecha": "12:00"}, {"abre": "11:00", "fecha": "14:00"}],
            },
        ),
    }
    for caso, dados in casos.items():
        resposta = moto.criar(dados)
        assert resposta.status_code == 400, caso
        assert resposta.json()["codigo"] == "validacao", caso
    assert Filial.objects.count() == 1

    sem_opcionais = _filial("Filial Caucaia", cnpj=None, contato=None)
    assert moto.criar(sem_opcionais).status_code == 201
    assert (
        moto.criar(
            {k: v for k, v in _filial("Filial Messejana").items() if k not in ("cnpj", "contato")}
        ).status_code
        == 201
    )


def test_fil_01_ca_012_07_uma_matriz_so(moto):
    centro = moto.centro()
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])
    resposta = moto.api().post(f"/api/filiais/{caucaia.pk}/tornar-matriz/")
    assert resposta.status_code == 200
    assert resposta.json()["matriz"] is True
    centro.refresh_from_db()
    assert centro.matriz is False
    assert Filial.objects.filter(matriz=True).count() == 1

    services.desativar(centro, "Teste")
    inativa = moto.api().post(f"/api/filiais/{centro.pk}/tornar-matriz/")
    assert inativa.status_code == 422
    assert inativa.json()["codigo"] == "filial_inativa"


def _em_outra_conexao(funcao):
    erros: list[BaseException] = []

    def rodar() -> None:
        try:
            connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
            funcao()
        except BaseException as erro:  # devolvido ao teste
            erros.append(erro)
        finally:
            connections.close_all()

    thread = threading.Thread(target=rodar)
    thread.start()
    return thread, erros


def test_fil_01_ca_012_07_duas_chamadas_simultaneas_nunca_deixam_duas_matrizes(empresa_a):
    """Conexões próprias, fora da transação do teste; as filiais criadas aqui são apagadas."""
    ids: list[int] = []
    matrizes: list[int] = []

    def preparar() -> None:
        for nome, matriz in (
            ("Concorrência A", True),
            ("Concorrência B", False),
            ("Concorrência C", False),
        ):
            ids.append(
                Filial.objects.create(
                    nome=nome, matriz=matriz, cep="60325000", logradouro="Rua", numero="1",
                    bairro="Centro", cidade="Fortaleza", uf="CE", horario=HORARIO_CENTRO,
                ).pk
            )  # fmt: skip

    def tornar(pk: int):
        return lambda: services.tornar_matriz(Filial.objects.get(pk=pk))

    def contar_e_apagar() -> None:
        matrizes.extend(Filial.objects.filter(pk__in=ids, matriz=True).values_list("pk", flat=True))
        Filial.objects.filter(pk__in=ids).delete()

    if Filial.objects.exists():
        pytest.skip("empresa_a precisa começar sem filiais gravadas")
    thread, erros = _em_outra_conexao(preparar)
    thread.join(timeout=20)
    assert not erros, erros
    try:
        corridas = [_em_outra_conexao(tornar(ids[1])), _em_outra_conexao(tornar(ids[2]))]
        for corrida, _ in corridas:
            corrida.join(timeout=20)
        assert not [e for _, lista in corridas for e in lista]
    finally:
        thread, erros = _em_outra_conexao(contar_e_apagar)
        thread.join(timeout=20)
        assert not erros, erros
    assert len(matrizes) == 1
    assert matrizes[0] in ids[1:]


# --- Feriados (FIL-03) ---


def test_fil_03_ca_012_08_feriados_nacionais_sugeridos(moto):
    centro = moto.centro()
    api = moto.api()
    sugestoes = api.get(f"/api/filiais/{centro.pk}/feriados/sugestoes/?ano=2026").json()
    datas = {s["data"]: s["nome"] for s in sugestoes["resultados"]}
    for data in ("2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20", "2026-12-25"):
        assert data in datas
    assert datas["2026-10-12"] == "Nossa Senhora Aparecida"

    # Nada vale antes da confirmação.
    assert api.get(f"/api/filiais/{centro.pk}/feriados/?ano=2026").json()["resultados"] == []
    assert selectors.esta_aberta(centro, _momento("2026-10-12 10:00")) is True

    confirmados = [
        {"data": s["data"], "nome": s["nome"], "origem": "nacional"}
        for s in sugestoes["resultados"]
    ]
    local = {"data": "2026-08-15", "nome": "Nossa Senhora da Assunção", "origem": "local"}
    resposta = api.post(
        f"/api/filiais/{centro.pk}/feriados/", {"feriados": [*confirmados, local]}, format="json"
    )
    assert resposta.status_code == 201
    datas_confirmadas = {f["data"] for f in resposta.json()["resultados"]}
    assert {"2026-10-12", "2026-08-15"} <= datas_confirmadas

    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])
    assert api.get(f"/api/filiais/{caucaia.pk}/feriados/?ano=2026").json()["resultados"] == []


def test_fil_03_ca_012_09_feriado_conta_como_fechado(moto):
    centro = moto.centro()
    services.confirmar_feriados(
        centro,
        [{"data": date(2026, 10, 12), "nome": "Nossa Senhora Aparecida", "origem": "nacional"}],
    )  # fmt: skip
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])

    assert selectors.esta_aberta(centro, _momento("2026-10-12 10:00")) is False
    assert selectors.proxima_abertura(centro, _momento("2026-10-10 12:30")) == _momento(
        "2026-10-13 08:00"
    )
    assert selectors.esta_aberta(caucaia, _momento("2026-10-12 10:00")) is True


def test_fil_02_ca_012_10_horario_normal(moto):
    centro = moto.centro()
    assert selectors.esta_aberta(centro, _momento("2026-10-10 11:59")) is True
    assert selectors.esta_aberta(centro, _momento("2026-10-10 12:00")) is False
    for hora in ("00:00", "09:00", "15:00", "23:59"):
        assert selectors.esta_aberta(centro, _momento(f"2026-10-11 {hora}")) is False
    assert selectors.esta_aberta(centro, _momento("2026-10-07 18:30")) is False
    assert selectors.proxima_abertura(centro, _momento("2026-10-07 18:30")) == _momento(
        "2026-10-08 08:00"
    )


# --- Escopo de filial (USR-07) ---


def test_usr_07_ca_012_11_seletor_de_filial(moto):
    centro = moto.centro()
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])

    mariana = moto.api().get("/api/filiais/minhas/").json()
    assert [f["nome"] for f in mariana["resultados"]] == ["Filial Centro", "Filial Caucaia"]
    assert mariana["pode_escolher_todas"] is True

    rodrigo = moto.api("Rodrigo").get("/api/filiais/minhas/").json()
    assert [f["nome"] for f in rodrigo["resultados"]] == ["Filial Centro"]
    assert rodrigo["pode_escolher_todas"] is False

    outra = moto.api("Rodrigo", HTTP_X_FILIAL=str(caucaia.pk)).get("/api/filiais/minhas/")
    assert outra.status_code == 403
    assert outra.json()["codigo"] == "USR-07"
    assert outra.json()["mensagem"] == "Você não tem acesso a esta filial"
    todas = moto.api("Rodrigo", HTTP_X_FILIAL="todas").get("/api/filiais/minhas/")
    assert (todas.status_code, todas.json()["codigo"]) == (403, "USR-07")
    assert moto.api("Mariana", HTTP_X_FILIAL="todas").get("/api/filiais/minhas/").status_code == 200

    sem_cabecalho = SimpleNamespace(META={}, user=moto.pessoas["Rodrigo"])
    assert selectors.filial_da_requisicao(sem_cabecalho) == centro


def test_usr_07_ca_012_12_so_o_administrador_administra_filiais(moto):
    centro = moto.centro()
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])
    for nome in ("Rodrigo", "Bruna", "João", "Lúcia"):
        api = moto.api(nome)
        assert api.get("/api/filiais/").status_code == 403, nome
        assert api.post("/api/filiais/", _filial("X"), format="json").status_code == 403, nome
        assert (
            api.patch(f"/api/filiais/{centro.pk}/", {"nome": "Y"}, format="json").status_code == 403
        ), nome
        for acao in ("desativar", "reativar"):
            resposta = api.post(
                f"/api/filiais/{caucaia.pk}/{acao}/", {"motivo": "x"}, format="json"
            )
            assert resposta.status_code == 403, (nome, acao)
        # O financeiro vê todas as filiais ativas (USR-07, T-067); os outros, só as suas.
        fora_do_escopo = 200 if nome == "Lúcia" else 404
        assert api.get(f"/api/filiais/{caucaia.pk}/").status_code == fora_do_escopo, nome
        assert api.get(f"/api/filiais/{centro.pk}/").status_code == 200, nome


# --- Desativar e reativar (FIL-06) ---


@pytest.fixture
def operacao():
    """Contadores falsos de operação por filial, como os que veiculos, locacoes e financeiro
    vão registrar em comum.leituras."""
    valores: dict[str, dict[int, int]] = {}
    reais = dict(leituras._contadores[selectors.ALVO])  # o de veículos é da T-013

    def registrar(nome: str, por_filial: dict[int, int]) -> None:
        valores[nome] = por_filial

        def contar(filial_id: int) -> int:
            return valores[nome].get(filial_id, 0)

        leituras.registrar_contador(selectors.ALVO, nome, contar)

    yield registrar
    for nome in valores:
        leituras.remover_contador(selectors.ALVO, nome)
        if nome in reais:
            leituras.registrar_contador(selectors.ALVO, nome, reais[nome])


def test_fil_06_ca_012_13_matriz_e_ultima_filial_nao_desativam(moto, operacao):
    centro = moto.centro()
    resposta = moto.api().post(
        f"/api/filiais/{centro.pk}/desativar/", {"motivo": "Teste"}, format="json"
    )
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "FIL-06"
    assert resposta.json()["detalhes"]["matriz"] is True

    Filial.objects.filter(pk=centro.pk).update(matriz=False)  # impossível pela API
    centro.refresh_from_db()
    with pytest.raises(ErroDeRegra) as erro:
        services.desativar(centro, "Teste")
    assert erro.value.detalhes is not None
    assert erro.value.detalhes["ultima_filial"] is True
    Filial.objects.filter(pk=centro.pk).update(matriz=True)

    moto.criar(_filial("Filial Caucaia"))
    operacao("veiculos", {centro.pk: 3})
    resposta = moto.api().post(
        f"/api/filiais/{centro.pk}/desativar/", {"motivo": "Teste"}, format="json"
    )
    assert resposta.json()["detalhes"] == {
        "matriz": True,
        "ultima_filial": False,
        "operacao": {"veiculos": 3, "locacoes": 0, "caixas": 0},
    }


def test_fil_06_ca_012_14_filial_sem_operacao_desativa(moto):
    moto.centro()
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])
    services.definir_filiais_do_usuario(moto.pessoas["Bruna"].pk, [caucaia.pk])
    api = moto.api()

    resposta = api.post(
        f"/api/filiais/{caucaia.pk}/desativar/", {"motivo": "Ponto fechado"}, format="json"
    )
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False
    for nome in ("Mariana", "Bruna", "Rodrigo"):
        minhas = moto.api(nome).get("/api/filiais/minhas/").json()["resultados"]
        assert caucaia.pk not in [f["id"] for f in minhas], nome
    assert api.get("/api/assinatura/").json()["uso"]["filiais"]["usado"] == 1
    assert UsuarioFilial.objects.filter(usuario=moto.pessoas["Bruna"], filial=caucaia).exists()
    evento = EventoAuditoria.objects.get(acao="filial.desativar", objeto_id=caucaia.pk)
    assert (evento.ator_nome, evento.motivo) == ("Mariana", "Ponto fechado")
    assert evento.ocorrido_em is not None

    reativada = api.post(
        f"/api/filiais/{caucaia.pk}/reativar/", {"motivo": "Reabriu"}, format="json"
    )
    assert reativada.status_code == 200
    assert api.get("/api/assinatura/").json()["uso"]["filiais"]["usado"] == 2

    api.post(f"/api/filiais/{caucaia.pk}/desativar/", {"motivo": "De novo"}, format="json")
    moto.criar(_filial("Filial Messejana", "Fortaleza"))
    moto.criar(_filial("Filial Aldeota", "Fortaleza"))
    cheio = api.post(f"/api/filiais/{caucaia.pk}/reativar/", {"motivo": "Volta"}, format="json")
    assert cheio.status_code == 422
    assert cheio.json()["codigo"] == "PLT-03"


def test_fil_06_ca_012_15_filial_com_operacao_nao_desativa(moto, operacao):
    moto.centro()
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])
    api = moto.api()

    def desativar():
        return api.post(f"/api/filiais/{caucaia.pk}/desativar/", {"motivo": "x"}, format="json")

    for grupo, quantos in (("veiculos", 31), ("locacoes", 1), ("caixas", 1)):
        operacao(grupo, {caucaia.pk: quantos})
        resposta = desativar()
        assert resposta.status_code == 422, grupo
        assert resposta.json()["codigo"] == "FIL-06"
        assert resposta.json()["detalhes"]["operacao"][grupo] == quantos
        operacao(grupo, {})  # só vendido/baixado, encerrada/cancelada, caixa fechado

    assert desativar().status_code == 200


def test_fil_06_ca_012_16_contas_em_aberto_nao_impedem(moto, operacao):
    moto.centro()
    caucaia = Filial.objects.get(pk=moto.criar(_filial("Filial Caucaia")).json()["id"])
    # Conta a receber de R$ 299,40 em aberto: não é grupo de operação do FIL-06.
    operacao("contas_receber_abertas", {caucaia.pk: 29940})
    resposta = moto.api().post(
        f"/api/filiais/{caucaia.pk}/desativar/", {"motivo": "Ponto fechado"}, format="json"
    )
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False


# --- CEP ---


def test_fil_02_ca_012_17_busca_de_cep(moto):
    for nome in PESSOAS:
        resposta = moto.api(nome).get("/api/enderecos/cep/60325000/")
        assert resposta.status_code == 200, nome
        assert resposta.json() == {
            "cep": "60325000",
            "logradouro": "Av. Bezerra de Menezes",
            "bairro": "São Gerardo",
            "cidade": "Fortaleza",
            "uf": "CE",
        }
    desconhecido = moto.api("Bruna").get("/api/enderecos/cep/99999999/")
    assert desconhecido.status_code == 404
    assert desconhecido.json()["codigo"] == "cep_nao_encontrado"
    assert desconhecido.json()["mensagem"] == "Não achamos esse CEP. Preencha o endereço à mão."
