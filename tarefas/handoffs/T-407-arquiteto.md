# T-407 · ADR 0026 com o env -i e conferência do contas.md · arquiteto → orquestrador

**O que foi feito:**
- `docs/decisoes/0026-leitura-de-documentos-em-pdf.md`, item 4 (M-01): a chamada passa a ser a da T-399 (`/usr/bin/env -i PATH=... LANG=... <python> -I trabalhador.py <tipo>`, aberta pelo `Popen` com o `env=` mantido), com nota de mudança de 28 out 2026 explicando o motivo (a `StdlibIntegration` do sentry-sdk acrescenta `SUBPROCESS_SENTRY_TRACE` e `SUBPROCESS_BAGGAGE` ao `env`). A decisão não foi reaberta. Status da ADR e o teste do ambiente do filho citam a T-399.
- `docs/api/contas.md`: conferi o ajuste da T-404 (PR #443) contra `backend/apps/contas/navegacao.py`. O exemplo do Essencial com Reembolsos (e sem Pendências do pagamento) e o mapa do `GIRO_MODULOS_ATIVOS` com `reembolsos` e `pendencias_pagamento` → `financeiro` batem com o código. Corrigi só o padrão citado de `config/settings/base.py`, que estava sem `auditoria` e `movimentacoes`.

**O que ficou de fora:** nada.

**Próximo passo para quem recebe:** abrir o PR da branch `t-407-adr-0026-contas` (só documentação).
