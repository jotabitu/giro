# T-186 (parte 1) · Estados da assinatura e virada do dia · backend → orquestrador, qa (T-204, T-215), frontend (T-187), backend (T-195)

Corte aprovado pelo orquestrador em 16 out 2026: a T-186 sai em 3 PRs empilhados. Esta é a parte 1 (branch `t-186-regua-assinatura`, sobre a `t-185b-forma-faturas`, PR #294).

**O que foi feito:**

- **Virada do dia** `plataforma.services.virar_estados`, pela tarefa `plataforma_virar_estados` (Beat, 00:05), idempotente no mesmo dia:
  1. fatura `aberta` vencida vira `atrasada` em D+1 (`fatura_assinatura.atrasar`, ator sistema, `PLT-02`);
  2. o plano agendado vira (`aplicar_mudanca_agendada`, abaixo);
  3. o estado de cada empresa `em_teste`, `ativa` ou `inadimplente`, pela tabela de transições do contrato, cada empresa na sua transação com a `Empresa` travada:
     - `em_teste` no dia seguinte ao fim do teste: com a 1ª fatura paga, `ativa`; sem forma, `suspensa` (CA-ASS-06); com forma e a 1ª atrasada (D+1), `inadimplente` (CA-ASS-05). No dia do vencimento, com forma e sem pagar, segue `em_teste`;
     - `ativa` com fatura atrasada (mensalidade ou diferença do upgrade): `inadimplente`;
     - `inadimplente` no D+15 da atrasada mais antiga: `suspensa`.
- **Volta a `ativa` ao pagar** (`voltar_a_ativa_ao_pagar`, chamada na baixa pelo webhook): `inadimplente` ou `suspensa` sem outra atrasada, ou `em_teste` com a 1ª paga depois do fim do teste, vira `ativa` na hora. Paga uma e com outra atrasada, segue como está, e o D+15 passa a contar da que ficou.
- **Downgrade agendado no dia do vencimento** (`aplicar_mudanca_agendada`, CA-ASS-41, a virada): grava `plano`, `ciclo` e o preço de tabela, limpa `plano_proximo` e `ciclo_proximo` e recalcula o uso, só se a mensalidade do período de hoje já saiu pelo plano e ciclo agendados. Não confere o uso de novo. Auditoria `empresa.mudar_plano` (ator sistema) nos dois lugares. Vale também para a mudança de ciclo pela equipe.
- **Auditoria dos estados nos dois lugares** (`transicionar_empresa`): `empresa.<estado>` no public (pela máquina de estados) e na empresa, com `antes`/`depois` e a regra.
- `Empresa.TRANSICOES`: `em_teste` → `inadimplente` (a tabela das regras já dizia; o model não tinha).
- `comum.estados.MaquinaDeEstados.refresh_from_db` passa a atualizar o status salvo. Sem isso, uma cópia relida depois de outra transação mudar o status (a baixa agora muda o da empresa) não salvava nenhum campo (`test_plt_14_fatura_guarda_tomador` quebrou assim). Teste em `comum/tests/test_estados.py`.

**Onde:** `backend/apps/plataforma/{services,tasks,models}.py` e o `README.md` do app, `backend/config/settings/base.py` (Beat), `backend/comum/estados.py`. Testes: `backend/tests/aceitacao/test_t186_estados.py` (12) e `comum/tests/test_estados.py` (+1).
**Contrato:** sem rota nova; OpenAPI sem mudança.
**Regras cobertas:** PLT-01, PLT-02, PLT-04 (testes `test_plt_01_*`, `test_plt_02_*`, `test_plt_04_downgrade_agendado_vira_no_dia_do_vencimento`, `test_plt_04_downgrade_sem_a_fatura_do_periodo_nao_vira`). Isolamento: `test_plt_02_estados_isolados_por_empresa`.
**Testes rodados:** ruff, ruff format, mypy; `test_t186_estados`, `test_t184_faturas`, `test_t185_assinatura`, `test_t185b_forma_faturas`, `test_t010_plataforma`, `apps/plataforma/tests`, `comum/tests/test_estados` e `test_tarefas`. Suíte toda não rodada (pouca memória).

**O que ficou de fora (partes 2 e 3):**

- **Parte 2 (`t-186b`):** `gerar_faturas` (06:00, 5 dias antes) com a conferência do downgrade (`test_plt_04_downgrade_agendado_deixa_de_caber`, `test_plt_04_downgrade_cabia_na_geracao`, CA-ASS-40 e 41); emissão no parceiro (boleto, Pix automático, página do cartão); cartão guardado no vencimento e uma tentativa a mais (`test_plt_02_cartao_uma_tentativa_a_mais`); a diferença do upgrade no cartão guardado na hora; o aviso de Pix automático autorizado (a forma sai de `aguardando_autorizacao`). Até lá, os testes desta parte criam a fatura do período seguinte por `criar_fatura`.
- **Parte 3 (`t-186c`):** as mensagens da régua `aut_13_regua_assinatura` (09:00): D-3, D0, D+3, D+7 com a tarefa de ligação.
- **T-195:** pausar, cancelar e voltar da pausa entram em `virar_estados` antes das transições daqui; `pausada` e `cancelada` não passam pela virada desta parte.

**Próximo passo para quem recebe:**

- **QA (T-204, T-215):** CA-ASS-03 a 06 e 11 (os estados) e 41 (a virada) com o relógio de referência.
- **Frontend (T-187):** nada muda na API; a `faixa_aviso` e o `somente_leitura` passam a vir dos estados reais.
- **Backend (T-195):** use `transicionar_empresa` para os estados de cancelar e pausar, e entre em `virar_estados` antes de `estado_do_dia`.
