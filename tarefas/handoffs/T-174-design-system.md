# T-174 · Tela de Aprovações no repositório de referência · design-system → frontend (T-175), orquestrador

**O que foi feito:** `Aprovacoes-Desktop.dc.html` e `Aprovacoes-Mobile.dc.html` copiados da cópia local do dono para `docs/telas/html/` (só estes dois; nenhuma outra tela foi copiada). Conferidos contra `APR-01` a `APR-11` e o seed Moto Rápida em 07 out 2026 (quarta). `docs/telas/README.md` ganhou a linha da tela (`/aprovacoes`, app `aprovacoes`, APR-01 a APR-11) e a linha do menu `aprovacoes` deixou de dizer "sem tela ainda".

**O que bate com o seed:** VEN-0177 (R$ 22.900 − 8% = R$ 21.068; R$ 1.832 de desconto; entrada 5.000 + 12 × 1.339; comissão R$ 632,04 = 3%); LOC-2812 (NMax mensal R$ 1.590, fim 15 out, 8 dias restantes, multa R$ 84,80, devolve R$ 286,20); Bruna, João Silva, Rodrigo e Mariana; PMZ-3E17; Moto Peças CE e vencimento 15 out iguais à `Despesas`.

**O que foi corrigido (texto, sem mudança de estilo):**
- Despesa dos pneus: "4 pneus" virou "2 pneus", como na `Despesas`, no `Gerente` e na OS-118 (R$ 1.200,00).
- Barra lateral: o contador "5" em Manutenções saiu, para ficar igual à das telas da main (`Gerente`, `Locações`). Resto da barra (itens, ordem, ícones, classes) já era o da main.
- Histórico: "Correção de km · QXA-4B21 · 18.950 → 18.905 km" contrariava o seed (QXA-4B21 está com 18.950 km em 07 out, sem correção); virou RJD-5B38 (Biz do Marcos) com 12.480 → 12.408 km, que é número ilustrativo.

**O que ficou como estava (não vem do seed):** contadores "Aprovadas 23", "Recusadas 3", tempo médio de 38 min, "Descontos aprovados R$ 2.410 em 5 vendas e locações", e as outras decisões recentes (diferença de caixa de R$ 3,50, desconto de 12% na Pop 110i, desbloqueio de Ana Beatriz Lima). São ilustrativos; o frontend deve ligar na API (T-175). Os horários "há 2 h", "há 1 h", "há 40 min" também são ilustrativos. `[decisão]` para o produto só se o seed passar a ter esses números.
**Observação:** o contador "3" do menu bate com os três pedidos pendentes do gerente (VEN-0177, LOC-2812, despesa dos pneus). O `Menu-Mobile` e a `Frota` seguem como estão na main (fora desta tarefa).

**Próximo passo:** frontend (T-175) recria a tela igual a esta referência; orquestrador abre o PR.
