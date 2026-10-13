# Cobertura de regras

Tabela regra → teste → status. Gerada na T-040 a partir de `backend/tests/aceitacao/`. Fonte dos critérios: `docs/qa/criterios/`. Data: 07 out 2026.

Status: **esqueleto** = teste com o código da regra e os números esperados, marcado `xfail(strict)` até o backend da tarefa entregar; **passa** = teste verde; **T-019** = critério [integração], fica para o seed completo.

| Regra | Critério | Teste | Tarefa | Status |
| --- | --- | --- | --- | --- |
| APR-06 | CA-013-16 | `test_apr_06_ca_013_16_correcao_para_baixo` | T-013 | esqueleto |
| AUD-01 | CA-011-28 | `test_aud_01_ca_011_28_eventos_de_seguranca` | T-011 | esqueleto |
| AUD-04 | CA-014-07 | `test_aud_04_ca_014_07_mascara_nas_listas` | T-014 | esqueleto |
| AUD-04 | CA-014-08 | `test_aud_04_ca_014_08_detalhe_completo_so_para_quem_cadastra` | T-014 | esqueleto |
| AUD-04 | CA-014-11 | `test_aud_04_ca_014_11_auditoria_sem_dado_pessoal_aberto` | T-014 | esqueleto |
| AUD-05 | CA-013-20 | `test_aud_05_ca_013_20_arquivo_privado` | T-013 | esqueleto |
| AUD-05 | CA-014-10 | `test_aud_05_ca_014_10_documentos_privados` | T-014 | esqueleto |
| AUD-09 | CA-014-09 | `test_aud_09_ca_014_09_suporte_giro_sempre_mascarado` | T-014 | esqueleto |
| CLI-01 | CA-014-01 | `test_cli_01_ca_014_01_cpf_validado_e_unico` | T-014 | esqueleto |
| CLI-01 | CA-014-12 | `test_cli_01_ca_014_12_busca_por_cpf` | T-014 | esqueleto |
| CLI-02 | CA-014-13 | `test_cli_02_ca_014_13_itens_da_analise` | T-014 | esqueleto |
| CLI-02 | CA-014-14 | `test_cli_02_ca_014_14_impedimentos_para_retirada` | T-014 | esqueleto |
| CLI-03 | CA-014-02 | `test_cli_03_ca_014_02_salvar_incompleto` | T-014 | esqueleto |
| CLI-03 | CA-014-03 | `test_cli_03_ca_014_03_completar_leva_a_ativo` | T-014 | esqueleto |
| CLI-03 | CA-014-04 | `test_cli_03_ca_014_04_consentimento` | T-014 | esqueleto |
| CLI-05 | CA-014-17 | `test_cli_05_ca_014_17_bloqueio_e_desbloqueio_manuais` | T-014 | esqueleto |
| CLI-06 | CA-014-18 | `test_cli_06_ca_014_18_inativar_e_reativar` | T-014 | esqueleto |
| CLI-07 | CA-014-22 | `test_cli_07_ca_014_22_filtros` | T-014 | esqueleto |
| CLI-08 | CA-014-05 | `test_cli_08_ca_014_05_salvar_e_iniciar_locacao` | T-014 | esqueleto |
| CLI-08 | CA-014-06 | `test_cli_08_ca_014_06_quem_cadastra` | T-014 | esqueleto |
| FIL-01 | CA-012-01 | `test_fil_01_ca_012_01_primeira_filial_e_matriz` | T-012 | esqueleto |
| FIL-01 | CA-012-02 | `test_fil_01_ca_012_02_representacao` | T-012 | esqueleto |
| FIL-01 | CA-012-05 | `test_fil_01_ca_012_05_nome_unico_sem_diferenca_de_maiusculas` | T-012 | esqueleto |
| FIL-01 | CA-012-06 | `test_fil_01_ca_012_06_validacoes` | T-012 | esqueleto |
| FIL-01 | CA-012-07 | `test_fil_01_ca_012_07_uma_matriz_so` | T-012 | esqueleto |
| FIL-02 | CA-012-10 | `test_fil_02_ca_012_10_horario_normal` | T-012 | esqueleto |
| FIL-02 | CA-012-17 | `test_fil_02_ca_012_17_busca_de_cep` | T-012 | esqueleto |
| FIL-03 | CA-012-08 | `test_fil_03_ca_012_08_feriados_nacionais_sugeridos` | T-012 | esqueleto |
| FIL-03 | CA-012-09 | `test_fil_03_ca_012_09_feriado_conta_como_fechado` | T-012 | esqueleto |
| FIL-06 | CA-012-13 | `test_fil_06_ca_012_13_matriz_e_ultima_filial_nao_desativam` | T-012 | esqueleto |
| FIL-06 | CA-012-14 | `test_fil_06_ca_012_14_filial_sem_operacao_desativa` | T-012 | esqueleto |
| FIL-06 | CA-012-15 | `test_fil_06_ca_012_15_filial_com_operacao_nao_desativa` | T-012 | esqueleto |
| FIL-06 | CA-012-16 | `test_fil_06_ca_012_16_contas_em_aberto_nao_impedem` | T-012 | esqueleto |
| FIL-06 | CA-013-14 | `test_fil_06_ca_013_14_veto_a_desativacao_da_filial` | T-013 | esqueleto |
| FIN-15 | carteira de outubro | `test_fin_15_carteira_tem_42_locacoes_e_csv_igual_ao_gerador` | T-056 | passa |
| FIN-15 | carteira de outubro | `test_fin_15_previsto_recebido_vence_hoje_e_atraso_em_07_out` | T-056 | passa |
| FIN-15 | carteira de outubro | `test_fin_15_abas_somam_a_aba_todas` | T-056 | passa |
| FIN-15 | carteira de outubro | `test_fin_15_contador_do_menu_e_a_aba_em_atraso` | T-056 | passa |
| FIN-15 | carteira de outubro | `test_fin_15_recebido_nunca_passa_do_previsto` | T-056 | passa |
| IMP-05 | CA-010-16 | `test_imp_05_ca_010_16_moto_rapida_na_lista_e_no_detalhe` | T-010 | passa |
| IMP-05 | CA-010-17 | `test_imp_05_ca_010_17_ordem_da_situacao` | T-010 | passa |
| LOC-01 | CA-013-21 | `test_loc_01_ca_013_21_tabela_do_seed` | T-013 | esqueleto |
| LOC-01 | CA-013-24 | `test_loc_01_ca_013_24_categoria` | T-013 | esqueleto |
| LOC-02 | CA-013-25 | `test_loc_02_ca_013_25_extras` | T-013 | esqueleto |
| LOC-15 | CA-013-22 | `test_loc_15_ca_013_22_preco_vigente_na_data` | T-013 | esqueleto |
| LOC-15 | CA-013-23 | `test_loc_15_ca_013_23_preco_novo_nao_reescreve_o_passado` | T-013 | esqueleto |
| PLT-01 | CA-010-02 | `test_plt_01_ca_010_02_moto_rapida_nasce_em_teste` | T-010 | passa |
| PLT-01 | CA-010-03 | `test_plt_01_ca_010_03_vencimento_da_primeira_fatura` | T-010 | passa |
| PLT-01 | CA-010-04 | `test_plt_01_ca_010_04_subdominio_e_cnpj_unicos` | T-010 | passa |
| PLT-01 | CA-010-05 | `test_plt_01_ca_010_05_isolamento_entre_empresas` | T-010 | passa |
| PLT-03 | CA-010-01 | `test_plt_03_ca_010_01_tres_planos_do_seed` | T-010 | passa |
| PLT-03 | CA-010-06 | `test_plt_03_ca_010_06_uso_da_moto_rapida_sem_aviso` | T-010 | passa |
| PLT-03 | CA-010-07 | `test_plt_03_ca_010_07_aviso_em_90_por_cento` | T-010 | passa |
| PLT-03 | CA-010-08 | `test_plt_03_ca_010_08_bloqueio_em_100_por_cento_so_de_cadastro_novo` | T-010 | passa |
| PLT-03 | CA-010-09 | `test_plt_03_ca_010_09_duas_criacoes_simultaneas_nao_furam_o_limite` | T-010 | passa |
| PLT-03 | CA-010-10 | `test_plt_03_ca_010_10_plano_sem_limite` | T-010 | passa |
| PLT-03 | CA-010-11 | `test_plt_03_ca_010_11_empresa_sem_operacao_fica_so_leitura` | T-010 | passa |
| PLT-03 | CA-011-17 | `test_plt_03_ca_011_17_limite_do_plano_conta_convites` | T-011 | esqueleto |
| PLT-03 | CA-012-03 | `test_plt_03_ca_012_03_uso_do_plano_na_lista` | T-012 | esqueleto |
| PLT-03 | CA-012-04 | `test_plt_03_ca_012_04_segunda_e_terceira_filial_ate_o_limite` | T-012 | esqueleto |
| PLT-03 | CA-013-08 | `test_plt_03_ca_013_08_limite_de_veiculos` | T-013 | esqueleto |
| PLT-07 | CA-011-26 | `test_plt_07_ca_011_26_faixa_e_permissoes_do_suporte` | T-011 | esqueleto |
| PLT-07 | CA-011-27 | `test_plt_07_ca_011_27_administrador_controla_o_suporte` | T-011 | esqueleto |
| PLT-08 | CA-010-12 | `test_plt_08_ca_010_12_login_com_duas_etapas_obrigatorio` | T-010 | passa |
| PLT-08 | CA-010-13 | `test_plt_08_ca_010_13_tres_codigos_errados_bloqueiam_por_15_minutos` | T-010 | passa |
| PLT-08 | CA-010-15 | `test_plt_08_ca_010_15_convite_da_equipe_vence_em_7_dias` | T-010 | passa |
| PLT-09 | CA-010-14 | `test_plt_09_ca_010_14_funcoes_da_equipe` | T-010 | passa |
| USR-01 | CA-011-01 | `test_usr_01_ca_011_01_contagens_do_seed` | T-011 | esqueleto |
| USR-01 | CA-011-02 | `test_usr_01_ca_011_02_so_o_administrador_administra_usuarios` | T-011 | esqueleto |
| USR-01 | CA-011-14 | `test_usr_01_ca_011_14_convidar` | T-011 | esqueleto |
| USR-01 | CA-011-15 | `test_usr_01_ca_011_15_convite_vence_em_7_dias` | T-011 | esqueleto |
| USR-01 | CA-011-16 | `test_usr_01_ca_011_16_reenviar_e_cancelar` | T-011 | esqueleto |
| USR-01 | CA-011-18 | `test_usr_01_ca_011_18_aceitar_o_convite` | T-011 | esqueleto |
| USR-02 | CA-011-04 | `test_usr_02_ca_011_04_login_com_duas_etapas` | T-011 | esqueleto |
| USR-02 | CA-011-10 | `test_usr_02_ca_011_10_quem_e_obrigado` | T-011 | esqueleto |
| USR-02 | CA-011-11 | `test_usr_02_ca_011_11_exigir_para_todos` | T-011 | esqueleto |
| USR-02 | CA-011-12 | `test_usr_02_ca_011_12_mudar_de_perfil` | T-011 | esqueleto |
| USR-02 | CA-011-13 | `test_usr_02_ca_011_13_configurar_autenticador_com_a_marca_da_locadora` | T-011 | esqueleto |
| USR-02 | CA-011-24 | `test_usr_02_ca_011_24_redefinir_duas_etapas` | T-011 | esqueleto |
| USR-03 | CA-011-20 | `test_usr_03_ca_011_20_pode_por_perfil` | T-011 | esqueleto |
| USR-04 | CA-011-07 | `test_usr_04_ca_011_07_quem_nao_pode_entrar` | T-011 | esqueleto |
| USR-04 | CA-011-22 | `test_usr_04_ca_011_22_desativar_encerra_na_hora` | T-011 | esqueleto |
| USR-04 | CA-011-23 | `test_usr_04_ca_011_23_sempre_um_administrador` | T-011 | esqueleto |
| USR-05 | CA-011-21 | `test_usr_05_ca_011_21_permissoes_extras_so_somam` | T-011 | esqueleto |
| USR-06 | CA-011-03 | `test_usr_06_ca_011_03_login_sem_duas_etapas` | T-011 | esqueleto |
| USR-06 | CA-011-05 | `test_usr_06_ca_011_05_cinco_tentativas_erradas_bloqueiam_por_15_minutos` | T-011 | esqueleto |
| USR-06 | CA-011-06 | `test_usr_06_ca_011_06_mensagem_de_erro_nao_revela_o_que_errou` | T-011 | esqueleto |
| USR-06 | CA-011-08 | `test_usr_06_ca_011_08_duracao_da_sessao` | T-011 | esqueleto |
| USR-06 | CA-011-09 | `test_usr_06_ca_011_09_sair_e_sessoes` | T-011 | esqueleto |
| USR-06 | CA-011-19 | `test_usr_06_ca_011_19_senha` | T-011 | esqueleto |
| USR-06 | CA-011-25 | `test_usr_06_ca_011_25_recuperacao_sem_revelar_contas` | T-011 | esqueleto |
| USR-07 | CA-012-11 | `test_usr_07_ca_012_11_seletor_de_filial` | T-012 | esqueleto |
| USR-07 | CA-012-12 | `test_usr_07_ca_012_12_so_o_administrador_administra_filiais` | T-012 | esqueleto |
| VEI-01 | CA-013-02 | `test_vei_01_ca_013_02_busca` | T-013 | esqueleto |
| VEI-01 | CA-013-03 | `test_vei_01_ca_013_03_valor_de_compra_so_para_gestao` | T-013 | esqueleto |
| VEI-01 | CA-013-04 | `test_vei_01_ca_013_04_escopo_de_filial` | T-013 | esqueleto |
| VEI-01 | CA-013-05 | `test_vei_01_ca_013_05_cadastrar` | T-013 | esqueleto |
| VEI-01 | CA-013-06 | `test_vei_01_ca_013_06_placa_e_chassi_unicos_em_qualquer_estado` | T-013 | esqueleto |
| VEI-01 | CA-013-07 | `test_vei_01_ca_013_07_formato` | T-013 | esqueleto |
| VEI-01 | CA-013-09 | `test_vei_01_ca_013_09_corrigir_placa_ou_chassi` | T-013 | esqueleto |
| VEI-01 | CA-013-15 | `test_vei_01_ca_013_15_km_nunca_diminui` | T-013 | esqueleto |
| VEI-02 | CA-013-10 | `test_vei_02_ca_013_10_acoes_permitidas` | T-013 | esqueleto |
| VEI-02 | CA-013-11 | `test_vei_02_ca_013_11_acoes_combina_perfil_e_estado` | T-013 | esqueleto |
| VEI-03 | CA-013-17 | `test_vei_03_ca_013_17_situacao_do_documento` | T-013 | esqueleto |
| VEI-03 | CA-013-18 | `test_vei_03_ca_013_18_vencimento_tira_da_frota_disponivel` | T-013 | esqueleto |
| VEI-03 | CA-013-19 | `test_vei_03_ca_013_19_renovar_nao_libera_sozinho` | T-013 | esqueleto |
| VEI-04 | CA-013-13 | `test_vei_04_ca_013_13_transferencia_so_disponivel` | T-013 | esqueleto |
| VEI-06 | CA-013-01 | `test_vei_06_ca_013_01_contagens_do_seed` | T-013 | esqueleto |
| VEI-06 | CA-013-26 | `test_vei_06_ca_013_26_ocupacao_de_90_dias` | T-013 | esqueleto |
| VEI-07 | CA-013-12 | `test_vei_07_ca_013_12_servico_de_transicao` | T-013 | esqueleto |

## Critérios [integração] da T-014 (ficam para a T-019)

CA-014-15 (CLI-05, bloqueio automático com 15 dias), CA-014-16 (CLI-05, desbloqueio ao quitar), CA-014-19 (CLI-07, ação principal), CA-014-20 (situação na lista), CA-014-21 (CLI-06, FIN-01, contagens e indicadores) e a parte com locação e financeiro de CA-014-18 (`cliente_com_pendencia`).

## Regras citadas nos critérios sem teste próprio (cobertas por outro código)

- PLT-09 e PLT-08 em CA-010-12 a 15 usam os códigos PLT-08 e PLT-09 no nome; CA-010-15 leva PLT-08 por falta de código próprio para convite da equipe.
- AUD-03, FIL-02 (tarefa urgente), AUT-06, APR-09 aparecem dentro dos critérios CA-011-27, CA-013-18 e CA-014-17, sem teste com o próprio código no nome.
- Regras fora de T-010 a T-014 (LOC, DEV, FIN, VEN e demais) entram nas próximas tarefas de aceitação.

## Inventário de todas as regras com código

Uma linha por código de `docs/regras-de-negocio.md` (136 códigos). "Testes" conta os testes de esqueleto da tabela acima. Os códigos sem critério não têm teste porque a regra ainda não virou critério de aceite; quando o produto escrever o critério, o qa cria o teste.

| Regra | Testes | Situação |
| --- | --- | --- |
| APR-01 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| APR-02 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| APR-03 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| APR-04 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| APR-05 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| APR-06 | 1 | esqueleto (T-010 a T-014) |
| APR-07 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| APR-08 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| APR-09 | 0 | critério escrito em T-015, T-017; teste na tarefa de aceitação correspondente |
| APR-10 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUD-01 | 1 | esqueleto (T-010 a T-014) |
| AUD-02 | 0 | critério escrito em T-018; teste na tarefa de aceitação correspondente |
| AUD-03 | 0 | critério escrito em T-018; teste na tarefa de aceitação correspondente |
| AUD-04 | 3 | esqueleto (T-010 a T-014) |
| AUD-05 | 2 | esqueleto (T-010 a T-014) |
| AUD-06 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUD-07 | 0 | critério escrito em T-018; teste na tarefa de aceitação correspondente |
| AUD-08 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUD-09 | 1 | esqueleto (T-010 a T-014) |
| AUT-01 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-02 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-03 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-04 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-05 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| AUT-06 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-07 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-08 | 0 | critério escrito em T-017, T-018; teste na tarefa de aceitação correspondente |
| AUT-09 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-10 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-11 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-12 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-13 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-14 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| AUT-15 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| CLI-01 | 2 | esqueleto (T-010 a T-014) |
| CLI-02 | 2 | esqueleto (T-010 a T-014) |
| CLI-03 | 3 | esqueleto (T-010 a T-014) |
| CLI-04 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| CLI-05 | 1 | esqueleto (T-010 a T-014) |
| CLI-06 | 1 | esqueleto (T-010 a T-014) |
| CLI-07 | 1 | esqueleto (T-010 a T-014) |
| CLI-08 | 2 | esqueleto (T-010 a T-014) |
| CLI-09 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| DEV-01 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| DEV-02 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| DEV-03 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| DEV-04 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| DEV-05 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| DEV-06 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| FIL-01 | 5 | esqueleto (T-010 a T-014) |
| FIL-02 | 2 | esqueleto (T-010 a T-014) |
| FIL-03 | 2 | esqueleto (T-010 a T-014) |
| FIL-04 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| FIL-05 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| FIL-06 | 5 | esqueleto (T-010 a T-014) |
| FIN-01 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| FIN-02 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| FIN-03 | 0 | critério escrito em T-015, T-017; teste na tarefa de aceitação correspondente |
| FIN-04 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| FIN-05 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| FIN-06 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| FIN-07 | 0 | critério escrito em T-016, T-017; teste na tarefa de aceitação correspondente |
| FIN-08 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| FIN-09 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| FIN-10 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| FIN-11 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| FIN-12 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| FIN-13 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| FIN-14 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| FIN-15 | 5 | passa (T-056, sobre a carteira de outubro em `docs/qa/carteira-outubro/`); a conferência contra a API fica para a T-017 e a T-019 |
| IMP-01 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| IMP-02 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| IMP-03 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| IMP-04 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| IMP-05 | 2 | passa (T-010) |
| IMP-06 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| LOC-01 | 2 | esqueleto (T-010 a T-014) |
| LOC-02 | 1 | esqueleto (T-010 a T-014) |
| LOC-03 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| LOC-04 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| LOC-05 | 0 | critério escrito em T-015, T-017; teste na tarefa de aceitação correspondente |
| LOC-06 | 0 | critério escrito em T-015, T-017; teste na tarefa de aceitação correspondente |
| LOC-07 | 0 | critério escrito em T-017; teste na tarefa de aceitação correspondente |
| LOC-08 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| LOC-09 | 0 | critério escrito em T-015, T-016; teste na tarefa de aceitação correspondente |
| LOC-10 | 0 | critério escrito em T-015, T-016; teste na tarefa de aceitação correspondente |
| LOC-11 | 0 | critério escrito em T-015, T-016; teste na tarefa de aceitação correspondente |
| LOC-12 | 0 | critério escrito em T-015, T-016, T-017; teste na tarefa de aceitação correspondente |
| LOC-13 | 0 | critério escrito em T-015, T-016; teste na tarefa de aceitação correspondente |
| LOC-14 | 0 | critério escrito em T-015; teste na tarefa de aceitação correspondente |
| LOC-15 | 2 | esqueleto (T-010 a T-014) |
| MAN-01 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| MAN-02 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| MAN-03 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| MAN-04 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| MAN-05 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| MAN-06 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| PLT-01 | 4 | passa (T-010) |
| PLT-02 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| PLT-03 | 11 | 7 passam (T-010); 4 esqueleto (T-011 a T-013) |
| PLT-04 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| PLT-05 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| PLT-06 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| PLT-07 | 2 | esqueleto (T-010 a T-014) |
| PLT-08 | 3 | passa (T-010) |
| PLT-09 | 1 | passa (T-010) |
| PLT-10 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| USR-01 | 6 | esqueleto (T-010 a T-014) |
| USR-02 | 6 | esqueleto (T-010 a T-014) |
| USR-03 | 1 | esqueleto (T-010 a T-014) |
| USR-04 | 3 | esqueleto (T-010 a T-014) |
| USR-05 | 1 | esqueleto (T-010 a T-014) |
| USR-06 | 7 | esqueleto (T-010 a T-014) |
| USR-07 | 2 | esqueleto (T-010 a T-014) |
| VEI-01 | 8 | esqueleto (T-010 a T-014) |
| VEI-02 | 2 | esqueleto (T-010 a T-014) |
| VEI-03 | 3 | esqueleto (T-010 a T-014) |
| VEI-04 | 1 | esqueleto (T-010 a T-014) |
| VEI-05 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEI-06 | 2 | esqueleto (T-010 a T-014) |
| VEI-07 | 1 | esqueleto (T-010 a T-014) |
| VEN-01 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-02 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-03 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-04 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-05 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-06 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-07 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-08 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-09 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VEN-10 | 0 | sem critério ainda; tarefa de critérios do produto pendente |
| VIS-01 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| VIS-02 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| VIS-03 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| VIS-04 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |
| VIS-05 | 0 | critério escrito em T-016; teste na tarefa de aceitação correspondente |

## T-019 · Seed completo: critérios CA-019-01 a 31

Testes em `backend/tests/aceitacao/test_t019_seed_completo.py` (`test_<regra>_seed_019_NN_*`), sobre o banco que o `make seed` deixa, com o relógio em 07 out 2026 12:00 (os casos de outras datas movem o relógio no próprio teste). Data: 13 out 2026.

| Critério | Caso | Status |
| --- | --- | --- |
| CA-019-01, 02 | Idempotência, sem dado real | passa (`test_seed_127_02`, `test_seed_127_07`, T-127) |
| CA-019-03 a 07 | Empresa, 5 pessoas, uso do plano, implantação concluída, plataforma e equipe | passa |
| CA-019-08, 09 | Tabela de preços e configuração; frota de 86 | passa |
| CA-019-10 | QXA-4B21 (estado, km de 23 set) | passa; troca de óleo: xfail, sem módulo de manutenção |
| CA-019-11 | Factor (16 L, 21.870 km, saída cheia) e NMax (8 L) | passa |
| CA-019-12, 13, 15 | Clientes, bloqueio do Rafael, em aberto R$ 1.646,40 | passa |
| CA-019-14 | Histórico da análise em 07 out | xfail: T-148 |
| CA-019-16 a 19 | 51 locações, as das telas, parcelas do CSV (sem D-21), reservas em novembro | passa |
| CA-019-20, 21 | Contas a receber do mês e da semana | passa |
| CA-019-22, 23 | Caixa de 07 out (gaveta R$ 281,00) e despesas de outubro (R$ 7.066,70) | passa |
| CA-019-24 | Contadores, aprovações, Lúcia e João | passa (agenda do João: ver [decisão] no backlog) |
| CA-019-25 | Eventos nas horas e com o ator do caso | passa; sangria com a filial: xfail, T-150 |
| CA-019-26 a 29 | Devolução da LOC-2836 (R$ 183,00), troca (R$ 263,00), LOC-2812, LOC-2841 em 07, 16, 28 e 30 out | passa |
| CA-019-30 | Multa e juros no caixa (Carlos 30609, Rafael 138517) | passa; Rafael volta `incompleto`: [decisão] no backlog |
| CA-019-31 | Venda VEN-0177, comissões, conciliação, DRE | xfail: sem módulo |

Os `xfail(strict)` avisam quando o código chegar.
