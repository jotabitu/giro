# T-123 · Código das decisões da troca de veículo · backend → orquestrador, frontend (T-125), qa

**O que foi feito:** o código das decisões da T-121 e da T-124, pelo contrato da T-122 (`LOC-08`, `LOC-09`, `LOC-12`, `DEV-01`, `DEV-02`).

- **Preço guardado no pedido:** a `TrocaVeiculo` grava o período (sem descontos), a diária, a caução e o `preco_do_dia` no pedido. A diferença de caução, as parcelas refeitas, a diária, a caução e a diferença do período saem desse preço, mesmo com a tabela mudando até a conclusão. A migração preenche as trocas antigas pelo dia de `criado_em`.
- **Parcela refeita inteira:** pelo preço novo do período `k` dela, com todos os descontos (`calculo.preco_com_descontos`), mais os extras por período.
  - No mensal em 4 semanais, cada parcela é a quarta parte do mês.
  - Mensal fidelidade: 2º mês 119000 → 159000 (sem desconto), 3º e 4º meses 107100 → 143100.
- **Diferença do período em curso:** calculada na conclusão e guardada na troca (`periodo_*`, `dias_*`, `ja_refeito_centavos`, `diferenca_centavos`). Usa o mesmo período e os mesmos dias restantes do `LOC-12` (`fim.periodo_em_curso`).
  - No mensal em 4 semanais, desconta o que as parcelas refeitas do período já subiram (T-124: 26667 − 20000 = 6667).
  - No acerto, entra um item `diferenca_troca` por troca concluída (`ItemAcerto.troca`). É cobrança se a diferença é positiva e crédito se é negativa. Diferença 0 não gera item.
  - Ao encerrar, a cobrança vira conta `acerto` paga com a caução, e o crédito entra com a caução (`DEV-02`).
- **Cancelar a troca:** `POST /api/locacoes/{id}/trocar-veiculo/cancelar/` (administrador, gerente e vendedor; vistoriador e financeiro recebem 403). Cada peça segue a tabela de `locacoes.md`:
  - a saída e a chegada em rascunho vão para `descartada`, com data e motivo, e respondem 409 `vistoria_descartada` a qualquer edição;
  - a devolução que apontava para a chegada descartada fica com `vistoria = null`, e `POST .../devolucao/` abre uma chegada nova;
  - a chegada concluída fica como a chegada da devolução (`DEV-07`);
  - o veículo novo volta a `disponivel`;
  - a conta de caução aberta vai para `cancelada` (`financeiro.services.cancelar_conta`, nova), e a paga volta no acerto.
  - Recusas: 409 `transicao_troca`, 409 `troca_saida_concluida`, 400 `motivo`.
- **Cancelamento com a troca pendente:** o cancelamento direto e o pedido respondem 409 `troca_pendente`, "Conclua ou cancele a troca antes". O `simular` e a renovação continuam.
- **Detalhe da locação:**
  - `acoes.cancelar` vem `false` com a troca pendente;
  - `acoes.cancelar_troca` vem `true` enquanto a saída do novo não foi concluída;
  - o bloco `troca` traz a troca pendente, e o vistoriador recebe sem `preco` e `caucao`;
  - `devolucao.devolucao_id` agora vem preenchido quando há devolução com chegada. Antes vinha sempre `null`.
- **`forma_devolucao` (nota da T-119):** `Devolucao.forma_devolucao` guarda só a escolha do acerto. Sem escolha, a resposta e o encerramento usam a forma do pedido de encerramento quando ele vale no momento do acerto. Ao encerrar, a forma usada fica gravada.
- Mensagem do 409 ao encerrar a devolução com a troca pendente: "Conclua ou cancele a troca antes de encerrar a devolução.".

**Onde:**
- `backend/apps/locacoes/`:
  - `models.py` e a migração `0005`;
  - `services.py`: `pedir_troca`, `preco_guardado`, `_parcela_refeita`, `_diferenca_do_periodo`, `concluir_troca`, `cancelar_troca` e `cancelar`;
  - `fim.py` (`periodo_em_curso`);
  - `selectors.py` (`acoes`, `_troca`, `trocas_concluidas`);
  - `api/serializers.py`.
- `backend/apps/vistorias/`:
  - `models.py` e a migração `0004`;
  - `services.py`: `cancelar_troca`, `_descartar`, `forma_da_devolucao`, `_item_da_troca`, `calculados`, `recalcular` e `_sincronizar`;
  - `leituras.py` (novo, ADR 0015: o status das vistorias da troca e o `devolucao_id` para o detalhe da locação);
  - `selectors.py`;
  - `api/`.
- `backend/apps/financeiro/services.py` (`cancelar_conta`).
- `docs/api/openapi.yaml`, regerado.

**Contrato:** `docs/api/locacoes.md` (Troca de veículo) e `docs/api/vistorias.md`. O OpenAPI regerado bate com eles: rota de cancelar, `acoes.cancelar_troca`, bloco `troca`, `diferenca_troca` e `vistoria`/`comparacao` nulas na devolução.

**Regras cobertas:** em `backend/tests/aceitacao/test_t123_decisoes_troca.py`, 13 testes:
- `test_loc_09_troca_de_veiculo_loc_2836`: parcela 3 44900; cobranças 23700 (8500 + 3200 + 12000); caução 50000; devolve 26300 por Pix; locação `encerrada`.
- `test_loc_09_preco_guardado_no_pedido`: a tabela muda em 08 out e a troca usa a de 07 out; a diferença em 08 out é 10286.
- `test_loc_09_parcela_refeita_mensal_fidelidade_3o_mes`: 107100 → 143100, e o 2º mês sem desconto.
- `test_loc_09_diferenca_mensal_4_semanais`, com o exemplo da T-124 (6667), e `..._desconta_parcelas_refeitas`.
- `test_loc_09_cancelar_troca_chegada_rascunho`, `..._chegada_concluida`, `..._caucao_aberta`, `..._caucao_paga` e `..._recusas` (inclui o 409 `troca_saida_concluida`).
- `test_loc_12_cancelamento_com_troca_pendente`.
- `test_loc_09_vistoria_descartada_fora_da_agenda`.
- `test_dev_07_forma_da_devolucao_pela_hora_do_acerto`.

Os testes afetados também passam, um arquivo por vez: t015, t016, t091, t111, t011, t056, isolamento, limites entre apps, rotas e permissões. Antes do push rodei `ruff check`, `ruff format --check`, `mypy` e `makemigrations --check`, todos limpos.

**Mudou em teste existente (`test_t016_vistorias.py`):**
- CA-016-15: a troca em 07 out cai no começo do período de 07 a 14 out. O acerto ganha a `diferenca_troca` de 12000: cobranças 20500, devolve 29500, e a conta `acerto` de 12000 fica paga com a caução. O critério CA-016-15 não dá esses totais.
- Na segunda troca no mesmo dia (NMax → Street), entra um crédito de 12000 que anula a cobrança. O saldo continua 38300.
- O CA-015-18 continua com 44900.

**O que ficou de fora:**
- Na diária, a parcela da renovação cobre várias diárias. O número de diárias é deduzido do valor da parcela, porque a parcela não guarda quantas diárias tem. Na diária também não há desconto por período.
- Devoluções antigas guardaram a forma do pedido na criação (T-119). Não mexi nesses dados; elas continuam com a forma gravada.
- `docs/api/locacoes.md` ainda chama de provisório o 409 `troca_saida_concluida`, que a T-124 confirmou. Ajustar o texto é do arquiteto.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR da branch `t-123-decisoes-troca`.
- **Frontend (T-125):** regerar os tipos do OpenAPI. O botão "Cancelar troca" usa `acoes.cancelar_troca`. Mostrar as mensagens da API nos 409 `troca_pendente` e `troca_saida_concluida`. O item `diferenca_troca` vem em `itens` (cobrança) ou em `creditos`. `devolucao.devolucao_id` pode vir `null` depois de uma troca cancelada.
- **QA:** o caso "Troca de veículo LOC-2836" e as quatro combinações do cancelamento estão nos testes acima e podem ir para os critérios.
