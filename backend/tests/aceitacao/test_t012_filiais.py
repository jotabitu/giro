"""T-012 · Filiais (critérios em docs/qa/criterios/T-012.md)."""

from .apoio import aguarda, pendente

T = "T-012"


@aguarda(T)
def test_fil_01_ca_012_01_primeira_filial_e_matriz():
    pendente(enviado_matriz=False, gravado_matriz=True, administrador_ligado=True, passo_implantacao="filial")


@aguarda(T)
def test_fil_01_ca_012_02_representacao():
    pendente(
        horario_resumo="seg a sex 8h–18h · sáb 8h–12h",
        endereco_resumo="Av. Bezerra de Menezes, 1200 · Fortaleza, CE",
        gerentes=[{"nome": "Rodrigo Pinheiro"}],
        campos_inexistentes=["vagas", "tabela de preço padrão", "conta de recebimento", "centro de custo",
                             "nota fiscal", "frota compartilhada", "status rascunho"],
    )


@aguarda(T)
def test_plt_03_ca_012_03_uso_do_plano_na_lista():
    pendente(plano={"usado": 1, "limite": 3, "aviso": False, "bloqueado": False, "nome_plano": "Profissional"})


@aguarda(T)
def test_plt_03_ca_012_04_segunda_e_terceira_filial_ate_o_limite():
    pendente(
        caucaia=(201, {"usado": 2, "aviso": False}), messejana=(201, {"usado": 3, "aviso": True, "bloqueado": True}),
        aldeota=(422, "PLT-03", {"item": "filiais", "usado": 3, "limite": 3}),
        mensagem="Seu plano permite até 3 filiais. Para abrir outra, mude de plano.", grava=False,
    )


@aguarda(T)
def test_fil_01_ca_012_05_nome_unico_sem_diferenca_de_maiusculas():
    pendente(nome="filial centro", resposta=(409, "filial_nome_em_uso"))


@aguarda(T)
def test_fil_01_ca_012_06_validacoes():
    pendente(
        status=(400, "validacao"), grava=False,
        casos=["CNPJ 12.345.678/0002-00", "CEP com 7 dígitos", "UF XX", "horario sem uma das 7 chaves",
               "segunda fecha 08:00 abre 18:00", "sábado com 3 intervalos", "intervalos 08–12 e 11–14"],
        sem_cnpj_inscricoes_e_contato="salva",
    )


@aguarda(T)
def test_fil_01_ca_012_07_uma_matriz_so():
    pendente(tornar_matriz="Caucaia vira matriz e Centro deixa de ser, na mesma transação", chamadas_simultaneas="nunca duas matrizes", inativa=(422, "filial_inativa"))


@aguarda(T)
def test_fil_03_ca_012_08_feriados_nacionais_sugeridos():
    pendente(
        sugeridos_2026=["2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20", "2026-12-25"],
        vale_antes_de_confirmar=False, local="2026-08-15 só para a Filial Centro",
    )


@aguarda(T)
def test_fil_03_ca_012_09_feriado_conta_como_fechado():
    pendente(
        esta_aberta_2026_10_12_10h=False, proxima_abertura_de_2026_10_10_12h30="2026-10-13 08:00",
        filial_sem_o_feriado_esta_aberta=True,
    )


@aguarda(T)
def test_fil_02_ca_012_10_horario_normal():
    pendente(
        sabado_11h59=True, sabado_12h00=False, domingo=False,
        quarta_18h30=False, proxima_abertura="2026-10-08 08:00",
    )


@aguarda(T)
def test_usr_07_ca_012_11_seletor_de_filial():
    pendente(
        mariana={"filiais": ["Centro", "Caucaia"], "pode_escolher_todas": True},
        rodrigo={"filiais": ["Centro"], "pode_escolher_todas": False},
        x_filial_caucaia=(403, "USR-07", "Você não tem acesso a esta filial"), x_filial_todas=(403, "USR-07"),
        sem_x_filial="matriz",
    )


@aguarda(T)
def test_usr_07_ca_012_12_so_o_administrador_administra_filiais():
    pendente(recebem_403=["Rodrigo", "Bruna", "João", "Lúcia"], rotas=["GET lista", "POST", "PATCH", "desativar", "reativar"], filial_fora_do_escopo=404)


@aguarda(T)
def test_fil_06_ca_012_13_matriz_e_ultima_filial_nao_desativam():
    pendente(matriz=(422, "filial_matriz", "Escolha outra matriz antes de desativar esta filial"), ultima_filial=(422, "ultima_filial"))


@aguarda(T)
def test_fil_06_ca_012_14_filial_sem_operacao_desativa():
    pendente(
        motivo="Ponto fechado", ativo=False, some_de_minhas=True, usado_apos=1, vinculos_preservados=True,
        auditoria="quem, quando e motivo", reativar=200, usado_apos_reativar=2, reativar_com_3_de_3=(422, "PLT-03"),
    )


@aguarda(T)
def test_fil_06_ca_012_15_filial_com_operacao_nao_desativa():
    pendente(
        veiculos=("disponivel", "alugado", "reservado", "em_manutencao", "indisponivel", "a_venda", "filial_com_veiculos"),
        locacoes=("rascunho", "aguardando_retirada", "ativa", "devolucao_atrasada", "filial_com_locacoes"),
        caixa=("aberto", "aguardando_aprovacao", "filial_com_caixa_aberto"), status=422, contagem_na_resposta="31 veículos",
        nao_veta=["veiculos vendido/baixado", "locações encerrada/cancelada", "caixas fechado"],
        assinante="falso do evento filiais.desativacao_solicitada (módulos reais em T-013, T-015, T-017)",
    )


@aguarda(T)
def test_fil_06_ca_012_16_contas_em_aberto_nao_impedem():
    pendente(conta_a_receber_centavos=29940, desativa=True, conta_status="aberta", filial_da_conta="Caucaia", verificar_com_financeiro_real="T-017")


@aguarda(T)
def test_fil_02_ca_012_17_busca_de_cep():
    pendente(
        cep="60325000", logradouro="Av. Bezerra de Menezes", bairro="São Gerardo", cidade="Fortaleza", uf="CE",
        desconhecido=(404, "cep_nao_encontrado", "Não achamos esse CEP. Preencha o endereço à mão."), todos_os_perfis=True,
    )
