# T-176 · Decisões da T-167: busca, exportar e despesa por veículo na tela de Despesas · produto → orquestrador, arquiteto, backend, frontend, design-system, qa

**O que foi feito:** registrei as decisões do dono do produto de 13 out 2026 sobre as três `[decisão]` do frontend na T-167 (análise em `C:/Users/Jota/Documents/giro-produto/analise-t167.md`, fora do git). Recomendações do produto aceitas em busca, vencimento e caixa, diálogo e nota; Exportar e Despesa por veículo entram no MVP por decisão do dono.

- `docs/regras-de-negocio.md`:
  - `FIN-05`: vencimento (começa igual à data); pago no caixa só para quem abre e fecha caixa, até R$ 500 e com o caixa aberto, senão recusado (`APR-03`, `FIN-07` "Abra o caixa do dia para pagar por ele"); pagar, aprovar e recusar no detalhe aberto pela linha, e o pedido também decidido no início do gerente e em `Aprovações`.
  - `FIN-06`: nota obrigatória ao lançar pela tela; a despesa da OS (`MAN-05`) fica para a manutenção (fase 2).
  - `FIN-16` (nova): gasto no mês (sem `recusada`), despesa por veículo (gasto ÷ veículos fora de `vendido` e `baixado` no último dia do mês, ou hoje; meio centavo para cima; sem veículo, sem número), busca (descrição e placa; muda lista e contagens, não indicadores) e Exportar (CSV, administrador e financeiro, placa com hífen, fluxo da auditoria, 6 linhas em outubro).
  - Nota de 13 out 2026 na auditoria: exceção da `AUD-07` no MVP para as despesas em CSV; `Admin-Exportar` continua só com a auditoria.
  - Linha "Números da tela Despesas em 07 out" nos dados de referência (R$ 82,17) e 4 linhas na tabela "Decisões de 13 out 2026".
- `docs/qa/criterios/despesas.md`: CA-DES-01 a CA-DES-19 com o seed (como `manutencao.md`, ganham o número da tarefa quando ela existir).
- `tarefas/backlog.md`: saem as três `[decisão]` da T-167; "Propostas da T-176" (contrato, backend, frontend), sem número; item da T-176 na T-028 para as telas `Despesas-*`. A T-176 não chegou a ter seção própria no backlog.
- `tarefas/feito.md`: linha da T-176, PR a abrir.

**Regras cobertas:** FIN-05, FIN-06, FIN-16, AUD-07.

**Fórmula e número:** R$ 7.066,70 ÷ 86 = R$ 82,1709, mostrado R$ 82,17 (8217 centavos). A referência mostra "R$ 82" sem centavos e muda na T-028, porque todo valor aparece com centavos.

**O que ficou de fora / para quem recebe:**
- **Arquiteto:** ajustar `financeiro.md` e `auditoria.md` (o orquestrador avisa); nome do item da exportação e o texto de `conteudo` ficam com ele.
- **Ajuste do dono no PR #186 (13 out 2026):** o financeiro também exporta as despesas (linha nova na tabela de perfis, `FIN-16`, nota na `AUD-07`, CA-DES-06b e CA-DES-08) e a placa sai com hífen no CSV (PMZ-3E17, CA-DES-06). T-177, T-178 e T-179 ajustadas no backlog.
- O texto de apoio de "A pagar esta semana" ("conta de luz") e o subtítulo "Mensalidade" seguem sem fonte na API; ficam como o frontend fez.

**Próximo passo:** o orquestrador abre o PR da T-176 e numera as propostas. Sem conflito esperado: só documentos.
