# T-298 · Contrato: emissão da assinatura com o Pix automático pendente · arquiteto → orquestrador, backend (T-297), frontend (T-187), qa

**O que foi feito:**

- `docs/api/assinatura.md`, "Faturas, cobrança e régua":
  - **Emissão no parceiro** virou uma tabela por forma no dia da emissão, com o `cobranca_tipo` de cada linha. Linha nova: `pix_automatico` sem autorização ativa sai como no `boleto`, com o boleto com Pix, o e-mail nesse dia e a linha da `PLT-13`; `cobranca_tipo = boleto` (CA-ASS-63).
  - A fatura emitida assim fica no boleto até o fim. A forma continua `pix_automatico` / `aguardando_autorizacao`. Autorizada depois, a forma vira `ativa`, mas isso não conta como troca de forma: o boleto não é cancelado nem ganha cobrança pela autorização, e a fatura seguinte é que sai pela autorização (Moto Rápida: 17 out, 20 out, 17 nov).
  - **Aviso da autorização do Pix automático**: `autorizacao_id` no `EventoWebhook`, conferência por `consultar_autorizacao` (nunca pelo corpo), `ativa` leva a forma a `ativa` (`assinatura.forma_ativa`, ator `sistema`), e os resultados `autorizacao_<status>`, `autorizacao_desconhecida`, `ja_autorizada` e `status_desconhecido` ficam no `WebhookRecebido`. Tudo como o PR #302 já faz.
  - `POST faturas/{codigo}/pagar/` e "Da T-298" no fim, com o que muda para as tarefas abertas.
- `docs/api/financeiro.md`, "Interface de pagamentos": `consultar_autorizacao` no `Protocol`, `autorizacao_id` e `token` no retorno de `validar_webhook`, o parágrafo do aviso da autorização (só a conta principal no MVP; locação na fase 2 pela T-283; evento do Asaas a conferir no sandbox) e `cobrar_cartao_salvo` chamado só por `cobrar_cartao_guardado`.

**Decisão de contrato (para o backend conferir):** o "Pagar" sem `meio` de uma fatura que já tem o boleto vivo, emitido por falta da autorização, devolve esse boleto, que já traz o `pix_copia_e_cola`. Pelo código de hoje (`_cobranca_pelo_meio` com `MEIO_DA_FORMA[pix_automatico] = "pix"`), ele cancelaria o boleto enviado por e-mail e criaria um Pix avulso. Isso contraria o "fica no boleto até o fim" da T-296. A empresa continua pagando por Pix, pelo Pix do próprio boleto, então a intenção do produto no handoff da T-296 ("Pix avulso continua para quem paga pela tela") se mantém. Fora esse caso, o Pix avulso segue como está. Se o produto discordar, basta tirar a exceção da linha do `pagar/`.

**Onde:** `docs/api/assinatura.md`, `docs/api/financeiro.md`, `tarefas/backlog.md` (seção da T-298 saiu), `tarefas/feito.md`.
**Contrato:** nenhuma rota nova; OpenAPI sem mudança.
**Regras cobertas:** PLT-02, PLT-13 (CA-ASS-63). Os testes ficam com a T-297.
**O que ficou de fora:** o texto da linha do e-mail na régua (parte 3 da T-186). O nome do evento de autorização no sandbox do Asaas segue a conferir (handoff T-186b).

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR desta branch.
- **Backend (T-297):** a linha nova da emissão e a exceção do "Pagar" sem `meio` (`_cobranca_pelo_meio`: com a forma `pix_automatico` e a cobrança viva `boleto`, devolver a cobrança). Vale um teste para isso, junto dos dois da T-297.
- **Frontend (T-187):** nada muda na API.
- **QA:** CA-ASS-63 com o relógio de referência.
