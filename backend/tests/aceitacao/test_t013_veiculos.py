"""T-013 · Veículos, categorias, documentos, histórico de status (docs/qa/criterios/T-013.md)."""

from .apoio import CONTAGENS_FROTA_SEED, PRECOS_SEED, aguarda, pendente

T = "T-013"


@aguarda(T)
def test_vei_06_ca_013_01_contagens_do_seed():
    pendente(
        contagens=CONTAGENS_FROTA_SEED,
        filtro_disponivel="só os 16, contagens iguais",
        vendido_baixado="só com filtro explícito",
    )


@aguarda(T)
def test_vei_01_ca_013_02_busca():
    pendente(
        buscas=["SAK1D39", "sak-1d39", "9C2KC2210RR004417"],
        acha="Honda CG 160 Fan vermelha",
        diaria_vigente_centavos=5490,
    )


@aguarda(T)
def test_vei_01_ca_013_03_valor_de_compra_so_para_gestao():
    pendente(
        gestao=("Mariana", "Rodrigo", 1390000),
        sem_acesso=("Bruna", "João", "Lúcia", None),
        campos_nulos=["valor_compra_centavos", "data_compra"],
    )


@aguarda(T)
def test_vei_01_ca_013_04_escopo_de_filial():
    pendente(veiculo_da_caucaia_para_rodrigo=404)


@aguarda(T)
def test_vei_01_ca_013_05_cadastrar():
    pendente(
        placa="QAB1C23",
        modelo="Honda Biz 125 2026",
        categoria="Urbana",
        filial="Centro",
        km=0,
        status=(201, "disponivel"),
        historico_inicial=True,
        primeira_leitura_km=True,
        veiculos_no_plano=(86, 87),
        bruna=403,
        joao=403,
    )


@aguarda(T)
def test_vei_01_ca_013_06_placa_e_chassi_unicos_em_qualquer_estado():
    pendente(
        placa_repetida=(409, "VEI-01", "placa"),
        chassi_de_vendido=(409, "VEI-01", "chassi"),
        chassi_de_baixado=(409, "VEI-01", "chassi"),
    )


@aguarda(T)
def test_vei_01_ca_013_07_formato():
    pendente(
        recusados=["chassi com 16 caracteres", "placa AB1234", "categoria de outra filial"],
        status=(400, "validacao"),
        aceitas=["ABC1234", "ABC1D23 (sem hífen)"],
    )


@aguarda(T)
def test_plt_03_ca_013_08_limite_de_veiculos():
    pendente(
        veiculos_ativos=150, cadastro_151=(422, "PLT-03"), com_150_sendo_1_baixado="cadastro passa"
    )


@aguarda(T)
def test_vei_01_ca_013_09_corrigir_placa_ou_chassi():
    pendente(
        quem="administrador",
        acao="corrigir-identificacao com motivo",
        auditoria="antes e depois",
        patch_com_placa="não muda",
        placa_ja_usada=(409, "VEI-01"),
    )


@aguarda(T)
def test_vei_02_ca_013_10_acoes_permitidas():
    pendente(
        casos=[
            ("Rodrigo bloquear SAK1D39", 200, "indisponivel"),
            ("Rodrigo desbloquear SAK1D39", 200, "disponivel"),
            ("Rodrigo colocar-a-venda SAK1D39 1650000", 200, "a_venda"),
            ("Rodrigo voltar-para-frota", 200, "disponivel"),
            (
                "bloquear QXA4B21 alugado",
                409,
                "transicao_veiculo",
                {"de": "alugado", "para": "indisponivel"},
            ),
            ("colocar-a-venda PMZ3E17 em_manutencao", 409, "transicao_veiculo"),
            ("Mariana baixar QXA4B21 alugado", 409, "transicao_veiculo"),
            ("Mariana baixar RHT9F02 reservado, motivo roubo", 200, "baixado"),
            ("Rodrigo baixar", 403),
        ],
        valor_a_venda_na_lista_centavos=1650000,
        grava="HistoricoStatusVeiculo e auditoria",
        patch_status="não existe",
    )


@aguarda(T)
def test_vei_02_ca_013_11_acoes_combina_perfil_e_estado():
    pendente(
        rodrigo_disponivel={
            "bloquear": True,
            "colocar_a_venda": True,
            "transferir": True,
            "desbloquear": False,
            "voltar_para_frota": False,
            "baixar": False,
        },
        bruna="todas as ações de escrita false",
    )


@aguarda(T)
def test_vei_07_ca_013_12_servico_de_transicao():
    pendente(
        aceita=[("vendido", "a_venda"), ("vendido", "indisponivel")],
        recebe_na_troca_chassi_de_vendido="mesmo id, histórico preservado, indisponivel",
        chassi_novo="cria veículo indisponivel",
        alugado_para_a_venda="erro de regra",
    )


@aguarda(T)
def test_vei_04_ca_013_13_transferencia_so_disponivel():
    pendente(
        sak1d39_centro_para_caucaia=200,
        grava="TransferenciaVeiculo origem e destino",
        alugado=(409, "VEI-04"),
        destino_igual_ou_filial_inativa=400,
    )


@aguarda(T)
def test_fil_06_ca_013_14_veto_a_desativacao_da_filial():
    pendente(
        caucaia_com_veiculo_disponivel=(422, "filial_com_veiculos"),
        unico_veiculo_baixado="desativa",
    )


@aguarda(T)
def test_vei_01_ca_013_15_km_nunca_diminui():
    pendente(
        registrar_3500=(200, 3500),
        registrar_3000=(
            422,
            "VEI-01",
            "O km informado é menor que o atual (3.500). Para corrigir, use Corrigir km.",
        ),
        detalhes={"km_atual": 3500},
        evento="veiculos.km_atualizado",
    )


@aguarda(T)
def test_apr_06_ca_013_16_correcao_para_baixo():
    pendente(
        rodrigo_3400=(200, "na hora, leitura de correção e auditoria"),
        motivo="Erro de digitação",
        joao=(202, {"tipo": "APR-06", "status": "pendente"}),
        km_ate_aprovar=3500,
        bruna=403,
    )


@aguarda(T)
def test_vei_03_ca_013_17_situacao_do_documento():
    pendente(
        hoje="2026-10-07",
        seguro={
            "2026-10-25": ("vence_em_breve", 18),
            "2026-11-06": ("vence_em_breve", 30),
            "2026-11-07": ("em_dia", 31),
            "2026-10-06": ("vencido", None),
        },
    )


@aguarda(T)
def test_vei_03_ca_013_18_vencimento_tira_da_frota_disponivel():
    pendente(
        tarefa="aut_06_vencimento_de_documentos",
        as_="2026-10-25 07:00",
        sak1d39_seguro="indisponivel, motivo Seguro vencido",
        qxa4b21_crlv="continua alugado, tarefa urgente para gerentes da Centro",
        ipva_rastreador="não mudam status",
        trinta_dias_antes="alerta aos gerentes, sem mudar status",
        duas_vezes="sem alerta duplicado",
    )


@aguarda(T)
def test_vei_03_ca_013_19_renovar_nao_libera_sozinho():
    pendente(
        novo_seguro=201,
        anterior="inativo no histórico",
        status="continua indisponivel",
        desbloquear_renovado=200,
        desbloquear_crlv_vencido=(422, "VEI-03"),
    )


@aguarda(T)
def test_aud_05_ca_013_20_arquivo_privado():
    pendente(
        url_vence_minutos=15,
        cada_get="nova URL",
        invalidos=["11 MB", ".exe"],
        status=400,
        vendedor_envia=403,
    )


@aguarda(T)
def test_loc_01_ca_013_21_tabela_do_seed():
    pendente(precos=PRECOS_SEED, filial="Centro", vigente_desde="2026-10-01")


@aguarda(T)
def test_loc_15_ca_013_22_preco_vigente_na_data():
    pendente(
        street_semanal_2026_09_30=29940,
        street_semanal_2026_10_01=32900,
        historico="duas vigências, da mais nova para a mais velha, com quem alterou",
    )


@aguarda(T)
def test_loc_15_ca_013_23_preco_novo_nao_reescreve_o_passado():
    pendente(
        vigente_desde_passado=400,
        vigente_desde_ja_existente=(409, "preco_ja_definido"),
        vigente_desde_2026_11_01=(201, {"diaria_centavos": 4990}),
        proximo_preco=True,
        locacoes_em_andamento_mantidas="número de locações ativas da Urbana",
        urbana_diaria_em_7_out=4490,
        put_do_preco_futuro_ate="2026-10-31",
    )


@aguarda(T)
def test_loc_01_ca_013_24_categoria():
    pendente(
        nome_repetido=(409, "categoria_nome_em_uso"),
        street_para_carro=(422, "categoria_com_veiculos"),
        desativar_street=(422, "categoria_com_veiculos"),
        rodrigo=403,
    )


@aguarda(T)
def test_loc_02_ca_013_25_extras():
    pendente(
        extra="Capacete extra",
        valor_centavos=1500,
        cobranca="por_periodo",
        status=201,
        mudar_para_1800="só locações novas",
        desativado="some da escolha",
    )


@aguarda(T)
def test_vei_06_ca_013_26_ocupacao_de_90_dias():
    pendente(
        alugado_60_disponivel_20_a_venda_10="75.00",
        entrou_ha_30_dias_alugado_15="50.00",
        formula="alugado ÷ (dias − dias a_venda)",
    )
