# T-297 · Boleto com Pix para o Pix automático ainda não autorizado · backend → orquestrador, frontend (T-187), qa

**O que foi feito:**
- `emitir_cobranca_da_fatura`: com a forma `pix_automatico` sem a autorização ativa no dia da emissão, a fatura sai como no boleto (`_emitir_boleto`: boleto com Pix no parceiro, `cobranca_tipo = boleto`, e-mail nesse dia para o `email_cobranca` e os administradores). O resultado na `gerar_faturas` é `boleto_sem_autorizacao` (antes, `aguardando_autorizacao` e nada saía). Vale para a fatura do período, a 1ª e a diferença do upgrade, que passam todas por essa função. A forma continua `pix_automatico` / `pendente`.
- `plataforma_enviar_boleto(fatura_id, pix_pendente=False)`: com `pix_pendente`, o e-mail abre com "Seu Pix automático ainda não foi autorizado. Esta fatura vai por boleto com Pix." (`tasks.PIX_AUTOMATICO_PENDENTE`). Parâmetro com padrão, então tarefa já enfileirada continua valendo.
- Autorizada depois, a fatura emitida fica no boleto: a emissão não volta nela (já tem cobrança), e a seguinte sai pela autorização.
- Exceção da T-298 em `pagar_fatura`: sem `meio`, com a forma `pix_automatico` e a cobrança viva `boleto`, devolve o boleto em vez de cancelá-lo por um Pix avulso. Com `meio`, vale o de sempre.
- `test_plt_13_pix_automatico_autorizado_e_cobrado_pela_autorizacao` (T-186b) passou a autorizar em 16 out, antes da emissão, porque em 17 out sem autorização agora sai boleto.

**Onde:** `backend/apps/plataforma/services.py`, `backend/apps/plataforma/tasks.py`, `backend/apps/plataforma/README.md`, `backend/tests/aceitacao/test_t297_pix_pendente.py`, `backend/tests/aceitacao/test_t186b_faturas_cobranca.py`.
**Contrato:** `docs/api/assinatura.md`, "Emissão no parceiro" e `POST faturas/{codigo}/pagar/` (T-298). Sem rota nova, OpenAPI sem mudança.
**Regras cobertas:** PLT-02, PLT-13, CA-ASS-63. Testes: `test_plt_13_pix_automatico_sem_autorizacao_sai_boleto`, `test_plt_13_autorizado_depois_vale_na_fatura_seguinte` (FAT-0001 em boleto em 17 out, autorizada em 20 out, FAT-0002 pela autorização em 17 nov), `test_plt_13_pagar_sem_meio_devolve_o_boleto`, `test_plt_13_boleto_comum_sem_a_linha`.
**Testes rodados:** `test_t297`, `test_t186b`, `test_t186c`, `test_t185b` e `test_t184` (67 passed, 1 xfailed), ruff e mypy do app `plataforma`.
**O que ficou de fora:** o boleto da conta principal sai sem `pix_copia_e_cola` (o adaptador do Asaas e o falso só buscam o Pix na cobrança `pix`). Os testes não afirmam o Pix do boleto. Registrado no backlog para o arquiteto, antes da T-299.
**Branch:** `t-297-boleto-pix-pendente`, empilhada sobre a `t-186c-regua-mensagens` (PR #304), com a `t-298-emissao-pix-pendente` (PR #305) mesclada. Abrir depois dos dois.
**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR depois do #304 e do #305.
- **Frontend (T-187):** nada muda na API. O detalhe da fatura mostra `cobranca.forma = boleto`.
- **Produto (T-299):** a linha nova do e-mail do boleto entra na leitura dos textos.
- **QA:** CA-ASS-63 com o relógio de referência (17 out, 20 out, 17 nov).
