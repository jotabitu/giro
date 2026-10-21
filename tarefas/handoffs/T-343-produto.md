# T-343 · Cancelar a ativa com o período pago já vencido · produto → orquestrador, backend (T-195), qa

Decisão do dono em 21 out 2026: **opção A**, recomendada pelo produto, para a `[decisão]` que a T-195 levantou (PR #375).

**O que foi feito:**

- **Regra:** o item Ativa da `PLT-06` ganhou o caso "Período pago já acabado". A empresa cancela no dia do vencimento da fatura seguinte, ainda sem pagá-la. Então:
  - o acesso termina na hora e a empresa vira `cancelada` no mesmo dia;
  - a fatura do dia vira `cancelada`, com a cobrança cancelada no parceiro, e não fica devida;
  - não há o que desfazer, e a tela mostra "termina agora".
  Se a fatura do dia já foi paga (o cartão cobrado antes), vale o caso comum: acesso até o fim do período dela.
- **Registro:** nota de mudança na seção Plataforma e a seção nova "Decisões de 21 out 2026". A `[decisão]` está riscada no backlog e a linha da T-343 está em feito.
- **Dados de referência:** "Cancelamento da Moto Rápida" ganhou dois casos:
  - (e) boleto, cancela em 22 nov às 10:00: `cancelada` na hora e a FAT-0002 `cancelada`. Aviso do apagamento em 13 fev 2027 e apagamento em 20 fev 2027.
  - (f) cartão pago às 08:00 do mesmo dia: acesso até 21 dez, `cancelada` em 22 dez e apagamento em 22 mar 2027.
- **Critério:** CA-ASS-69 em `docs/qa/criterios/assinatura.md`, com os dois casos e o teste `test_plt_06_acesso_que_ja_acabou_termina_agora`.

**Onde:** `docs/regras-de-negocio.md`, `docs/qa/criterios/assinatura.md`, `tarefas/backlog.md`, `tarefas/feito.md`.
**Regras cobertas:** PLT-06, AUD-08.

**Próximo passo:**
- **Backend (T-195):** o código já faz A. Confira duas coisas:
  - o caso (f), em que a fatura do dia já foi paga, dá acesso até 21 dez e não "termina agora";
  - a data do apagamento do caso (e) é 20 fev 2027.
- **QA:** CA-ASS-69.
- **Orquestrador:** a branch está empilhada sobre a `t-195-cancelar-pausar` (PR #375). Abra o PR depois dele ou junto.
