"""T-010 · Plataforma, planos, empresas (critérios em docs/qa/criterios/T-010.md)."""

from .apoio import PLANOS_SEED, aguarda, pendente

T = "T-010"


@aguarda(T)
def test_plt_03_ca_010_01_tres_planos_do_seed():
    pendente(planos=PLANOS_SEED, meses_cobrados_no_anual=10)


@aguarda(T)
def test_plt_01_ca_010_02_moto_rapida_nasce_em_teste():
    pendente(
        status="em_teste",
        teste_inicio="2026-10-07",
        teste_fim="2026-10-21",
        dias_restantes=14,
        preco_contratado_centavos=44900,
        ciclo="mensal",
        schema="motorapida",
        endereco="motorapida.girolocadoras.com.br",
        usuaria="mariana@motorapida.com.br",
        usuaria_status="convite_pendente",
        convite_dias=7,
        email_so_apos_commit=True,
        auditoria_da_plataforma=True,
    )


@aguarda(T)
def test_plt_01_ca_010_03_vencimento_da_primeira_fatura():
    pendente(primeira_cobranca="2026-10-22", faturas_recentes=[])


@aguarda(T)
def test_plt_01_ca_010_04_subdominio_e_cnpj_unicos():
    pendente(
        subdominio_em_uso=(409, "subdominio_em_uso"),
        cnpj_em_uso=(409, "cnpj_em_uso"),
        reservados=["admin", "www", "api", "app", "suporte", "status"],
        invalidos=["Moto_Rapida", "mr", "x" * 31],
        cnpj_digito_errado="12.345.678/0001-11",
        status_validacao=400,
    )


@aguarda(T)
def test_plt_01_ca_010_05_isolamento_entre_empresas():
    pendente(token_de_outra_empresa=(401, "nao_autenticado"))


@aguarda(T)
def test_plt_03_ca_010_06_uso_da_moto_rapida_sem_aviso():
    pendente(
        veiculos=(86, 150),
        filiais=(1, 3),
        usuarios=(5, 10),
        aviso=False,
        bloqueado=False,
        somente_leitura=False,
        faixa_aviso=None,
    )


@aguarda(T)
def test_plt_03_ca_010_07_aviso_em_90_por_cento():
    pendente(
        profissional={134: False, 135: True},
        essencial={27: True},
        bloqueado_em_135=False,
        notificacao="limite do plano em 90%",
        notificacoes_com_136=1,
    )


@aguarda(T)
def test_plt_03_ca_010_08_bloqueio_em_100_por_cento_so_de_cadastro_novo():
    pendente(
        status=422,
        codigo="PLT-03",
        detalhes={"item": "veiculos", "usado": 150, "limite": 150},
        mensagem_filiais="Seu plano permite até 3 filiais. Para abrir outra, mude de plano.",
        bloqueado=True,
        leitura_continua=True,
    )


@aguarda(T)
def test_plt_03_ca_010_09_duas_criacoes_simultaneas_nao_furam_o_limite():
    pendente(veiculos_antes=149, passam=1, recusada=(422, "PLT-03"))


@aguarda(T)
def test_plt_03_ca_010_10_plano_sem_limite():
    pendente(plano="Completo", limite=None, aviso=False, bloqueado=False)


@aguarda(T)
def test_plt_03_ca_010_11_empresa_sem_operacao_fica_so_leitura():
    pendente(
        status=["suspensa", "pausada", "cancelada"],
        somente_leitura=True,
        escrita=(403, "empresa_sem_operacao"),
        leitura=200,
    )


@aguarda(T)
def test_plt_08_ca_010_12_login_com_duas_etapas_obrigatorio():
    pendente(
        ok=200,
        cookie="__Host-giro_refresh",
        cookie_flags=["HttpOnly", "Secure", "SameSite=Strict"],
        refresh_no_corpo=False,
        erro=(401, "credenciais_invalidas"),
        mesma_mensagem=True,
        sem_autenticador="configurar_2fa",
        codigos_recuperacao=8,
        restantes_em_eu=8,
    )


@aguarda(T)
def test_plt_08_ca_010_13_tres_codigos_errados_bloqueiam_por_15_minutos():
    pendente(
        pessoa="Diego Santos",
        erros=3,
        as_10_00=(429, "PLT-08"),
        tentar_de_novo_em="10:15",
        codigo_certo_10_14=429,
        codigo_certo_10_15="entra",
        evento_seguranca_no_public=True,
    )


@aguarda(T)
def test_plt_09_ca_010_14_funcoes_da_equipe():
    pendente(
        pode={
            "dono": (True, True, True, True, True),
            "Diego Santos": (True, True, False, False, False),
            "Paula Andrade": (True, False, True, False, False),
            "Caio Ribeiro": (True, True, False, False, False),
        },
        ordem=(
            "ver_empresas",
            "entrar_como_suporte",
            "cobranca_e_faturas",
            "planos_e_precos",
            "equipe_interna",
        ),
        endpoint_da_fase_2=404,
    )


@aguarda(T)
def test_plt_08_ca_010_15_convite_da_equipe_vence_em_7_dias():
    pendente(
        convite="Larissa Melo",
        em_13_out=200,
        em_15_out=(410, "convite_expirado"),
        apos_aceitar="configurar_2fa",
        ativo_so_apos_codigo=True,
    )


@aguarda(T)
def test_imp_05_ca_010_16_moto_rapida_na_lista_e_no_detalhe():
    pendente(
        situacao={"codigo": "em_teste", "rotulo": "Teste · dia 1", "tom": "info"},
        uso={"veiculos": 86, "filiais": 1, "usuarios": 5},
        filtro_situacao="em_teste",
        busca="12345678000110",
        dias_restantes=14,
        responsavel="Mariana Costa",
        passos_implantacao=10,
    )


@aguarda(T)
def test_imp_05_ca_010_17_ordem_da_situacao():
    pendente(
        parada_3_dias_135_de_150="implantacao_parada", parada_2_dias_135_de_150="perto_do_limite"
    )
