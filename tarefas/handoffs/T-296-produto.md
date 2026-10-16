# T-296 · Pix automático da assinatura sem autorização · produto → orquestrador, arquiteto, backend, qa

**O que foi feito:** o dono escolheu a opção B, que era a recomendação do produto. Se a empresa escolheu Pix automático e ainda não autorizou no dia da emissão (5 dias antes), a fatura sai em boleto com Pix por e-mail, como na forma boleto. A escolha do Pix automático continua e vale a partir da fatura seguinte, depois de autorizada.

A branch `t-296-pix-automatico-sem-autorizacao` recebeu a `origin/main` (485b346, com o PR #302).

**Onde:**
- `docs/regras-de-negocio.md`:
  - `PLT-13`: o caso "Pix automático ainda não autorizado", com a linha do e-mail;
  - `PLT-02`: a emissão;
  - nota de mudança da T-296;
  - linha na tabela "Decisões de 16 out 2026".
- `docs/qa/criterios/assinatura.md`: CA-ASS-63.
- `tarefas/backlog.md`: a `[decisão]` trocada pela decisão.
- `tarefas/feito.md`.

**Regras cobertas:** PLT-02, PLT-13.

**Tarefa de backend que sai daqui (para o orquestrador numerar):**

> **Boleto com Pix para o Pix automático ainda não autorizado** · **Agente:** backend · **Depende de:** T-186 parte 2 (PR #302) · **Regras:** PLT-02, PLT-13 · **Critério:** CA-ASS-63 · **Pronto quando:**
> - em `emitir_cobranca_da_fatura`, com a forma `pix_automatico` e a autorização ainda pendente no dia da emissão, a fatura sai como na forma boleto: o boleto com Pix é criado no parceiro, `cobranca_tipo` fica `boleto`, e o e-mail vai nesse dia para o `email_cobranca` e para os administradores. O e-mail leva a linha "Seu Pix automático ainda não foi autorizado. Esta fatura vai por boleto com Pix.";
> - vale para a fatura do período, para a 1ª e para a da diferença do upgrade;
> - a forma continua `pix_automatico` / `aguardando_autorizacao`;
> - autorizada depois, a fatura já emitida em boleto não ganha cobrança pela autorização, nem no vencimento nem depois. Ela segue paga pelo boleto, pelo Pix dele ou pelo "Pagar". A próxima fatura emitida sai pela autorização;
> - com a autorização ativa na emissão, nada muda (`cobrar_com_autorizacao`);
> - testes `test_plt_13_pix_automatico_sem_autorizacao_sai_boleto` e `test_plt_13_autorizado_depois_vale_na_fatura_seguinte` (Moto Rápida: FAT-0001 em boleto em 17 out; autorizada em 20 out; FAT-0002 pela autorização em 17 nov);
> - o texto da linha do e-mail fica com a parte 3 (mensagens da régua), se ela já estiver em curso.

**Para o arquiteto:** em `docs/api/assinatura.md`, "Emissão no parceiro", acrescentar o caso. No `pix_automatico` sem autorização ativa, sai o boleto com Pix e o e-mail, e a fatura emitida assim fica no boleto até o fim. Não muda rota nem OpenAPI.

**O que ficou de fora:** nada da regra. A resposta do `POST faturas/{codigo}/pagar/` sem `meio` (hoje "Pix avulso" para o `pix_automatico`) continua valendo para quem paga pela tela.

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar a tarefa do backend e abrir o PR desta branch.
- **QA:** CA-ASS-63 com o relógio de referência.
