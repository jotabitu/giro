# T-121 · Regras da troca de veículo · produto → orquestrador, arquiteto, backend, frontend, qa

Em 10 out 2026, o dono do produto seguiu todas as recomendações da análise das 5 `[decisão]` da T-092 e do 6º ponto levantado pelo produto (período em curso).

| # | Ponto | Decisão | Onde |
| --- | --- | --- | --- |
| 1 | Preço da nova categoria | **A, com o ajuste:** tabela do dia do pedido da troca, guardada na troca (período, diária, caução) | `LOC-09` |
| 2 | Taxa de R$ 10,00 do combustível | **A:** uma por veículo que volta com menos combustível | `DEV-01` |
| 3 | Parcelas refeitas | **B:** parcela inteira pelo preço novo, com o desconto do vendedor e o plano especial contando desde o começo | `LOC-09` |
| 4 | Troca pendente que não termina | **B:** rota para cancelar a troca, com o destino de cada peça | `LOC-09`, transições do veículo, estados da troca |
| 5 | Cancelamento e renovação com troca pendente | renovação permitida; cancelamento recusado com 409 `troca_pendente` | `LOC-08`, `LOC-12` |
| 6 | Dias restantes do período em curso | **B:** diferença proporcional no acerto final; crédito se a categoria for mais barata | `LOC-09`, `DEV-01`, `DEV-02` |

**O que foi feito:**

- **`docs/regras-de-negocio.md`:**
  - `LOC-09`: preço do pedido guardado, parcela refeita inteira (ex.: Mensal fidelidade no 3º mês, 1.071,00 → 1.431,00), diferença do período em curso, cancelamento da troca pendente e o que acontece com cada peça, renovação e cancelamento com troca pendente.
  - `LOC-08`: renovação permitida com troca pendente. `LOC-12`: 409 `troca_pendente` no pedido e no cancelamento direto.
  - `DEV-01`: taxa por veículo devolvido e o item da diferença do período. `DEV-02`: o crédito da `LOC-09` na ordem do pagamento.
  - Transições do veículo: `disponivel` → `reservado` na troca pedida, `reservado` → `disponivel` na troca cancelada, `alugado` → `disponivel`/`em_manutencao` na troca concluída (veículo antigo).
  - Estados das entidades: Troca de veículo (`pendente`, `concluida`, `cancelada`).
  - Notas de mudança de 10 out (T-121) em Locação, Vistoria e devolução e Dados de referência; linha na tabela de decisões.
  - Caso de referência novo: "Troca de veículo LOC-2836".
- **`tarefas/backlog.md`:** as 5 `[decisão]` da T-092 viraram uma linha de registro; criadas a T-122 (arquiteto) e a T-123 (backend); nota do botão "Cancelar troca" na T-022.

**Caso "Troca de veículo LOC-2836"** (conta conferida):

Juliana renova por 1 semana em 07 out (parcela 3 de 32900 vencendo em 14 out, fim 21 out 18:00) e troca a Factor pela NMax às 18:00, no começo do período de 07 a 14 out. Paga a caução de 20000 (total 50000). A parcela 3 passa a 44900 e é paga em 14 out. A NMax volta em 21 out 18:00, cheia e sem avaria.

| Item do acerto | Valor |
| --- | --- |
| Retrovisor da Factor | 8500 |
| Combustível da Factor (4 L × 550 + 1000) | 3200 |
| Diferença do período de 07 a 14 out ((44900 − 32900) ÷ 7 × 7) | 12000 |
| NMax | 0 |
| **Cobranças** | **23700** |
| Caução | 50000 |
| **Devolver** | **26300** |

Nenhum caso existente muda: "Acerto da devolução LOC-2836" continua em R$ 183,00 e o CA-015-18 em 44900.

**O que o código da T-092 já faz:** preço de hoje (falta guardar no pedido), taxa por veículo, renovação permitida. **O que muda (T-123):** itens 1 (guardar), 3, 4, 5 (cancelamento) e 6.

## Próximo passo para quem recebe

- **Orquestrador:** abrir o PR da T-121 e liberar a T-122.
- **Arquiteto (T-122):** contrato da rota de cancelar a troca (caminho e app pela ADR 0011, perfis, recusas), `acoes.cancelar_troca`, o 409 `troca_pendente` no cancelamento e `acoes.cancelar` `false`, os campos do preço guardado na `TrocaVeiculo` e o item da diferença do período no acerto (com o crédito).
- **Backend (T-123):** código dos itens 1, 3, 4, 5 e 6 com testes com `loc_09`/`loc_12`/`dev_01` no nome e os números acima (`test_loc_09_troca_de_veiculo_loc_2836`, 26300 a devolver; Mensal fidelidade 3º mês 143100).
- **Frontend (T-022):** botão "Cancelar troca" e a mensagem do 409 `troca_pendente` (nota na T-022).
- **QA:** o seed da troca usa o caso novo, separado do "Acerto da devolução LOC-2836".
