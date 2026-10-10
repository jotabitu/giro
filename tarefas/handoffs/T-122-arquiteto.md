# T-122 · Contrato da troca de veículo · arquiteto → backend (T-123), orquestrador, produto, frontend, qa

Contrato das decisões da T-121 (`LOC-08`, `LOC-09`, `LOC-12`, `DEV-01`, `DEV-02`) em `docs/api/locacoes.md` (seção "Troca de veículo") e `docs/api/vistorias.md`, e o modelo em `docs/decisoes/modelo-de-dados.md` (`TrocaVeiculo`, `Vistoria`, `Devolucao`, `ItemAcerto`).

## O que ficou definido

- **Cancelar a troca:** `POST /api/locacoes/{id}/trocar-veiculo/cancelar/`, em `apps/vistorias/api` (ADR 0011), corpo `{ motivo }`. Pode quem pede a troca (administrador, gerente, vendedor); vistoriador e financeiro recebem 403. Responde 200 `{ troca: { id, status: "cancelada", cancelada_em, saida_vistoria, devolucao_vistoria, conta_caucao, devolucao_id } }`.
  - O que acontece com cada peça (tabela em `locacoes.md`):
    - a troca vai para `cancelada`;
    - a saída do veículo novo vai para `descartada`, e o veículo novo, para `disponivel`;
    - a conta da diferença de caução vai para `cancelada` se está aberta; se está paga, fica e volta no acerto;
    - a chegada do antigo em rascunho vai para `descartada`, e a devolução fica com `vistoria = null` até o veículo voltar; a chegada concluída fica como a chegada da devolução (`DEV-07`).
  - A auditoria grava `locacao.cancelar_troca` e `vistoria.descartar`. Nenhum evento de domínio.
  - Recusas: 400 `motivo`, 409 `transicao_troca` (sem troca pendente), 409 `troca_saida_concluida` (provisória, `[decisão]`) e 409 `transicao_locacao`.
- **Cancelamento com troca pendente:** `POST .../cancelar/`, direto ou pedido, responde 409 `troca_pendente`, "Conclua ou cancele a troca antes". O `simular` continua respondendo. A renovação continua permitida.
- **Detalhe da locação:**
  - `acoes.cancelar` vem `false` com a troca pendente;
  - `acoes.cancelar_troca` vem `true` para quem cria, com a troca pendente e a saída do novo ainda não concluída;
  - bloco novo `troca` (a pendente ou `null`), com as duas vistorias, o preço guardado e a conta da caução, sem valores para o vistoriador.
- **Preço guardado na `TrocaVeiculo`:** `valor_periodo_centavos` (sem descontos), `diaria_centavos`, `caucao_centavos` e `preco_do_dia`, gravados no pedido. A diferença de caução e a conclusão usam esses campos, e não a tabela do dia.
- **Diferença do período em curso:** calculada na conclusão e guardada na troca. A conta usa o mesmo período e os mesmos dias restantes de `calcular_encerramento` no dia da troca, com os descontos daquele período. Campos: `periodo_inicio`, `periodo_fim`, `dias_do_periodo`, `dias_restantes`, `periodo_antigo_centavos`, `periodo_novo_centavos`, `ja_refeito_centavos` e `diferenca_centavos` (com sinal).
- **Item do acerto `diferenca_troca`:** um por troca concluída, com `ItemAcerto.troca` (FK nula) e o modo `calculado`.
  - Natureza `cobranca` se a diferença é positiva e `credito` se é negativa, com o valor sempre positivo. Diferença 0 não gera item.
  - Descrição: "Diferença do período de 07/10 a 14/10 na troca pela Yamaha NMax 160 GEN0001 ((R$ 449,00 − R$ 329,00) ÷ 7 × 7 dias)".
  - O crédito entra com a caução na ordem da `DEV-02`.
- **Diferenças da T-092, aprovadas e registradas no contrato:**
  - a rota em `vistorias/api`;
  - os ids das vistorias e da conta sem FK na `TrocaVeiculo`;
  - `ItemAcerto.veiculo`, com a taxa do combustível por veículo;
  - 409 `troca_pendente` e o aviso `LOC-09` no acerto;
  - o evento `vistorias.troca_concluida`, ainda sem assinante;
  - a mensagem do 409 ao encerrar a devolução passa a ser "Conclua ou cancele a troca antes de encerrar a devolução.".
- **Nota da T-119 (precisa de ajuste, pequeno):** `iniciar_devolucao` decide a `forma_devolucao` pela hora em que a devolução foi aberta, e o acerto decide pela hora da chegada. O dinheiro não muda, mas a forma sai errada em dois casos:
  - a devolução aberta antes do dia do fim e concluída nele leva a forma do pedido, e não é antecipada;
  - a devolução aberta antes da aprovação, ou pela troca, fica sem forma, e é antecipada.
  - Contrato novo: `Devolucao.forma_devolucao` guarda só a escolha do `PATCH`. Sem escolha, a resposta e o encerramento usam `cancelamento_forma` quando `encerramento_antecipado_vale(locacao, momento_da_devolucao(chegada))`. Coloquei esse ajuste na T-123, e o orquestrador decide se ele fica lá.

## Passos para o backend (T-123)

1. **Migração de `locacoes`:**
   - campos novos da `TrocaVeiculo`: os do preço, os da conclusão e os do cancelamento (`cancelada_em`, `cancelada_por`, `motivo_cancelamento`);
   - os campos do preço preenchidos nas trocas existentes com `preco_vigente` do dia de `criado_em`;
   - `pedir_troca` grava o preço, e `concluir_troca` usa o guardado no lugar de `preco_da_troca`.
2. **`_parcela_refeita`:** refaz a parcela inteira, com `calculo.preco_com_descontos(entrada com o período da troca, k)` mais os extras. No 4 semanais, cada parcela é a quarta parte. Teste `test_loc_09_parcela_refeita_mensal_fidelidade_3o_mes`, de 107100 para 143100, e o 1º mês sem desconto.
3. **`concluir_troca` calcula e grava a diferença**, reaproveitando `fim.periodo_em`, `diarias_nao_usadas` e `proporcional`. `ja_refeito_centavos` soma, só no mensal em 4 semanais, o quanto mudaram as parcelas refeitas que vencem antes de `periodo_fim`.
   - Selector `locacoes.selectors.trocas_concluidas(locacao)`.
   - Teste com a tabela mudando entre o pedido e a conclusão.
4. **`vistorias`:**
   - migração com `Vistoria.status` `descartada`, `descartada_em`, `motivo_descarte`, `Devolucao.vistoria` nula e `ItemAcerto.troca`;
   - os filtros de rascunho, agenda e `_chegadas` ignoram as descartadas, e `PATCH`, fotos, avarias e concluir respondem 409 `vistoria_descartada`;
   - `iniciar_devolucao` e `_chegada_do_veiculo_atual` abrem uma chegada nova quando `vistoria` é nula;
   - `recalcular` e o serializer aceitam `vistoria` nula;
   - `calculados` ganha um item `diferenca_troca` por troca concluída, com a chave `(tipo, troca_id)` no `_sincronizar`.
5. **Rota de cancelar:** `vistorias.services.cancelar_troca` (vistorias e devolução), que chama `locacoes.services.cancelar_troca` (troca, veículo novo, conta). Para a conta, `financeiro.services.cancelar_conta(conta_id, motivo, regra)` é nova: `cancelar_abertas` cancela todas as contas da origem.
   - Testes: `test_loc_09_cancelar_troca_chegada_rascunho`, `..._chegada_concluida`, `..._caucao_aberta` e `..._caucao_paga` (a caução paga volta no acerto), mais a recusa com a saída concluída.
6. **`_pode_cancelar`** recusa com 409 `troca_pendente` antes do perfil, no pedido e no direto. A renovação continua.
   - `acoes`: `cancelar` `false` e `cancelar_troca`, mais o bloco `troca` no detalhe.
   - Teste `test_loc_12_cancelamento_com_troca_pendente`.
7. **`forma_devolucao`** pela hora do acerto (nota da T-119).
8. **Caso "Troca de veículo LOC-2836":** `test_loc_09_troca_de_veiculo_loc_2836` dá cobranças 23700 (8500 + 3200 + 12000) e devolve 26300. O CA-015-18 continua em 44900. Regere o OpenAPI.

## Para os outros

- **Produto:** duas `[decisão]` e um ajuste de tabela em `tarefas/backlog.md`:
  - cancelar com a saída do novo já concluída;
  - a diferença no mensal em 4 semanais sem cobrar duas vezes as semanas refeitas;
  - o estado `descartada` da Vistoria na tabela de estados.
  - O contrato segue o que está entre parênteses, e a T-123 pode começar com ele.
- **Frontend (T-022):**
  - o botão "Cancelar troca" chama `trocar-veiculo/cancelar/` com o motivo, e aparece quando `acoes.cancelar_troca` vem `true`;
  - no 409 `troca_pendente`, mostre a mensagem que vem da API;
  - o item `diferenca_troca` aparece em itens ou em créditos, conforme `natureza`;
  - `devolucao_id` pode voltar a `null` depois de uma troca cancelada.
- **QA:** o caso novo, mais as quatro combinações do cancelamento (chegada em rascunho ou concluída, caução aberta ou paga).

## Check

Só documentação. Conferi as rotas, os serviços e os nomes contra o código da T-092 (`locacoes/services.py`, `vistorias/services.py`, `vistorias/api/urls.py`) e os números do caso contra as regras.
