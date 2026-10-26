# Cobertura de regras

Tabela regra → teste → status, refeita na T-375 (parte 1) a partir dos testes da `origin/main` de 26 out 2026 (`943c1ca`), lendo os testes: nada foi rodado. Substitui a versão de 07 out (T-040), que era de esqueletos `xfail` e não vale mais. Fonte das regras: `docs/regras-de-negocio.md`; fases pelas marcas da T-356 (25 out 2026). Os critérios `CA-` estão em `docs/qa/criterios/`.

## Como ler

- **Regra:** código da regra (160 códigos achados no arquivo de regras; a contagem do Produto na T-353 foi 159, a diferença é uma regra nova ou a forma de contar).
- **Fase:** 1 = MVP; 2 = marcada como fase 2 na regra, na seção ou pela T-356.
- **Testes:** até 2 testes com o código no nome (`test_<regra>_...`), e a coluna seguinte tem quantos existem. `(xfail)` = teste que ainda não passa de propósito.
- **Status:** `coberta` = pelo menos um teste verde com o código no nome; `outro nome` = a regra é testada, mas sem o código no nome; `xfail` = só há teste esperado-falhar; `fase 2` = fora do MVP e sem teste ainda; `FALTA TESTE` = é da fase 1 e nada a cobre.

## Resumo

| Status | Regras |
| --- | --- |
| coberta | 124 (3 delas são da fase 2 e já têm teste, ver abaixo) |
| xfail | 3 |
| outro nome | 2 |
| fase 2 sem teste | 28 |
| **FALTA TESTE (fase 1)** | **3**: `AUT-01`, `AUT-11`, `IMP-07` |

Atenção: `FIN-09` (comissão da locação) tem testes verdes (`test_fin_09_ca_015_25_*`) e é da fase 2 desde a T-356. Quando o backend parar de lançar a comissão de locação (tarefa que decorre da T-356), esses testes têm de ser trocados por um que prove que **nenhuma** comissão nasce, na mesma entrega. Aviso a quem pegar essa tarefa. Os outros dois casos de fase 2 já com teste são `FIN-13` (linhas do relatório) e `AUT-04` (Pix Automático pelo Asaas, que o MVP não usa: a parcela segue a régua).

## As regras sem teste com o código no nome

O Produto contou 42 na T-353 (main `626d432`); hoje são 33, porque os testes das T-215, T-281 e das tarefas de assinatura e cancelamento entraram depois. Conferência de cada uma:

| Regra | Resultado | Detalhe |
| --- | --- | --- |
| `PLT-10`, `PLT-16` | fase 2 | painel da plataforma e compra pública (`Plat-*`, `Compra-*`) sem rota no frontend (MEMORY, 14 out) |
| `IMP-06`, `AUT-14` | fase 2 | marca "Fase 2" na regra (T-356) |
| `IMP-07` | **falta teste** | regra nova da T-356 (o que marca cada passo do assistente); nenhum teste cobre. Pertence à tarefa que implementa os 5 passos da implantação |
| `VEI-05` | outro nome | "Rendeu no ano" e custo de manutenção: o teste `test_usr_09_vendedor_sem_custo_do_veiculo` e o do contrato da ficha (`test_t013_veiculos.py`, chaves `rendeu_no_ano_centavos` e `custo_manutencao_ano_centavos`) conferem a presença e a ausência; **não há teste do valor** (receitas − custos do ano). Renomear com o código e somar um teste do cálculo |
| `CLI-11` | fase 2 | preencher pela CNH-e (16 out) |
| `VEN-01`, `VEN-03` a `VEN-10` | fase 2 | vendas inteiras; `apps/vendas` é só README |
| `FIN-10`, `FIN-11`, `FIN-14`, `AUT-10`, `AUT-12` | fase 2 | comissões, conciliação e relatórios (T-356) |
| `MAN-01`, `MAN-02`, `MAN-04` a `MAN-06`, `AUT-07` | fase 2 | manutenção e preventivas; `apps/manutencao` não existe |
| `APR-08`, `AUT-09` | fase 2 | aviso da aprovação esquecida |
| `AUT-16` | fase 2 | expurgo da auditoria (T-356) |
| `AUT-01` | **falta teste** | lembrete de devolução às 08:00 por WhatsApp. É da fase 1 e a tarefa nem existe no código: backlog **T-367** |
| `AUT-02` | outro nome | a tarefa `aut_02_marcar_devolucao_atrasada` é exercida em `test_loc_10_ca_015_19_tolerancia_e_diarias` (`test_t091_locacao_fim.py`) e nos de `test_t111_decisoes_t091.py`; falta um teste com `aut_02` no nome (renomear ou somar um) |
| `AUT-11` | **falta teste** | backup mensal (e-mail com o link). A geração do arquivo existe (`apps/auditoria`, exportação completa com 2 etapas), mas a tarefa agendada do dia 1 às 09:00 não, e nem a regra nem o backlog marcam a fase. [decisão] para o Produto: fase 1 ou 2? |
| `FIN-09` (já tem teste) | ver acima | comissão da locação ficou fase 2 |

## xfail que ainda existem

Sete testes (nenhum xfail dinâmico: `QUEBRADAS` da T-317 está vazia e a T-189 não tem mais `xfail`).

| Teste | Arquivo | O que destrava |
| --- | --- | --- |
| `test_plt_06_reativar_so_com_atrasada_paga` | `test_t195_cancelar_pausar.py` | **T-365** (backend, `reativar_empresa`, depende da T-196). `strict` |
| `test_plt_14_fatura_guarda_tomador_ao_pedir_a_nota` | `test_t184_faturas.py` | **T-197** (backend, NFS-e da assinatura, `[bloqueada]` até o contador confirmar). Não é `strict` |
| `test_man_03_seed_019_10_proxima_troca_de_oleo_aos_19900` | `test_t019_seed_completo.py` | módulo de manutenção/OS (fase 2); sem tarefa no backlog |
| `test_ven_02_seed_019_31_venda_ven_0177` | `test_t019_seed_completo.py` | módulo de vendas (fase 2); sem tarefa no backlog |
| `test_fin_09_seed_019_31_comissao_da_venda_ven_0177` | `test_t019_seed_completo.py` | vendas e comissões (fase 2, `AUT-10`); sem tarefa no backlog |
| `test_fin_12_seed_019_31_conciliacao_diferenca_de_137_10` | `test_t019_seed_completo.py` | módulo de conciliação (fase 2); sem tarefa no backlog |
| `test_fin_13_seed_019_31_dre_de_setembro_34231_30` | `test_t019_seed_completo.py` | selector da DRE e relatórios (fase 2); sem tarefa no backlog |

Os cinco da fase 2 são os casos da tabela de referência (VEN-0177, comissão, conciliação R$ 137,10, DRE de setembro R$ 34.231,30, troca de óleo aos 19.900 km) que só se provam quando os módulos existirem. Até lá, a "Pronto quando" do QA ("todos os casos da tabela de referência passam") não se fecha na fase 1: peço decisão do Orquestrador sobre registrar isso como exceção da fase.

## Tabela por regra

| Regra | Fase | Testes com o código no nome | Qtd | Status |
| --- | --- | --- | --- | --- |
| PLT-01 | 1 | `test_plt_01_periodo_da_primeira_fatura_da_moto_rapida`<br>`test_plt_01_mes_sem_o_dia_vence_no_ultimo_e_volta`<br>+23 testes | 25 | coberta |
| PLT-02 | 1 | `test_plt_02_cartao_salvo_recusado_no_parceiro_falso`<br>`test_plt_02_situacao_do_cartao_recusado_e_da_atrasada`<br>+21 testes | 23 | coberta |
| PLT-03 | 1 | `test_plt_03_preco_anual_e_10_mensalidades`<br>`test_plt_03_exigir_limite_fora_de_transacao_e_erro_de_programacao`<br>+19 testes | 21 | coberta |
| PLT-04 | 1 | `test_plt_04_planos_para_comparar`<br>`test_plt_04_upgrade_em_teste`<br>+20 testes | 22 | coberta |
| PLT-05 | 1 | `test_plt_05_plano_desativado_so_aparece_se_for_o_atual` | 1 | coberta |
| PLT-06 | 1 | `test_plt_06_datas_do_cancelamento_da_moto_rapida`<br>`test_plt_06_cancelar_anual_sem_devolucao_vai_ate_o_fim_do_ano_pago`<br>+36 testes | 39 | coberta |
| PLT-07 | 1 | `test_plt_07_ca_011_26_faixa_e_permissoes_do_suporte`<br>`test_plt_07_ca_011_27_administrador_controla_o_suporte`<br>+11 testes | 13 | coberta |
| PLT-08 | 1 | `test_plt_08_ca_010_12_login_com_duas_etapas_obrigatorio`<br>`test_plt_08_ca_010_13_tres_codigos_errados_bloqueiam_por_15_minutos`<br>+18 testes | 20 | coberta |
| PLT-09 | 1 | `test_plt_09_ca_010_14_funcoes_da_equipe`<br>`test_plt_09_ca_018_15_so_o_dono_ve` | 2 | coberta |
| PLT-10 | 2 | — | 0 | fase 2 · Telas Plat-* e painel da plataforma são fase 2 (MEMORY, 14 out) |
| PLT-11 | 1 | `test_plt_11_catalogo_confere_a_tabela_da_regra`<br>`test_plt_11_ca_ass_21_sem_oferta_no_completo` | 2 | coberta |
| PLT-12 | 1 | `test_plt_12_ramo_get_seed`<br>`test_plt_12_configuracoes_cartao_ramo`<br>+11 testes | 13 | coberta |
| PLT-13 | 1 | `test_plt_13_cartao_pago_na_pagina_fica_guardado`<br>`test_plt_13_cartao_com_outra_forma_nao_guarda_token`<br>+25 testes | 27 | coberta |
| PLT-14 | 1 | `test_plt_14_descricao_da_fatura`<br>`test_plt_14_codigo_da_fatura_por_empresa`<br>+13 testes | 16 | coberta |
| PLT-15 | 1 | `test_plt_15_seed_019_ca_ass_47_48_dados_fiscais_e_filial_separados`<br>`test_plt_15_endereco_nasce_da_matriz`<br>+9 testes | 11 | coberta |
| PLT-16 | 2 | — | 0 | fase 2 · Compra pública (Compra-*) é fase 2 (MEMORY, 14 out) |
| IMP-01 | 1 | `test_imp_01_seed_019_06_implantacao_concluida`<br>`test_usr_08_imp_01_implantacao`<br>+4 testes | 6 | coberta |
| IMP-02 | 1 | `test_imp_02_83_prontos_3_com_erro_e_86_depois_de_corrigir`<br>`test_imp_02_correcao_que_ainda_tem_erro_continua_com_erro`<br>+7 testes | 9 | coberta |
| IMP-03 | 1 | `test_imp_03_importa_ate_o_limite_e_avisa` | 1 | coberta |
| IMP-04 | 1 | `test_imp_04_ca_015_09_sem_modelo_de_contrato_publicado`<br>`test_imp_04_publicar_o_primeiro_modelo_conclui_o_passo_contrato`<br>+2 testes | 4 | coberta |
| IMP-05 | 1 | `test_imp_05_passo_da_implantacao_move_o_funil`<br>`test_imp_05_parada_mostra_o_primeiro_passo_aberto`<br>+17 testes | 19 | coberta |
| IMP-06 | 2 | — | 0 | fase 2 · Marca "Fase 2" na regra (T-356) |
| IMP-07 | 1 | — | 0 | FALTA TESTE |
| USR-01 | 1 | `test_usr_01_ca_011_01_contagens_do_seed`<br>`test_usr_01_ca_011_02_so_o_administrador_administra_usuarios`<br>+17 testes | 19 | coberta |
| USR-02 | 1 | `test_usr_02_ca_011_04_login_com_duas_etapas`<br>`test_usr_02_ca_011_10_quem_e_obrigado`<br>+13 testes | 15 | coberta |
| USR-03 | 1 | `test_usr_03_ca_011_20_pode_por_perfil`<br>`test_usr_03_ca_011_21_detalhe_com_permissoes_extras`<br>+1 testes | 3 | coberta |
| USR-04 | 1 | `test_usr_04_is_active_segue_o_status`<br>`test_usr_04_status_so_muda_pela_maquina`<br>+8 testes | 10 | coberta |
| USR-05 | 1 | `test_usr_05_ca_011_21_permissoes_extras_so_somam`<br>`test_usr_05_usr_08_navegacao_por_perfil`<br>+11 testes | 13 | coberta |
| USR-06 | 1 | `test_usr_06_ca_011_03_login_sem_duas_etapas`<br>`test_usr_06_ca_011_05_cinco_tentativas_erradas_bloqueiam_por_15_minutos`<br>+6 testes | 8 | coberta |
| USR-07 | 1 | `test_usr_07_troca_de_filiais_da_pessoa_vai_para_a_auditoria`<br>`test_usr_07_financeiro_escolhe_todas_as_filiais`<br>+8 testes | 10 | coberta |
| USR-08 | 1 | `test_usr_05_usr_08_navegacao_por_perfil`<br>`test_usr_08_administrador_ve_o_geral_depois_da_primeira_locacao`<br>+9 testes | 11 | coberta |
| USR-09 | 1 | `test_usr_09_vistoriador_ve_veiculo_sem_valores`<br>`test_usr_09_vendedor_sem_custo_do_veiculo`<br>+8 testes | 10 | coberta |
| FIL-01 | 1 | `test_fil_01_resumo_com_almoco_e_dias_soltos`<br>`test_fil_01_horario_valido`<br>+8 testes | 10 | coberta |
| FIL-02 | 1 | `test_fil_02_ca_012_10_horario_normal`<br>`test_fil_02_ca_012_17_busca_de_cep` | 2 | coberta |
| FIL-03 | 1 | `test_fil_03_pascoa`<br>`test_fil_03_nacionais_de_2026`<br>+3 testes | 5 | coberta |
| FIL-04 | 1 | `test_vei_04_fil_04_ca_013_27_categoria_so_da_filial_na_transferencia` | 1 | coberta |
| FIL-05 | 1 | `test_fil_05_ca_015_09_veiculo_de_outra_filial`<br>`test_fin_06_fil_05_filial_da_despesa_ligada_a_veiculo` | 2 | coberta |
| FIL-06 | 1 | `test_fil_06_ca_012_13_matriz_e_ultima_filial_nao_desativam`<br>`test_fil_06_ca_012_14_filial_sem_operacao_desativa`<br>+4 testes | 6 | coberta |
| VEI-01 | 1 | `test_vei_01_ca_013_02_busca`<br>`test_vei_01_ca_013_03_valor_de_compra_so_para_gestao`<br>+11 testes | 13 | coberta |
| VEI-02 | 1 | `test_vei_02_ca_013_10_acoes_permitidas`<br>`test_vei_02_ca_013_11_acoes_combina_perfil_e_estado`<br>+2 testes | 4 | coberta |
| VEI-03 | 1 | `test_vei_03_ca_013_17_situacao_do_documento`<br>`test_vei_03_aut_06_ca_013_18_vencimento_tira_da_frota_disponivel`<br>+4 testes | 6 | coberta |
| VEI-04 | 1 | `test_vei_04_mov_06_rota_transferir_saiu`<br>`test_vei_04_ca_013_13_transferencia_so_disponivel`<br>+2 testes | 4 | coberta |
| VEI-05 | 1 | `test_usr_09_vendedor_sem_custo_do_veiculo` (test_t013_veiculos.py) | 0 | outro nome |
| VEI-06 | 1 | `test_vei_06_ca_013_01_contagens_do_seed`<br>`test_vei_06_ca_013_26_ocupacao_de_90_dias`<br>+4 testes | 6 | coberta |
| VEI-07 | 1 | `test_vei_07_ca_013_12_servico_de_transicao` | 1 | coberta |
| VEI-08 | 1 | `test_vei_08_catalogo_acha_modelo_unico`<br>`test_vei_08_catalogo_ambiguo_nao_preenche`<br>+27 testes | 29 | coberta |
| MOV-01 | 1 | `test_mov_01_mov_03_ca_246_01_ida_ao_lava_jato`<br>`test_mov_01_ca_246_13_auditoria`<br>+5 testes | 7 | coberta |
| MOV-02 | 1 | `test_mov_02_ca_246_11_quem_pode`<br>`test_mov_02_ca_246_17_quem_leva_acha_a_chegada`<br>+3 testes | 5 | coberta |
| MOV-03 | 1 | `test_mov_03_acao_movimentar`<br>`test_mov_01_mov_03_ca_246_01_ida_ao_lava_jato`<br>+14 testes | 16 | coberta |
| MOV-04 | 1 | `test_mov_04_fin_05_ca_246_02_parada_com_despesa`<br>`test_mov_04_ca_246_07_oficina_mantem_em_manutencao`<br>+3 testes | 5 | coberta |
| MOV-05 | 1 | `test_mov_05_vei_01_ca_246_03_chegada_no_destino`<br>`test_mov_05_mov_06_vei_04_ca_246_09_transferencia_na_chegada`<br>+3 testes | 5 | coberta |
| MOV-06 | 1 | `test_vei_04_mov_06_rota_transferir_saiu`<br>`test_mov_05_mov_06_vei_04_ca_246_09_transferencia_na_chegada` | 2 | coberta |
| CLI-01 | 1 | `test_cli_01_cpf_unico_pelo_hash`<br>`test_cli_01_mesmo_cpf_em_outra_empresa_pode`<br>+8 testes | 10 | coberta |
| CLI-02 | 1 | `test_cli_02_ca_014_13_itens_da_analise`<br>`test_cli_02_ca_014_14_impedimentos_para_retirada`<br>+2 testes | 4 | coberta |
| CLI-03 | 1 | `test_cli_03_ca_014_02_salvar_incompleto`<br>`test_cli_03_ca_014_03_completar_leva_a_ativo`<br>+5 testes | 7 | coberta |
| CLI-04 | 1 | `test_cli_04_seed_019_14_historico_da_analise_em_07_out`<br>`test_cli_04_historico_conta_que_nasce_vencida_nao_e_atraso`<br>+2 testes | 4 | coberta |
| CLI-05 | 1 | `test_cli_05_ca_014_15_bloqueio_automatico_com_15_dias`<br>`test_cli_05_ca_014_16_desbloqueio_automatico_ao_quitar`<br>+8 testes | 10 | coberta |
| CLI-06 | 1 | `test_cli_06_ca_014_20_situacao_na_lista`<br>`test_cli_06_ca_014_21_contagens_e_indicadores`<br>+1 testes | 3 | coberta |
| CLI-07 | 1 | `test_cli_07_ca_014_19_acao_principal`<br>`test_cli_07_ca_014_19_acao_principal_com_os_blocos`<br>+1 testes | 3 | coberta |
| CLI-08 | 1 | `test_cli_08_ca_014_05_salvar_e_iniciar_locacao`<br>`test_cli_08_ca_014_06_quem_cadastra` | 2 | coberta |
| CLI-09 | 1 | `test_cli_09_ca_014_18_inativar_e_reativar`<br>`test_cli_09_ca_015_09_cliente_inativo` | 2 | coberta |
| CLI-10 | 1 | `test_cli_10_lista_filtra_por_filial`<br>`test_cli_10_lista_ignora_o_seletor`<br>+1 testes | 3 | coberta |
| CLI-11 | 2 | — | 0 | fase 2 · Marca "fase 2" na regra (16 out) |
| LOC-01 | 1 | `test_loc_01_ca_013_21_tabela_do_seed`<br>`test_loc_01_ca_013_24_categoria`<br>+7 testes | 9 | coberta |
| LOC-02 | 1 | `test_loc_02_ca_013_25_extras`<br>`test_loc_02_ca_015_04_extras_por_periodo` | 2 | coberta |
| LOC-03 | 1 | `test_loc_03_ca_015_06_ate_5_por_cento_sem_aprovacao`<br>`test_loc_03_ca_015_06_gerente_da_8_por_cento_direto`<br>+4 testes | 6 | coberta |
| LOC-04 | 1 | `test_loc_05_loc_04_ca_017_04_parcelas_antecipadas` | 1 | coberta |
| LOC-05 | 1 | `test_loc_01_loc_05_loc_14_ca_015_02_diaria_semanal_e_mensal`<br>`test_loc_05_ca_015_07_rascunho_e_confirmacao`<br>+5 testes | 7 | coberta |
| LOC-06 | 1 | `test_loc_06_ca_015_15_total_pago_loc_2836`<br>`test_loc_06_total_pago_pelo_fluxo` | 2 | coberta |
| LOC-07 | 1 | `test_loc_07_loc_10_ca_015_16_sinais_e_lista`<br>`test_loc_07_cli_05_ca_017_11_atraso_alimenta_locacao_e_cliente` | 2 | coberta |
| LOC-08 | 1 | `test_loc_08_aditivo_sem_assinatura_em_7_dias_avisa_os_gerentes`<br>`test_loc_08_aditivo_assinado_nao_conta_como_contrato`<br>+10 testes | 12 | coberta |
| LOC-09 | 1 | `test_loc_09_ca_015_18_troca_de_veiculo`<br>`test_loc_09_ca_016_15_troca_de_veiculo_acerto_unico`<br>+15 testes | 17 | coberta |
| LOC-10 | 1 | `test_loc_07_loc_10_ca_015_16_sinais_e_lista`<br>`test_loc_10_loc_11_fil_03_ca_016_12_atraso_no_acerto`<br>+2 testes | 4 | coberta |
| LOC-11 | 1 | `test_loc_11_filial_sempre_fechada_nao_tem_proxima_abertura`<br>`test_loc_11_almoco_conta_como_fechado`<br>+2 testes | 4 | coberta |
| LOC-12 | 1 | `test_dev_07_loc_12_ca_016_25_aprovacao_deixa_as_parcelas_4_e_5_em_aberto`<br>`test_loc_12_loc_13_ca_016_14_encerramento_antecipado_da_patricia`<br>+17 testes | 19 | coberta |
| LOC-13 | 1 | `test_loc_12_loc_13_ca_016_14_encerramento_antecipado_da_patricia`<br>`test_loc_12_loc_13_ca_015_21_patricia_loc_2812`<br>+3 testes | 5 | coberta |
| LOC-14 | 1 | `test_loc_01_loc_05_loc_14_ca_015_02_diaria_semanal_e_mensal`<br>`test_loc_14_ca_015_02_mensal_menor_que_um_mes` | 2 | coberta |
| LOC-15 | 1 | `test_loc_15_ca_013_22_preco_vigente_na_data`<br>`test_loc_15_ca_013_23_preco_novo_nao_reescreve_o_passado`<br>+4 testes | 6 | coberta |
| VIS-01 | 1 | `test_vis_01_saida_so_para_locacao_aguardando_retirada`<br>`test_vis_01_avaria_da_saida_e_preexistente_e_sem_valor`<br>+3 testes | 5 | coberta |
| VIS-02 | 1 | `test_vis_02_ca_016_01_lista_pronta_ao_criar`<br>`test_vis_01_vis_02_vis_03_vei_01_ca_016_02_todas_as_pendencias` | 2 | coberta |
| VIS-03 | 1 | `test_vis_01_vis_02_vis_03_vei_01_ca_016_02_todas_as_pendencias`<br>`test_dev_01_vis_03_ca_016_10_combustivel_com_outros_niveis` | 2 | coberta |
| VIS-04 | 1 | `test_vis_04_ca_016_04_concluida_nao_se_edita_e_correcao` | 1 | coberta |
| VIS-05 | 1 | `test_vis_05_ca_016_08_agenda`<br>`test_vis_05_agenda_com_todas_as_filiais_pede_uma` | 2 | coberta |
| DEV-01 | 1 | `test_dev_01_vis_03_ca_016_10_combustivel_com_outros_niveis`<br>`test_dev_01_ca_016_10_sem_tanque_ou_sem_preco_vira_informado`<br>+6 testes | 8 | coberta |
| DEV-02 | 1 | `test_dev_02_ca_016_11_saldo_negativo_vira_conta`<br>`test_dev_02_ca_016_22_parcela_que_nao_cabe_vai_para_renegociada`<br>+3 testes | 5 | coberta |
| DEV-03 | 1 | `test_dev_03_ca_016_09_acerto_loc_2836` | 1 | coberta |
| DEV-04 | 1 | `test_dev_04_dev_06_ca_016_17_encerrar`<br>`test_dev_04_vai_para_oficina_leva_a_em_manutencao` | 2 | coberta |
| DEV-05 | 1 | `test_dev_05_ca_016_16_salvar_e_continuar_depois`<br>`test_dev_05_devolucao_so_de_locacao_ativa` | 2 | coberta |
| DEV-06 | 1 | `test_dev_04_dev_06_ca_016_17_encerrar` | 1 | coberta |
| DEV-07 | 1 | `test_dev_07_ca_016_23_antes_do_fim_sem_aprovacao_recusa`<br>`test_dev_07_ca_016_23_no_dia_do_fim_antes_da_hora_nao_e_antecipada`<br>+10 testes | 12 | coberta |
| DEV-08 | 1 | `test_dev_08_seed_019_11_factor_e_nmax`<br>`test_dev_08_km_de_saida_igual_na_ficha_e_na_devolucao`<br>+1 testes | 3 | coberta |
| VEN-01 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-02 | 2 | `test_ven_02_seed_019_31_venda_ven_0177` (xfail) | 1 | xfail · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-03 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-04 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-05 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-06 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-07 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-08 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-09 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| VEN-10 | 2 | — | 0 | fase 2 · Vendas inteiras são fase 2 (regras, "Mudanças em 25 out 2026"; `apps/vendas` é só README) |
| FIN-01 | 1 | `test_fin_01_ca_017_01_estados_pela_data`<br>`test_fin_01_ca_017_03_em_aberto_dos_clientes`<br>+6 testes | 8 | coberta |
| FIN-02 | 1 | `test_fin_02_ca_017_02_faixas_de_atraso` | 1 | coberta |
| FIN-03 | 1 | `test_fin_03_juros_pro_rata_com_um_arredondamento_so`<br>`test_dev_01_fin_03_ca_016_13_parcela_com_multa_e_juros`<br>+6 testes | 8 | coberta |
| FIN-04 | 1 | `test_fin_04_ca_017_05_baixa_no_caixa_em_dinheiro`<br>`test_fin_04_aut_05_ca_017_07_webhook_do_pix_baixa_sozinho`<br>+37 testes | 39 | coberta |
| FIN-15 | 1 | `test_fin_07_fin_15_caixa_hoje_no_painel_do_administrador`<br>`test_fin_15_seed_019_20_contas_a_receber_de_outubro`<br>+12 testes | 14 | coberta |
| FIN-05 | 1 | `test_fin_05_fin_06_ca_017_19_despesas_de_outubro`<br>`test_fin_05_apr_03_ca_017_20_limite_de_500`<br>+7 testes | 9 | coberta |
| FIN-06 | 1 | `test_fin_05_fin_06_ca_017_19_despesas_de_outubro`<br>`test_fin_06_aud_05_ca_017_22_nota_e_veiculo`<br>+4 testes | 6 | coberta |
| FIN-16 | 1 | `test_fin_16_despesa_por_veiculo_no_seed`<br>`test_fin_16_busca_descricao_e_placa`<br>+9 testes | 11 | coberta |
| FIN-07 | 1 | `test_fin_07_ca_016_18_devolucao_em_dinheiro_exige_caixa`<br>`test_fin_07_ca_017_12_um_caixa_por_filial_por_dia`<br>+12 testes | 14 | coberta |
| FIN-08 | 1 | `test_fin_08_aut_08_ca_017_16_fechamento_automatico` | 1 | coberta |
| FIN-09 | 2 | `test_fin_09_ca_015_25_comissao_da_locacao_nova`<br>`test_fin_09_ca_015_25_estorno_e_renovacao_sem_comissao` | 3 | coberta (fase 2 já com teste) · Comissões, fase 2 (T-356) |
| FIN-10 | 2 | — | 0 | fase 2 · Comissões, fase 2 (T-356) |
| FIN-11 | 2 | — | 0 | fase 2 · Conciliação, fase 2 |
| FIN-12 | 2 | `test_fin_12_seed_019_31_conciliacao_diferenca_de_137_10` (xfail) | 1 | xfail · Conciliação, fase 2 |
| FIN-13 | 2 | `test_fin_13_linha_da_locacao_com_pago_sem_caucao_e_tipo_do_veiculo` | 2 | coberta (fase 2 já com teste) · Relatórios e DRE, fase 2 (T-356) |
| FIN-14 | 2 | — | 0 | fase 2 · Relatórios e DRE, fase 2 (T-356) |
| MAN-01 | 2 | — | 0 | fase 2 · Manutenção e OS são fase 2 (regras, planos por módulo) |
| MAN-02 | 2 | — | 0 | fase 2 · Manutenção e OS são fase 2 (regras, planos por módulo) |
| MAN-03 | 2 | `test_man_03_seed_019_10_proxima_troca_de_oleo_aos_19900` (xfail) | 1 | xfail · Manutenção e OS são fase 2 (regras, planos por módulo) |
| MAN-04 | 2 | — | 0 | fase 2 · Manutenção e OS são fase 2 (regras, planos por módulo) |
| MAN-05 | 2 | — | 0 | fase 2 · Manutenção e OS são fase 2 (regras, planos por módulo) |
| MAN-06 | 2 | — | 0 | fase 2 · Manutenção e OS são fase 2 (regras, planos por módulo) |
| APR-01 | 1 | `test_apr_01_ca_015_06_acima_do_limite_gerente_aprova`<br>`test_apr_01_ca_015_06_recusado_volta_a_zero_e_avisa`<br>+6 testes | 8 | coberta |
| APR-02 | 1 | `test_apr_02_ca_015_16_loc_2812_cancelamento_pendente`<br>`test_apr_02_ca_015_21_gerente_cancela_direto`<br>+3 testes | 5 | coberta |
| APR-03 | 1 | `test_fin_05_apr_03_ca_017_20_limite_de_500`<br>`test_apr_03_apr_09_contador_de_despesas`<br>+3 testes | 5 | coberta |
| APR-04 | 1 | `test_fin_07_apr_04_ca_017_15_diferenca_vai_para_o_gerente`<br>`test_apr_12_ca_apr_04_cancelado_nao_muda_numeros_do_seed`<br>+1 testes | 3 | coberta |
| APR-05 | 1 | `test_apr_12_apr_04_ca_apr_05_diferenca_de_caixa_do_rodrigo_aprovada_pela_mariana` | 1 | coberta |
| APR-06 | 1 | `test_apr_06_pedido_repetido_e_pedido_pendente`<br>`test_apr_06_ca_013_16_correcao_para_baixo`<br>+5 testes | 7 | coberta |
| APR-07 | 1 | `test_apr_07_recusar_exige_motivo_e_o_km_fica` | 1 | coberta |
| APR-08 | 2 | — | 0 | fase 2 · Marca "Fase 2" na regra |
| APR-09 | 1 | `test_apr_09_quem_pede_nao_aprova_no_banco`<br>`test_apr_09_ca_015_06_vendedora_com_a_extra_nao_aprova_o_proprio`<br>+9 testes | 11 | coberta |
| APR-10 | 1 | `test_apr_10_pedir_grava_o_pedido_e_a_auditoria`<br>`test_apr_10_cancelar_pendentes_publica_a_decisao`<br>+3 testes | 5 | coberta |
| APR-11 | 1 | `test_apr_03_ca_apr_11_resumo_dos_pneus_com_placa_pmz_3e17` | 1 | coberta |
| APR-12 | 1 | `test_apr_12_desconto_aprovado`<br>`test_apr_12_recusado`<br>+13 testes | 15 | coberta |
| AUT-01 | 1 | — | 0 | FALTA TESTE |
| AUT-02 | 1 | `test_loc_10_ca_015_19_tolerancia_e_diarias` (test_t091_locacao_fim.py) | 0 | outro nome |
| AUT-03 | 1 | `test_aut_03_bloqueio_recupera_dia_perdido`<br>`test_aut_03_texto_d_menos_1`<br>+7 testes | 9 | coberta |
| AUT-04 | 2 | `test_aut_04_asaas_autorizacao_semanal_do_carlos`<br>`test_aut_04_asaas_cobra_a_parcela_pela_autorizacao`<br>+1 testes | 3 | coberta (fase 2 já com teste) · Pix Automático, fase 2 (T-283) |
| AUT-05 | 1 | `test_fin_04_aut_05_ca_017_07_webhook_do_pix_baixa_sozinho`<br>`test_aut_05_t029_pix_pago_no_asaas_baixa_uma_vez`<br>+5 testes | 7 | coberta |
| AUT-06 | 1 | `test_vei_03_aut_06_ca_013_18_vencimento_tira_da_frota_disponivel`<br>`test_vei_03_aut_06_ca_013_28_reservado_ou_em_manutencao_no_vencimento`<br>+1 testes | 3 | coberta |
| AUT-07 | 2 | — | 0 | fase 2 · Preventivas (MAN-03), fase 2 |
| AUT-08 | 1 | `test_fin_08_aut_08_ca_017_16_fechamento_automatico` | 1 | coberta |
| AUT-09 | 2 | — | 0 | fase 2 · Aprovação esquecida (APR-08), fase 2 |
| AUT-10 | 2 | — | 0 | fase 2 · Comissões do mês, fase 2 (T-356) |
| AUT-11 | 1 | — | 0 | FALTA TESTE |
| AUT-12 | 2 | — | 0 | fase 2 · Conciliação (FIN-11), fase 2 |
| AUT-13 | 1 | `test_aut_13_ca_ass_10_lembrete_d3_por_email`<br>`test_aut_13_ca_ass_11_d3_com_o_link_da_pagina_do_cartao`<br>+14 testes | 16 | coberta |
| AUT-14 | 2 | — | 0 | fase 2 · Implantação parada (IMP-06), fase 2 (T-356) |
| AUT-15 | 1 | `test_aut_15_encerra_acessos_de_suporte_vencidos` | 1 | coberta |
| AUT-16 | 2 | — | 0 | fase 2 · Expurgo da auditoria, fase 2 (T-356) |
| AUD-01 | 1 | `test_aud_01_evento_guarda_ator_acao_objeto_antes_depois_ip_aparelho`<br>`test_aud_01_sem_requisicao_o_ator_e_o_sistema`<br>+28 testes | 30 | coberta |
| AUD-02 | 1 | `test_aud_02_expurgo_so_apaga_eventos_com_mais_de_5_anos`<br>`test_aud_02_expurgo_recusa_limite_mais_recente_que_5_anos`<br>+8 testes | 10 | coberta |
| AUD-03 | 1 | `test_aud_03_ca_018_11_suporte_em_destaque`<br>`test_aud_03_ca_018_14_auditoria_de_acessos`<br>+2 testes | 4 | coberta |
| AUD-04 | 1 | `test_mascara_de_cpf_aud_04`<br>`test_aud_04_ca_014_07_mascara_nas_listas`<br>+2 testes | 4 | coberta |
| AUD-05 | 1 | `test_aud_05_aceita_pdf_jpg_e_png_pelo_conteudo`<br>`test_aud_05_recusa_formato_ou_tamanho`<br>+11 testes | 13 | coberta |
| AUD-06 | 1 | `test_aud_06_auditoria_de_pessoa_nao_guarda_nome_nem_documento_completos`<br>`test_aud_06_anonimizar_apaga_o_cifrado_e_troca_o_hash`<br>+1 testes | 3 | coberta |
| AUD-07 | 1 | `test_aud_07_ca_018_13_exportar`<br>`test_aud_07_ca_018_13_backup_completo_pede_2_etapas_recentes`<br>+1 testes | 3 | coberta |
| AUD-08 | 1 | `test_aud_08_aviso_7_dias_antes_e_apagamento_no_90_dia`<br>`test_aud_08_ca_010_11_cancelada_nao_le_nem_escreve`<br>+15 testes | 17 | coberta |
| AUD-09 | 1 | `test_aud_09_ca_014_09_suporte_giro_sempre_mascarado`<br>`test_aud_09_ca_018_06_dados_pessoais_mascarados`<br>+2 testes | 4 | coberta |
