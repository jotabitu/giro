# T-213 · Assinatura: endereço e downgrade · arquiteto → orquestrador, backend (T-184, T-185, T-186), frontend (T-187), qa (T-215)

**O que foi feito:** contrato da assinatura ajustado às decisões do dono de 14 out 2026 (T-211). Branch `t-213-contrato-endereco-downgrade`, a partir da `origin/main`. Só documentos.

- `docs/api/assinatura.md` (versão 15 out 2026):
  - **Endereço da nota (`PLT-15`, opção B; CA-ASS-47 e 48).** Nova parte "De onde vem o endereço" em `PATCH dados-fiscais/`: `filiais.services.criar_filial`, quando a filial nasce matriz, chama na mesma transação `plataforma.services.copiar_endereco_da_matriz(endereco)`, que trava a `Empresa` e só grava se ela ainda não tem endereço (cópia única, da primeira filial, venha ela do assistente, da tela de Filiais ou da importação). Editar a filial, `tornar-matriz` e outra matriz depois não mudam a nota; o `PATCH` não muda filial. `endereco: null` no `PATCH` passa a ser recusado (400), para a nota não voltar a esperar. Quando o endereço passa a existir, `on_commit` agenda `plataforma.pedir_notas_pendentes(empresa_id)` (só com a NFS-e ligada). Seed: `endereco` igual ao da Filial Centro (o "Caso do seed" e o exemplo do `GET` deixaram de dizer nulo).
  - **Downgrade agendado (`PLT-04`, opção A; CA-ASS-40 e 41).** Nova seção "Downgrade agendado: conferência e virada": `gerar_faturas`, 5 dias antes, confere de novo (limites e `pendencias_dos_modulos`); não cabe → limpa `plano_proximo`, fatura pelo plano atual, e-mail com o `detalhes` da 422 e auditoria `empresa.mudar_plano_recusado` (ator `sistema`); cabe → fatura pelo plano menor, e o plano só muda no dia do vencimento, por `plataforma.services.aplicar_mudanca_agendada` chamado em `virar_estados` (00:05), sem conferir de novo. Até lá, limites e módulos são os do plano atual. Testes `test_plt_04_downgrade_agendado_deixa_de_caber` e `test_plt_04_downgrade_cabia_na_geracao`.
  - **Desfazer o downgrade depois da fatura gerada** (entre a geração e a véspera): a fatura `aberta` volta ao valor do plano atual e a cobrança no parceiro é refeita, como na troca no teste. Não é regra nova: é o que a `PLT-04` ("desfazer até a véspera") pede quando a fatura já saiu.
  - **Reativação (`PLT-06`, opção A; CA-ASS-46):** saiu a marca `[decisão]`; o 409 `fatura_em_atraso` fica, com o teste `test_plt_06_reativar_so_com_atrasada_paga` e a linha na tabela de erros. O vencimento da fatura nova não mudou aqui: é a T-217.
  - "O que muda para as tarefas abertas" com o bloco "Da T-213".
- `docs/api/filiais.md`: efeito novo do `POST /api/filiais/` (cópia do endereço quando nasce matriz, com o aviso do passo 6); `PLT-15` nas regras.
- `docs/api/plataforma.md`: `copiar_endereco_da_matriz` na interface para os outros apps; a ação `reativar` cita o 409 `fatura_em_atraso`.
- `docs/decisoes/modelo-de-dados.md`: `Empresa.endereco_*` (cópia única, não volta a nulo) e `plano_proximo` (conferido na geração, aplicado no vencimento).

**Regras cobertas:** PLT-04, PLT-06, PLT-15.

**Para quem recebe:**
- **T-184 (backend, faturas e seed):** `copiar_endereco_da_matriz` e a chamada em `criar_filial`; seed com o endereço da Filial Centro nos dados fiscais; `pedir_notas_pendentes` depois do commit. Testes `test_plt_15_endereco_nasce_da_matriz`, `test_plt_15_endereco_da_nota_e_da_filial_separados`.
- **T-185 (backend, rotas):** `PATCH dados-fiscais/` recusa `endereco: null`; `DELETE mudanca-plano/` depois da fatura gerada devolve a fatura ao valor do plano atual; `GET` do seed com endereço.
- **T-186 (backend, régua e estados):** conferência do downgrade em `gerar_faturas` e `aplicar_mudanca_agendada` em `virar_estados`; testes de CA-ASS-40 e 41.
- **T-187 (frontend, dados fiscais):** bloco já preenchido no seed; o formulário troca o endereço inteiro, sem opção de apagar.
- **T-215 (qa):** CA-ASS-40, 41, 46, 47 e 48 com os nomes de teste acima.

**Próximo passo:** o orquestrador abre o PR. Depois desta, a T-217 (reativação no período pago) em branch própria.
