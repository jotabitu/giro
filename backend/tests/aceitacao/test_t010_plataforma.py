"""T-010 · Plataforma, planos, empresas (critérios em docs/qa/criterios/T-010.md)."""

import re
import threading
import time
from datetime import date, timedelta
from io import StringIO
from typing import Any

import pytest
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection, connections, transaction
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_tenants.utils import tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Convite, Usuario
from apps.plataforma import selectors
from apps.plataforma.models import Empresa, Plano, UsoEmpresa
from apps.plataforma.services import (
    Administrador,
    atualizar_uso,
    endereco_de_acesso,
    exigir_limite,
)
from comum.auditoria import Ator, TipoAtor, usar_ator
from comum.autenticacao import COOKIE_REFRESH, emitir_tokens
from comum.erros import Conflito, ErroDeValidacao, LimiteDoPlano

from .apoio import PLANOS_SEED
from .conftest import (
    CNPJ_MOTO_RAPIDA,
    HOST_PLATAFORMA,
    SENHA,
    cliente,
    codigo_atual,
    entrar,
    liberar_codigo,
)

ENTRAR = "/api/plataforma/auth/entrar/"
OUTRO_CNPJ = "11.222.333/0001-81"


def _schemas() -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT nspname FROM pg_namespace")
        return {linha[0] for linha in cursor.fetchall()}


def _usar_plano(empresa, plano, **uso):
    """Plano e uso no public para uma empresa de teste já existente."""
    empresa.plano = plano
    empresa.save(update_fields=["plano"])
    UsoEmpresa.objects.update_or_create(empresa=empresa, defaults=uso)


def _usuario_da_empresa(email="vendedor@a.com", perfil="vendedor"):
    return Usuario.objects.create_user(email, "senha-forte-123", nome=email, perfil=perfil)


# --- Planos ---


def test_plt_03_ca_010_01_tres_planos_do_seed(equipe):
    token = entrar(*equipe["Diego Santos"])
    resposta = cliente(HOST_PLATAFORMA, token).get("/api/plataforma/planos/")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["proximo"] is None and corpo["anterior"] is None
    planos = {p["nome"]: p for p in corpo["resultados"]}
    assert list(planos) == ["Essencial", "Profissional", "Completo"]
    for nome, esperado in PLANOS_SEED.items():
        plano: dict[str, Any] = planos[nome]
        valores: Any = esperado
        assert plano["preco_mensal_centavos"] == valores["mensal"]
        assert plano["preco_anual_centavos"] == valores["anual"]
        assert plano["meses_cobrados_no_anual"] == 10
        assert plano["limite_veiculos"] == valores["veiculos"]
        assert plano["limite_filiais"] == valores["filiais"]
        assert plano["limite_usuarios"] == valores["usuarios"]


# --- Criação da empresa ---


def test_plt_01_ca_010_02_moto_rapida_nasce_em_teste(
    criar_empresa, relogio, equipe, django_capture_on_commit_callbacks, settings
):
    dono = equipe["Você"][0]
    with django_capture_on_commit_callbacks(execute=False) as depois_do_commit:
        with usar_ator(Ator(tipo=TipoAtor.USUARIO, id=dono.pk, nome=dono.nome)):
            empresa = criar_empresa()
        assert mail.outbox == []  # nada sai antes do commit

    empresa.refresh_from_db()
    assert empresa.status == "em_teste"
    assert (empresa.teste_inicio, empresa.teste_fim) == (date(2026, 10, 7), date(2026, 10, 21))
    assert selectors.dias_restantes(empresa) == 14
    assert empresa.preco_contratado_centavos == 44900
    assert empresa.ciclo == "mensal"
    assert empresa.schema_name == "motorapida"
    assert "motorapida" in _schemas()
    assert empresa.domains.get().domain == f"motorapida.{settings.DOMINIO_BASE}"
    settings.DOMINIO_BASE = "girolocadoras.com.br"
    assert endereco_de_acesso(empresa.subdominio) == "motorapida.girolocadoras.com.br"
    settings.DOMINIO_BASE = "localhost"

    with tenant_context(empresa):  # migrações aplicadas: as tabelas da empresa existem
        mariana = Usuario.objects.get(email="mariana@motorapida.com.br")
        convite = Convite.objects.get(usuario=mariana)
        assert (mariana.nome, mariana.perfil, mariana.status) == (
            "Mariana Costa",
            "administrador",
            "convite_pendente",
        )
        assert not mariana.has_usable_password()
        assert convite.expira_em - relogio.agora == timedelta(days=7)

    detalhe = selectors.detalhe_empresa(selectors.com_situacao().get(pk=empresa.pk))
    passos = {p["passo"]: p["concluido_em"] for p in detalhe["implantacao"]["passos"]}
    assert passos["conta"] is None  # só conclui quando Mariana criar a senha (T-011)
    assert detalhe["uso"]["usuarios"]["usado"] == 1  # o convite pendente conta (USR-01)

    evento = EventoAuditoria.objects.get(acao="empresa.criar", objeto_id=empresa.pk)
    assert (evento.ator_nome, evento.ator_id, evento.regra) == ("Você", dono.pk, "PLT-01")

    for callback in depois_do_commit:
        callback()
    connection.set_schema_to_public()
    assert [m.to for m in mail.outbox] == [["mariana@motorapida.com.br"]]
    assert "https://motorapida.localhost/convite/" in mail.outbox[0].body


def test_plt_01_ca_010_02_falha_nao_deixa_schema_nem_email(
    criar_empresa, monkeypatch, django_capture_on_commit_callbacks
):
    from apps.contas import services as contas

    original = contas._enviar_depois_do_commit

    def enviar_e_falhar(convite):
        original(convite)
        raise RuntimeError("falha depois do convite")

    monkeypatch.setattr(contas, "_enviar_depois_do_commit", enviar_e_falhar)
    with (
        django_capture_on_commit_callbacks(execute=True) as depois_do_commit,
        pytest.raises(RuntimeError),
    ):
        criar_empresa(subdominio="falhou")
    connection.set_schema_to_public()
    assert depois_do_commit == []
    assert mail.outbox == []
    assert "falhou" not in _schemas()
    assert not Empresa.objects.filter(subdominio="falhou").exists()


def test_plt_01_ca_010_03_vencimento_da_primeira_fatura(criar_empresa):
    empresa = criar_empresa()
    assert empresa.primeira_cobranca == date(2026, 10, 22)
    detalhe = selectors.detalhe_empresa(selectors.com_situacao().get(pk=empresa.pk))
    assert detalhe["faturas_recentes"] == []


def test_plt_01_ca_010_04_subdominio_e_cnpj_unicos(criar_empresa):
    criar_empresa()
    antes = _schemas()

    with pytest.raises(Conflito) as erro:
        criar_empresa(subdominio="motorapida", cnpj=OUTRO_CNPJ)
    assert (erro.value.status_http, erro.value.codigo) == (409, "subdominio_em_uso")
    with pytest.raises(Conflito) as conflito:
        criar_empresa(subdominio="outra", cnpj=CNPJ_MOTO_RAPIDA)
    assert (conflito.value.status_http, conflito.value.codigo) == (409, "cnpj_em_uso")

    invalidos = ["admin", "www", "api", "app", "suporte", "status", "Moto_Rapida", "mr", "x" * 31]
    for subdominio in invalidos:
        with pytest.raises(ErroDeValidacao) as invalido:
            criar_empresa(subdominio=subdominio, cnpj=OUTRO_CNPJ)
        assert (invalido.value.status_http, invalido.value.codigo) == (400, "validacao")
        assert "subdominio" in invalido.value.campos, subdominio

    with pytest.raises(ErroDeValidacao) as invalido:
        criar_empresa(subdominio="outra", cnpj="12.345.678/0001-11")
    assert invalido.value.campos == {"cnpj": ["CNPJ inválido"]}
    assert _schemas() == antes


def test_plt_01_ca_010_05_isolamento_entre_empresas(criar_empresa):
    moto_rapida = criar_empresa()
    outra = criar_empresa(
        subdominio="outra",
        cnpj=OUTRO_CNPJ,
        nome_exibicao="Outra",
        administrador=Administrador(nome="Ana", email="ana@outra.com.br"),
    )
    with tenant_context(moto_rapida):
        rodrigo = _usuario_da_empresa("rodrigo@motorapida.com.br", "gerente")
        token = str(emitir_tokens(rodrigo).access_token)
    with tenant_context(outra):
        assert not Usuario.objects.filter(email="rodrigo@motorapida.com.br").exists()
        assert not Usuario.objects.filter(email="mariana@motorapida.com.br").exists()

    assert cliente("motorapida.localhost", token).get("/api/assinatura/").status_code == 200
    resposta = cliente("outra.localhost", token).get("/api/assinatura/")
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


# --- Uso do plano e limites ---


def test_plt_03_ca_010_06_uso_da_moto_rapida_sem_aviso(empresa_a, planos):
    _usar_plano(empresa_a, planos["Profissional"], veiculos=86, filiais=1, usuarios=5)
    token = str(emitir_tokens(_usuario_da_empresa()).access_token)
    resposta = cliente("empresa-a.localhost", token).get("/api/assinatura/")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert {item: (u["usado"], u["limite"]) for item, u in corpo["uso"].items()} == {
        "veiculos": (86, 150),
        "filiais": (1, 3),
        "usuarios": (5, 10),
    }
    assert not any(u["aviso"] or u["bloqueado"] for u in corpo["uso"].values())
    assert corpo["somente_leitura"] is False
    assert corpo["faixa_aviso"] is None


def test_plt_03_ca_010_07_aviso_em_90_por_cento(
    empresa_a, planos, relogio, django_capture_on_commit_callbacks
):
    _usuario_da_empresa("mariana@a.com", "administrador")
    _usuario_da_empresa("bruna@a.com", "vendedor")
    _usar_plano(empresa_a, planos["Profissional"], veiculos=134)
    assert selectors.uso_do_plano(empresa_a)["veiculos"]["aviso"] is False

    with django_capture_on_commit_callbacks(execute=True):
        atualizar_uso("veiculos", 1)
    uso = selectors.uso_do_plano(empresa_a)["veiculos"]
    assert (uso["usado"], uso["aviso"], uso["bloqueado"]) == (135, True, False)
    assert [m.to for m in mail.outbox] == [["mariana@a.com"]]
    assert "limite do plano em 90%" in mail.outbox[0].subject
    connection.set_tenant(empresa_a)  # a tarefa eager volta a conexão ao public no fim

    with django_capture_on_commit_callbacks(execute=True):
        atualizar_uso("veiculos", 1)
    assert selectors.uso_do_plano(empresa_a)["veiculos"]["usado"] == 136
    assert len(mail.outbox) == 1  # mesmo mês: não avisa de novo

    _usar_plano(empresa_a, planos["Essencial"], veiculos=27)
    assert selectors.uso_do_plano(empresa_a)["veiculos"]["aviso"] is True


def test_plt_03_ca_010_08_bloqueio_em_100_por_cento_so_de_cadastro_novo(empresa_a, planos):
    _usar_plano(empresa_a, planos["Profissional"], veiculos=150, filiais=3)
    with pytest.raises(LimiteDoPlano) as erro:
        exigir_limite("veiculos")
    assert erro.value.status_http == 422
    assert erro.value.codigo == "PLT-03"
    assert erro.value.detalhes == {"item": "veiculos", "usado": 150, "limite": 150}

    with pytest.raises(LimiteDoPlano) as erro:
        exigir_limite("filiais")
    assert (
        erro.value.mensagem == "Seu plano permite até 3 filiais. Para abrir outra, mude de plano."
    )

    token = str(emitir_tokens(_usuario_da_empresa()).access_token)
    resposta = cliente("empresa-a.localhost", token).get("/api/assinatura/")
    assert resposta.status_code == 200  # ler continua funcionando
    assert resposta.json()["uso"]["veiculos"]["bloqueado"] is True
    assert resposta.json()["somente_leitura"] is False


def _em_outra_conexao(funcao):
    """Roda numa thread, com conexão própria em autocommit (fora da transação do teste)."""
    erros: list[BaseException] = []

    def rodar() -> None:
        try:
            funcao()
        except BaseException as erro:  # devolvido ao teste
            erros.append(erro)
        finally:
            connections.close_all()

    thread = threading.Thread(target=rodar)
    thread.start()
    return thread, erros


def test_plt_03_ca_010_09_duas_criacoes_simultaneas_nao_furam_o_limite(db):
    """Duas conexões de verdade, cada uma na sua transação, disputando o último veículo."""
    antes: dict[str, Any] = {}
    resultados: list[str] = []

    def preparar() -> None:
        empresa = Empresa.objects.get(schema_name="empresa_a")
        uso, _ = UsoEmpresa.objects.get_or_create(empresa=empresa)
        antes.update(plano=empresa.plano_id, veiculos=uso.veiculos, uso=uso.pk)
        Empresa.objects.filter(pk=empresa.pk).update(plano=Plano.objects.get(nome="Profissional"))
        UsoEmpresa.objects.filter(pk=uso.pk).update(veiculos=149, aviso_90_enviado={})

    def cadastrar() -> None:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
        try:
            with transaction.atomic():
                exigir_limite("veiculos")
                time.sleep(0.3)  # a outra criação chega enquanto esta segura a trava
                atualizar_uso("veiculos", 1)
            resultados.append("passou")
        except LimiteDoPlano as erro:
            resultados.append(erro.codigo)

    def conferir_e_desfazer() -> None:
        antes["final"] = UsoEmpresa.objects.get(pk=antes["uso"]).veiculos
        UsoEmpresa.objects.filter(pk=antes["uso"]).update(
            veiculos=antes["veiculos"], aviso_90_enviado={}
        )
        Empresa.objects.filter(schema_name="empresa_a").update(plano_id=antes["plano"])

    thread, erros = _em_outra_conexao(preparar)
    thread.join(timeout=20)
    assert not erros, erros
    try:
        corridas = [_em_outra_conexao(cadastrar) for _ in range(2)]
        for corrida, _ in corridas:
            corrida.join(timeout=20)
        assert not [e for _, lista in corridas for e in lista]
    finally:
        thread, erros = _em_outra_conexao(conferir_e_desfazer)
        thread.join(timeout=20)
        assert not erros, erros
    assert sorted(resultados) == ["PLT-03", "passou"]
    assert antes["final"] == 150


def test_plt_03_ca_010_10_plano_sem_limite(empresa_a, planos):
    _usar_plano(empresa_a, planos["Completo"], veiculos=5000, filiais=80, usuarios=900)
    for item in ("veiculos", "filiais", "usuarios"):
        exigir_limite(item)  # nunca bloqueia
    for uso in selectors.uso_do_plano(empresa_a).values():
        assert (uso["limite"], uso["aviso"], uso["bloqueado"]) == (None, False, False)


@pytest.mark.parametrize("status", ["suspensa", "pausada", "cancelada"])
def test_plt_03_ca_010_11_empresa_sem_operacao_fica_so_leitura(empresa_a, planos, status):
    _usar_plano(empresa_a, planos["Profissional"], veiculos=86)
    token = str(emitir_tokens(_usuario_da_empresa()).access_token)
    # Suspender, pausar e cancelar são ações da fase 2: o estado é montado direto.
    Empresa._base_manager.filter(pk=empresa_a.pk).update(status=status)
    api = cliente("empresa-a.localhost", token)

    leitura = api.get("/api/assinatura/")
    assert leitura.status_code == 200
    assert leitura.json()["somente_leitura"] is True
    escrita = api.post("/api/assinatura/", {}, format="json")
    assert escrita.status_code == 403
    assert escrita.json()["codigo"] == "empresa_sem_operacao"


# --- Equipe da plataforma ---


def test_plt_08_ca_010_12_login_com_duas_etapas_obrigatorio(equipe):
    dono, dispositivo = equipe["Você"]
    api = cliente(HOST_PLATAFORMA)

    resposta = api.post(
        ENTRAR,
        {"email": dono.email, "senha": SENHA, "codigo": codigo_atual(dispositivo)},
        format="json",
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    cookie = resposta.cookies[COOKIE_REFRESH]
    assert corpo["access"]
    assert "refresh" not in corpo and cookie.value not in str(corpo)
    assert cookie["httponly"] and cookie["secure"]
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/" and not cookie["domain"]

    liberar_codigo(dispositivo)
    senha_errada = api.post(
        ENTRAR,
        {"email": dono.email, "senha": "errada", "codigo": codigo_atual(dispositivo)},
        format="json",
    )
    codigo_errado = api.post(
        ENTRAR, {"email": dono.email, "senha": SENHA, "codigo": "000000"}, format="json"
    )
    for erro in (senha_errada, codigo_errado):
        assert erro.status_code == 401
        assert erro.json()["codigo"] == "credenciais_invalidas"
    assert senha_errada.json()["mensagem"] == codigo_errado.json()["mensagem"]

    # Dono criado por comando (createsuperuser), ainda sem autenticador.
    call_command(
        "createsuperuser",
        email="novo-dono@girolocadoras.com.br",
        nome="Novo dono",
        interactive=False,
        stdout=StringIO(),
    )
    novo = Usuario.objects.get(email="novo-dono@girolocadoras.com.br")
    novo.set_password(SENHA)
    novo.save(update_fields=["password"])
    etapa = api.post(ENTRAR, {"email": novo.email, "senha": SENHA}, format="json")
    assert etapa.status_code == 200
    assert etapa.json()["etapa"] == "configurar_2fa"
    pre = cliente(HOST_PLATAFORMA, etapa.json()["token_pre_2fa"])
    uri = pre.post("/api/plataforma/auth/2fa/configurar/").json()["otpauth_uri"]
    assert uri.startswith("otpauth://totp/Giro%3Anovo-dono%40girolocadoras.com.br?secret=")
    assert uri.endswith("&issuer=Giro")
    pendente = TOTPDevice.objects.get(user=novo, confirmed=False)
    verificado = pre.post(
        "/api/plataforma/auth/2fa/verificar/", {"codigo": codigo_atual(pendente)}, format="json"
    )
    assert verificado.status_code == 200
    assert len(verificado.json()["codigos_recuperacao"]) == 8
    assert verificado.json()["access"]

    eu = cliente(HOST_PLATAFORMA, verificado.json()["access"]).get("/api/plataforma/auth/eu/")
    assert eu.status_code == 200
    assert "codigos_recuperacao" not in eu.json()
    assert eu.json()["codigos_recuperacao_restantes"] == 8
    assert eu.json()["dois_fatores_ativo"] is True


def test_plt_08_ca_010_13_tres_codigos_errados_bloqueiam_por_15_minutos(equipe, relogio):
    diego, dispositivo = equipe["Diego Santos"]
    api = cliente(HOST_PLATAFORMA)
    errado = {"email": diego.email, "senha": SENHA, "codigo": "000000"}

    relogio.em("2026-10-07 10:00")
    assert api.post(ENTRAR, errado, format="json").status_code == 401
    assert api.post(ENTRAR, errado, format="json").status_code == 401
    terceira = api.post(ENTRAR, errado, format="json")
    assert terceira.status_code == 429
    assert terceira.json()["codigo"] == "PLT-08"
    assert terceira.json()["detalhes"]["tentar_de_novo_em"] == "2026-10-07T13:15:00Z"  # 10:15

    certo = {"email": diego.email, "senha": SENHA, "codigo": codigo_atual(dispositivo)}
    relogio.em("2026-10-07 10:14")
    assert api.post(ENTRAR, certo, format="json").status_code == 429
    relogio.em("2026-10-07 10:15")
    assert api.post(ENTRAR, certo, format="json").status_code == 200

    evento = EventoAuditoria.objects.get(acao="usuario.bloqueado", objeto_id=diego.pk)
    assert (evento.categoria, evento.regra) == ("seguranca", "PLT-08")
    assert (evento.ip, evento.aparelho) == ("10.0.0.5", "pytest")


def test_plt_08_ca_010_18_cinco_senhas_erradas_bloqueiam_por_15_minutos(equipe, relogio):
    caio, dispositivo = equipe["Caio Ribeiro"]
    api = cliente(HOST_PLATAFORMA)
    errada = {"email": caio.email, "senha": "palpite", "codigo": codigo_atual(dispositivo)}

    relogio.em("2026-10-07 10:00")
    for _ in range(4):
        assert api.post(ENTRAR, errada, format="json").status_code == 401
    quinta = api.post(ENTRAR, errada, format="json")
    assert quinta.status_code == 429
    assert quinta.json()["codigo"] == "PLT-08"
    assert quinta.json()["detalhes"]["tentar_de_novo_em"] == "2026-10-07T13:15:00Z"  # 10:15

    relogio.em("2026-10-07 10:14")
    certo = {"email": caio.email, "senha": SENHA, "codigo": codigo_atual(dispositivo)}
    assert api.post(ENTRAR, certo, format="json").status_code == 429
    relogio.em("2026-10-07 10:15")
    assert api.post(ENTRAR, certo, format="json").status_code == 200

    evento = EventoAuditoria.objects.get(acao="usuario.bloqueado", objeto_id=caio.pk)
    assert (evento.categoria, evento.regra) == ("seguranca", "PLT-08")
    assert (evento.ip, evento.aparelho) == ("10.0.0.5", "pytest")

    # 4 erradas e a certa: entra e a contagem volta a zero, então mais 4 erradas não bloqueiam.
    cache.clear()  # o limite de requisições por minuto (comum.limites) não é o assunto aqui
    relogio.em("2026-10-07 11:00")
    for _ in range(4):
        assert api.post(ENTRAR, errada, format="json").status_code == 401
    liberar_codigo(dispositivo)
    certo["codigo"] = codigo_atual(dispositivo)
    assert api.post(ENTRAR, certo, format="json").status_code == 200
    for _ in range(4):
        assert api.post(ENTRAR, errada, format="json").status_code == 401
    caio.refresh_from_db()
    assert caio.bloqueado_ate is None
    assert EventoAuditoria.objects.filter(acao="usuario.bloqueado", objeto_id=caio.pk).count() == 1


def test_plt_09_ca_010_14_funcoes_da_equipe(equipe):
    ordem = (
        "ver_empresas",
        "entrar_como_suporte",
        "cobranca_e_faturas",
        "planos_e_precos",
        "equipe_interna",
    )
    esperado = {
        "Você": (True, True, True, True, True),
        "Diego Santos": (True, True, False, False, False),
        "Paula Andrade": (True, False, True, False, False),
        "Caio Ribeiro": (True, True, False, False, False),
    }
    for nome, permissoes in esperado.items():
        api = cliente(HOST_PLATAFORMA, entrar(*equipe[nome]))
        pode = api.get("/api/plataforma/auth/eu/").json()["pode"]
        assert tuple(pode[p] for p in ordem) == permissoes, nome
        assert api.get("/api/plataforma/empresas/").status_code == 200
        fase_2 = api.post("/api/plataforma/planos/", {"nome": "Novo"}, format="json")
        assert fase_2.status_code == 404, nome


def test_plt_08_ca_010_15_convite_da_equipe_vence_em_7_dias(publico, relogio):
    relogio.em("2026-10-07 10:00")
    saida = StringIO()
    call_command(
        "convidar_equipe_plataforma",
        "larissa@girolocadoras.com.br",
        "suporte",
        "--nome",
        "Larissa Melo",
        stdout=saida,
    )
    achado = re.search(r"/convite/(\S+)", saida.getvalue())
    assert achado is not None
    caminho = f"/api/plataforma/convites/{achado.group(1)}/"
    api = cliente(HOST_PLATAFORMA)

    relogio.em("2026-10-13 10:00")
    resposta = api.get(caminho)
    assert resposta.status_code == 200
    assert (resposta.json()["nome"], resposta.json()["funcao"]) == ("Larissa Melo", "suporte")

    relogio.em("2026-10-15 10:00")
    vencido = api.get(caminho)
    assert vencido.status_code == 410
    assert vencido.json()["codigo"] == "convite_expirado"

    relogio.em("2026-10-13 10:00")
    aceito = api.post(f"{caminho}aceitar/", {"senha": SENHA}, format="json")
    assert aceito.status_code == 200
    assert aceito.json()["etapa"] == "configurar_2fa"
    larissa = Usuario.objects.get(email="larissa@girolocadoras.com.br")
    assert larissa.status == "convite_pendente"

    de_novo = api.post(ENTRAR, {"email": larissa.email, "senha": SENHA}, format="json")
    assert de_novo.json()["etapa"] == "configurar_2fa"
    pre = cliente(HOST_PLATAFORMA, de_novo.json()["token_pre_2fa"])
    pre.post("/api/plataforma/auth/2fa/configurar/")
    dispositivo = TOTPDevice.objects.get(user=larissa, confirmed=False)
    verificado = pre.post(
        "/api/plataforma/auth/2fa/verificar/", {"codigo": codigo_atual(dispositivo)}, format="json"
    )
    assert verificado.status_code == 200
    larissa.refresh_from_db()
    assert larissa.status == "ativo"


# --- Lista e detalhe das empresas ---


def test_imp_05_ca_010_16_moto_rapida_na_lista_e_no_detalhe(criar_empresa, equipe):
    empresa = criar_empresa()
    UsoEmpresa.objects.filter(empresa=empresa).update(veiculos=86, filiais=1, usuarios=5)
    api = cliente(HOST_PLATAFORMA, entrar(*equipe["Você"]))

    lista = api.get("/api/plataforma/empresas/").json()
    item = next(e for e in lista["resultados"] if e["subdominio"] == "motorapida")
    assert item["status"] == "em_teste"
    assert item["situacao"] == {"codigo": "em_teste", "rotulo": "Teste · dia 1", "tom": "info"}
    assert item["uso"] == {"veiculos": 86, "limite_veiculos": 150, "filiais": 1, "usuarios": 5}
    assert lista["contagens"]["em_teste"] >= 1

    for filtro in ("situacao=em_teste", "busca=12345678000195"):
        encontrados = api.get(f"/api/plataforma/empresas/?{filtro}").json()["resultados"]
        assert "motorapida" in [e["subdominio"] for e in encontrados], filtro

    detalhe = api.get(f"/api/plataforma/empresas/{empresa.pk}/").json()
    assert detalhe["teste"]["dias_restantes"] == 14
    assert detalhe["responsavel"]["nome"] == "Mariana Costa"
    assert [p["passo"] for p in detalhe["implantacao"]["passos"]] == [
        "conta",
        "marca",
        "filial",
        "ramo",
        "precos",
        "contrato",
        "recebimentos",
        "importar",
        "equipe",
        "primeira_locacao",
    ]


def test_imp_05_ca_010_17_ordem_da_situacao(empresa_a, planos, relogio):
    _usar_plano(empresa_a, planos["Profissional"], veiculos=135)
    Empresa._base_manager.filter(pk=empresa_a.pk).update(
        status="em_teste", teste_inicio=date(2026, 10, 1), etapa_implantacao="marca"
    )

    def situacao(dias_parada: int) -> str:
        Empresa._base_manager.filter(pk=empresa_a.pk).update(
            etapa_implantacao_desde=relogio.agora - timedelta(days=dias_parada)
        )
        return selectors.situacao(selectors.com_situacao().get(pk=empresa_a.pk))["codigo"]

    assert situacao(3) == "implantacao_parada"
    assert situacao(2) == "perto_do_limite"
