# T-216 · Vencimento da fatura na reativação · produto → orquestrador, arquiteto, qa

**O que foi feito:** decidi a observação do fim do handoff da T-211, a pedido do dono do produto (14 out 2026). Com a regra antiga, a equipe reativava a `cancelada` "como na volta da pausa", com a fatura nova vencendo no dia da volta. Se a empresa tinha cancelado na hora (inadimplente ou suspensa) com um período ainda pago, os mesmos dias eram cobrados duas vezes. Branch `t-216-reativacao-periodo`, a partir da `origin/main` (com o #206).

- `docs/regras-de-negocio.md`:
  - `PLT-06`, "Depois do cancelamento": a empresa volta a `ativa` na hora. Se o último período pago ainda não acabou, a fatura nova vence no dia seguinte ao fim dele, e o dia de vencimento não muda. Se já acabou, vence no dia da volta, que passa a ser o dia de vencimento, como antes. A pausada não entra nesse caso, porque a pausa começa no fim do período pago.
  - Dado de referência novo: "Reativação da Moto Rápida no período pago". A FAT-0001 (22 out a 21 nov) está paga e a diferença do upgrade, de R$ 304,84, atrasada. A empresa cancela em 10 nov, a diferença é paga em 15 nov e a reativação é no mesmo dia: `ativa` em 15 nov, e a fatura de R$ 899,00 vence em 22 nov ("Plano Completo · 22 nov a 21 dez"), com o dia 22 mantido.
  - O caso "Reativação da Moto Rápida com fatura em atraso" (reativação em 01 dez, FAT-0002 vencendo em 01 dez) não muda.
  - Notas de mudança e uma linha nova em "Decisões de 14 out 2026".
- `docs/qa/criterios/assinatura.md`: CA-ASS-49.
- `tarefas/backlog.md`: seção da T-216 com uma proposta sem número para o arquiteto.
- `tarefas/feito.md`: linha da T-216, PR a abrir.

**Regras cobertas:** PLT-06, PLT-01.

**Para quem recebe:**
- **Arquiteto:** na `reativar_empresa` (`assinatura.md`, "Mudança de ciclo e reativação pela equipe", e ação `reativar` no `plataforma.md`), o vencimento passa a ser o dia seguinte ao fim do último período de fatura `mensalidade` `paga`, quando esse período ainda não acabou; nesse caso, o `dia_vencimento` fica como está. Se o período já acabou, nada muda.
- **Qa:** `test_plt_06_reativar_no_periodo_pago` (CA-ASS-49), junto com os outros da assinatura.

**Próximo passo:** o orquestrador abre o PR e numera a proposta. Só documentos, sem teste para rodar.
