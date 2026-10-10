# T-124 · Regras do contrato da troca de veículo · produto → orquestrador, backend (T-123), qa, frontend

Em 10 out 2026, o dono do produto confirmou as 2 `[decisão]` do arquiteto na T-122 com as opções que o contrato já seguia.

| # | Ponto | Decisão | Onde |
| --- | --- | --- | --- |
| 1 | Cancelar a troca com a saída do veículo novo já concluída | **Recusado** com 409 `troca_saida_concluida`, "O veículo novo já foi entregue. Conclua a troca com a chegada do veículo antigo." | `LOC-09` |
| 2 | Diferença do período em curso no mensal em 4 semanais | **Desconta o que as parcelas refeitas já subiram** (`ja_refeito_centavos`), para não cobrar os mesmos dias duas vezes; nos outros planos não muda nada | `LOC-09` |

**O que foi feito em `docs/regras-de-negocio.md`:**

- `LOC-09`: a recusa do cancelamento com a saída concluída; o desconto das parcelas refeitas no mensal em 4 semanais, com exemplo; a saída em rascunho descartada vira vistoria `descartada`, com data e motivo.
- Tabela de estados das entidades: Vistoria `rascunho`, `concluida`, `descartada`, com a nota do que é `descartada`.
- Nota de mudança de 10 out 2026 (T-124) no fim da seção Locação e linha "Contrato da troca de veículo (T-122, T-124)" na tabela de decisões.
- `tarefas/backlog.md`: as 3 linhas da T-122 viraram uma linha de registro.

**Exemplo do mensal em 4 semanais (conta conferida):** Street mensal R$ 1.190,00 em 4 semanais de R$ 297,50 (15, 22 e 29 set e 06 out), de 15 set a 15 out, trocada pela Scooter premium (mensal R$ 1.590,00) em 25 set.

- Dias restantes: 15 out − 25 set = 20 de 30. Proporcional: 40000 × 20 ÷ 30 = 26666,67 → **26667**.
- Parcelas refeitas (vencem depois de 25 set e antes de 15 out): 29 set e 06 out, de 29750 para 39750 → `ja_refeito_centavos` = **20000**.
- `diferenca_centavos` = 26667 − 20000 = **6667** (R$ 66,67), cobrança.
- Prova: 10 dias da Street (39667) + 20 da Scooter premium (106000) = 145667; pago: 2 × 29750 + 2 × 39750 + 6667 = 145667.

**Para o backend (T-123):** nada muda no contrato. Sugestão de teste: `test_loc_09_diferenca_mensal_4_semanais` com os números acima (6667), e `test_loc_09_cancelar_troca_saida_concluida` com o 409.

**Para o qa:** os dois casos acima entram nos critérios da troca.

**Para o frontend (T-022):** nada novo; o botão "Cancelar troca" já depende de `acoes.cancelar_troca`, que vem `false` com a saída concluída.

## Check

Só documentação. A conta do exemplo fecha com o mês proporcional (R$ 1.456,67). Nenhum caso de referência muda: a Juliana (LOC-2836) é semanal, `ja_refeito_centavos` 0, e a diferença continua R$ 120,00.
