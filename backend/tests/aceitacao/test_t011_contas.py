"""T-011 · Contas, perfis, 2 etapas, convite (critérios em docs/qa/criterios/T-011.md)."""

from .apoio import USUARIOS_SEED, aguarda, pendente

T = "T-011"


@aguarda(T)
def test_usr_01_ca_011_01_contagens_do_seed():
    pendente(
        contagens={"todos": 6, "ativos": 3, "convites": 2, "desativados": 1},
        plano={"usado": 5, "limite": 10, "aviso": False, "bloqueado": False},
        usuarios=USUARIOS_SEED,
        felipe_conta_no_plano=False,
    )


@aguarda(T)
def test_usr_01_ca_011_02_so_o_administrador_administra_usuarios():
    pendente(
        recebem_403=["Rodrigo", "Bruna", "João", "Lúcia"], rotas=["GET /api/usuarios/", "escritas"]
    )


@aguarda(T)
def test_usr_06_ca_011_03_login_sem_duas_etapas():
    pendente(
        pessoa="Bruna",
        etapa="pronto",
        access_no_corpo=True,
        refresh="só no cookie __Host-giro_refresh",
        manter_conectado="ignorado",
    )


@aguarda(T)
def test_usr_02_ca_011_04_login_com_duas_etapas():
    pendente(
        mariana="verificar_2fa",
        rodrigo="verificar_2fa",
        sem_access=True,
        token_pre_2fa_vence_em_segundos=300,
        aos_5min01s=401,
    )


@aguarda(T)
def test_usr_06_ca_011_05_cinco_tentativas_erradas_bloqueiam_por_15_minutos():
    pendente(
        inicio="09:00",
        quinta=(429, "USR-06"),
        tentar_de_novo_em="09:15",
        as_09_14=429,
        as_09_15="entra",
        evento="seguranca",
        aviso_a="Mariana",
        mariana_3_senhas_mais_2_codigos=429,
        quatro_erros_e_acerto="entra e zera",
    )


@aguarda(T)
def test_usr_06_ca_011_06_mensagem_de_erro_nao_revela_o_que_errou():
    pendente(
        email_inexistente=(401, "credenciais_invalidas"),
        senha_errada=(401, "credenciais_invalidas"),
        mensagem="E-mail ou senha incorretos",
    )


@aguarda(T)
def test_usr_04_ca_011_07_quem_nao_pode_entrar():
    pendente(
        felipe=(403, "usuario_inativo", "Seu acesso foi desativado. Fale com o administrador."),
        joao=(403, "convite_pendente", "Use o link do convite para criar seu acesso"),
    )


@aguarda(T)
def test_usr_06_ca_011_08_duracao_da_sessao():
    pendente(
        desktop={
            "ultimo_uso": "08:00",
            "renovar_19_59": 200,
            "renovar_20_01": (401, "sessao_encerrada"),
        },
        celular={
            "ultimo_uso": "2026-10-07 10:00",
            "renovar_06_nov_09_59": 200,
            "renovar_06_nov_10_01": (401, "sessao_encerrada"),
        },
        refresh_gira=True,
        refresh_anterior=401,
        sem_x_requested_with=403,
    )


@aguarda(T)
def test_usr_06_ca_011_09_sair_e_sessoes():
    pendente(
        sair=204,
        ip_mascarado="/24",
        encerrar_outras="mantém só a atual",
        access_encerrado=(401, "sessao_encerrada"),
    )


@aguarda(T)
def test_usr_02_ca_011_10_quem_e_obrigado():
    pendente(
        obrigatorio={"Mariana": True, "Lúcia": True, "Rodrigo": False, "Bruna": False},
        mariana_desativa=(422, "USR-02"),
        rodrigo_desativa=204,
    )


@aguarda(T)
def test_usr_02_ca_011_11_exigir_para_todos():
    pendente(bruna_sem_otp=(401, "2fa_obrigatorio"), proximo_login="configurar_2fa")


@aguarda(T)
def test_usr_02_ca_011_12_mudar_de_perfil():
    pendente(
        rodrigo="gerente → financeiro",
        sem_otp="2fa_obrigatorio",
        auditoria="usuario.alterar_perfil",
        categoria="seguranca",
        antes="gerente",
        depois="financeiro",
    )


@aguarda(T)
def test_usr_02_ca_011_13_configurar_autenticador_com_a_marca_da_locadora():
    pendente(
        issuer="Moto%20R%C3%A1pida",
        palavra_giro_ausente=True,
        codigos_recuperacao=8,
        restantes_apos_uso=7,
        mesmo_codigo_duas_vezes=False,
    )


@aguarda(T)
def test_usr_01_ca_011_14_convidar():
    pendente(
        email="joao@motorapida.com.br",
        perfil="vistoriador",
        filial="Filial Centro",
        celular="(85) 99654-2210",
        status=201,
        convite_expira_em="2026-10-14",
        canais=["email", "whatsapp"],
        apos_commit=True,
        plano=(5, 6),
        sem_email=(400, "validacao"),
        sem_celular="só e-mail",
        email_em_uso=(409, "email_em_uso"),
        vistoriador_sem_filial=(400, "validacao"),
    )


@aguarda(T)
def test_usr_01_ca_011_15_convite_vence_em_7_dias():
    pendente(
        em_14_out=200,
        em_15_out=(410, "convite_expirado"),
        vencido_continua="convite_pendente",
        conta_no_plano=True,
    )


@aguarda(T)
def test_usr_01_ca_011_16_reenviar_e_cancelar():
    pendente(
        reenviar_em_15_out="expira em 22 out",
        link_antigo=[404, 410],
        cancelar="desativado",
        plano_cai=1,
        reenviar_ativo=(409, "transicao_usuario"),
    )


@aguarda(T)
def test_plt_03_ca_011_17_limite_do_plano_conta_convites():
    pendente(ativos=8, convites=2, convidar_mais=(422, "PLT-03"), apos_cancelar_um="passa")


@aguarda(T)
def test_usr_01_ca_011_18_aceitar_o_convite():
    pendente(
        joao="pronto e ativo",
        lucia="configurar_2fa, ativa só após confirmar o código",
        mariana="marca o passo conta da implantação",
    )


@aguarda(T)
def test_usr_06_ca_011_19_senha():
    pendente(
        recusadas=[
            "abc123",
            "senhasemnumero",
            "123456789012",
            "<o próprio e-mail>",
            "password1234",
        ],
        status=(400, "validacao"),
        aceita="girafa-azul-2026",
    )


@aguarda(T)
def test_usr_03_ca_011_20_pode_por_perfil():
    pendente(
        rodrigo={"painel": "filial", "locacoes_cancelar": "aprova"},
        bruna={"painel": "proprios", "locacoes_cancelar": "pede", "despesas_aprovar": False},
        joao={"veiculos": "km_e_avarias", "despesas_lancar": "manutencao"},
        lucia={"financeiro_pagar": True, "veiculos": "nao"},
        mariana={"administracao": True},
    )


@aguarda(T)
def test_usr_05_ca_011_21_permissoes_extras_so_somam():
    pendente(
        aprovar_desconto={"Bruna": "aprova", "Rodrigo": "padrao_do_perfil: true"},
        relatorios_todas_filiais="painel: todas_filiais",
        reduz_permissao=False,
    )


@aguarda(T)
def test_usr_04_ca_011_22_desativar_encerra_na_hora():
    pendente(
        access_atual=(401, "sessao_encerrada"),
        refresh_renova=False,
        plano=(5, 4),
        historico_na_auditoria=True,
        reativar="ativo",
        reativar_com_10_de_10=(422, "PLT-03"),
    )


@aguarda(T)
def test_usr_04_ca_011_23_sempre_um_administrador():
    pendente(
        tirar_proprio_perfil_sendo_unica=(422, "ultimo_administrador"),
        desativar_a_si_mesma=(422, "desativar_a_si_mesmo"),
    )


@aguarda(T)
def test_usr_02_ca_011_24_redefinir_duas_etapas():
    pendente(
        motivo="Perdeu o celular",
        sessoes_caem=True,
        proximo_login="configurar_2fa se o perfil exigir",
        auditoria="seguranca com motivo",
    )


@aguarda(T)
def test_usr_06_ca_011_25_recuperacao_sem_revelar_contas():
    pendente(
        esqueci=202,
        mesmo_corpo=True,
        link_vale_minutos=60,
        aos_60min01s=(410, "link_expirado"),
        uso_unico=True,
        quarto_pedido_na_hora="não envia",
        redefinir="encerra todas as sessões; autenticador segue exigido",
    )


@aguarda(T)
def test_plt_07_ca_011_26_faixa_e_permissoes_do_suporte():
    pendente(
        suporte={
            "nome": "Diego Santos",
            "permissao": "ver",
            "duracao_min": 30,
            "motivo": "Chamado #1042",
        },
        escrita=(403, "PLT-07", "No modo só ver você não pode fazer isto"),
        apos_fim=(401, "PLT-07"),
        rotas_proibidas=["auth/entrar", "renovar", "sessoes", "escrita de usuarios"],
        proibidas_status=(403, "PLT-07"),
    )


@aguarda(T)
def test_plt_07_ca_011_27_administrador_controla_o_suporte():
    pendente(
        bloquear="acesso vira revogado",
        proxima_requisicao="falha",
        auditoria="entrada, saída e revogação com destaque e motivo (AUD-03)",
    )


@aguarda(T)
def test_aud_01_ca_011_28_eventos_de_seguranca():
    pendente(
        eventos=[
            "login",
            "login que falhou",
            "bloqueio por tentativas",
            "mudança de perfil, filiais ou permissões",
            "desativação",
            "redefinição de 2 etapas",
            "troca de senha",
        ],
        campos=["quem", "quando", "ação", "objeto", "antes", "depois", "ip", "aparelho"],
        grava_segredo=False,
    )
