# T-236 · Contratos pela T-235 · arquiteto → orquestrador, backend (T-184, T-195, T-185), segurança (T-199), design-system (T-237), frontend, qa

**O que foi feito:** os contratos seguem as decisões do dono de 15 out 2026 (T-235) sobre a revisão da segurança (T-230). Branch `t-236-contratos-apagamento`, **empilhada sobre a `origin/t-235-regras-apagamento`** (PR #235, ainda não mesclado), porque cita a `PLT-16`, a `AUD-08` nova e os CA-ASS-58 a 62 e CA-APR-11, que só existem nela. Mesclar o #235 antes; depois disso, o PR da T-236 mostra só o commit dela. Só documentos, sem teste para rodar.

- `docs/api/assinatura.md`, **"Tomador da fatura"** (M-01, CA-ASS-59):
  - novos campos `tomador_razao_social`, `tomador_cnpj`, `tomador_endereco` (JSON) e `tomador_gravado_em` na `FaturaAssinatura`;
  - um serviço só, `gravar_tomador(fatura)`: grava uma vez, a partir da `Empresa`, e nunca muda depois;
  - o tomador é gravado no primeiro destes momentos: (1) ao pedir a nota; (2) na baixa, quando a emissão está desligada (o caso do MVP); (3) no apagamento;
  - `emitir_nota_fatura` lê o tomador da fatura;
  - a auditoria `empresa.dados_fiscais` no `public` sai sem os valores, e a cópia do endereço da matriz passa a ser gravada nos dois lugares.
- `docs/api/cancelamento.md`, **"O que fica no `public`"** pela opção B (CA-ASS-58 e 60). O passo (c) do `apagar_empresa` tem quatro partes, nesta ordem:
  1. as faturas não canceladas gravam o tomador, e as `atrasada` guardam também o `email_cobranca`;
  2. `anonimizar_pagador` na conta principal (B-01);
  3. saem as linhas de apoio;
  4. a linha da `Empresa` fica só com o CNPJ, o plano, as datas, a cidade e a UF.

  Além disso:
  - a baixa da fatura de empresa apagada acontece só no `public` e limpa o e-mail da fatura;
  - o CNPJ sai quando a última fatura sair pelo prazo de guarda (a tarefa nasce junto com a decisão do prazo).

  O teste `test_aud_08_o_que_fica_no_public` passou a se chamar `test_aud_08_linha_apagada_so_com_cnpj`.
- `docs/api/auditoria.md`, **"Dados da empresa no `public`"** (M-03): nova lista `omitir_no_public` em `Empresa.CAMPOS_AUDITORIA` (razão social, nome de exibição, `endereco_*`, e-mail de cobrança, contato do responsável). Esses valores nunca são gravados no `public`; o schema da empresa continua com eles completos. O `empresa` da `Plat-Auditoria` ganha `cnpj` e `apagada`. Teste: `test_aud_08_auditoria_publica_sem_endereco`.
- `docs/api/plataforma.md`:
  - **CNPJ único só entre empresas não apagadas** (B-02), com restrição parcial;
  - **`situacao_do_cnpj`**, que devolve `em_uso`, `fatura_em_atraso`, `ja_foi_cliente` ou `nova`;
  - na compra de quem já foi cliente (`PLT-16`), a empresa nasce `ativa`, sem teste, com `empresa_anterior`, `dia_vencimento` igual ao dia da compra e a 1ª fatura vencendo hoje;
  - novos erros: 409 `cnpj_em_uso` (agora com mensagem) e 409 `fatura_anterior_em_atraso`;
  - no painel, a empresa apagada aparece com `nome_exibicao` nulo, o CNPJ e o rótulo "Dados apagados", e a empresa nova traz `ja_foi_cliente`;
  - o Django Admin das faturas mostra o tomador e o e-mail da fatura atrasada. Testes: `test_plt_16_compra_de_novo_sem_teste` e `test_plt_16_compra_de_novo_recusada`.
- `docs/api/aprovacoes.md`: o `resumo` do `APR-03` da despesa ganha a célula "Descrição"; o fornecedor e a forma saem por decisão (CA-APR-11). Teste novo: `test_apr_03_resumo_da_despesa`.
- `docs/decisoes/modelo-de-dados.md`: os campos e a restrição novos. `docs/decisoes/0025-...`: nota de 15 out 2026 no item 4.
- `tarefas/backlog.md` (estado da T-236) e `tarefas/feito.md` (PR a abrir).

**Regras cobertas:** AUD-08, PLT-14, PLT-16, PLT-06, PLT-15, APR-03.

**O que muda para a T-184 (o backend já está nela):**
- A `FaturaAssinatura` ganha `tomador_razao_social`, `tomador_cnpj`, `tomador_endereco`, `tomador_gravado_em` e `email_cobranca`. Se a migração da fatura ainda não foi mesclada, os campos entram nela; senão, numa migração nova.
- `plataforma.services.gravar_tomador(fatura)` é chamado na baixa pelo webhook da conta principal. Com a emissão desligada no MVP, é ali que o tomador nasce hoje. No Django Admin, os campos ficam só para leitura.
- O teste `test_plt_14_fatura_guarda_tomador` cobre o caminho da baixa. O caminho da nota fica em `xfail`, junto com o CA-ASS-29, até a T-197.
- O seed e a 1ª fatura não mudam: a FAT-0001 não está paga e nasce sem tomador.
- No sandbox do Asaas, conferir se a atualização do cliente aceita e-mail e telefones vazios e `notificationDisabled`. É o que o `anonimizar_pagador` vai usar no apagamento. Se não aceitar, me avisar, e o contrato passa a remover o cliente.
- A baixa de fatura de empresa apagada (só no `public`, sem transição) é da T-195. Mesmo assim, vale deixar o serviço de baixa sem depender do schema da empresa quando `apagada_em` estiver preenchido.

**Para quem recebe:**
- **T-195 (backend):** o passo (c) em quatro partes, `anonimizar_pagador` na interface e no fake, a baixa da empresa apagada e `omitir_no_public` em `comum.auditoria`. Testes `test_aud_08_*` (CA-ASS-58 e 60).
- **PLT-16 (backend, sem número):** a restrição parcial do CNPJ, `situacao_do_cnpj`, a criação sem teste, `empresa_anterior` e o aviso no Django Admin (CA-ASS-61 e 62). Sugiro juntar à T-195 (só faz sentido depois do apagamento) ou abrir uma tarefa nova; a decisão é do orquestrador.
- **T-185 (rotas):** nenhuma rota muda. O teste que conferia o antes e o depois do `PATCH dados-fiscais/` no `public` passa a conferir no schema da empresa.
- **Backend de aprovações e financeiro (origem `financeiro` do `APR-03`):** a célula "Descrição" e o teste `test_apr_03_resumo_da_despesa`.
- **T-199 (segurança):** a limpeza da linha, o pagador no parceiro e o `omitir_no_public` entram na revisão do apagamento.
- **T-237 (design-system):** aviso na `Compra-Checkout` e cartão da despesa sem fornecedor, como já está na tarefa. Para o painel (fase 2): CNPJ no lugar do nome, "Dados apagados" e "Já foi cliente".
- **Qa (T-204, T-215):** CA-ASS-58 a 62 e CA-APR-11.

**Observações (interpretações minhas, sem mudar regra):**
- Na fatura atrasada paga depois do apagamento, o e-mail sai na baixa. Com a nota ligada, sai logo depois de a nota ser pedida, para a nota ir para esse e-mail. O CA-ASS-60 diz "na baixa", o que vale para o MVP (emissão desligada).
- A recusa `fatura_em_atraso` da `PLT-16` olha só as faturas `atrasada`, como diz a regra.
- `cnpj_em_uso` usa o texto da `PLT-16` em qualquer estado não apagado, não só na `cancelada`.

**Próximo passo:** o orquestrador abre o PR depois do #235.
