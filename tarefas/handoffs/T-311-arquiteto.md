# T-311 · Contrato da baixa com movimentação aberta · arquiteto → orquestrador, backend (T-288), frontend, qa

Origem: decisão do dono (opção B) na T-310, PR #321 (`MOV-03`, CA-246-22 e 23, handoff `tarefas/handoffs/T-310-produto.md`). A branch `t-311-contrato-baixa` saiu da `origin/main` e recebeu a `origin/t-310-baixa-com-movimentacao`, porque o #321 ainda não estava na main.

**O que foi feito:**

- **`docs/api/movimentacoes.md`:**
  - **"Estados":** a baixa é a única exceção a "depois de iniciada, não se cancela", sem rota própria.
  - **Representação:** ganhou `cancelada_em` e `motivo_cancelamento`.
  - **`cancelar/`:** a rota continua só para a `agendada`.
  - **Seção nova "Baixa do veículo com a movimentação aberta":**
    - a movimentação `agendada`, `em_transito` ou `no_local` vira `cancelada` com "Veículo baixado: {motivo}", na mesma transação da baixa;
    - as despesas das paradas ficam em qualquer status, e a parada `no_local` fica sem saída e sem despesa;
    - na transferência, nem `transferir` nem `TransferenciaVeiculo`: o veículo fica na filial de saída;
    - as fotos da chegada ficam guardadas;
    - auditoria: `veiculo.baixar` e `movimentacao.cancelar` com `detalhes.origem = baixa_veiculo`.
  - **"Interface interna":** o assinante do evento novo.
- **`docs/api/veiculos.md`:**
  - **Rota da baixa:** não há 409 pela movimentação. A resposta vem com `movimentacao_aberta: null`.
  - **`acoes.aviso_baixar`:** "A MOV-0001 será cancelada." para o diálogo, ou `null`. O texto vem da API, como o handoff da T-310 pedia.
  - **Evento novo:** `veiculos.veiculo_baixado`, na tabela de eventos.
  - **"Veículo em movimentação" (T-300):** atualizado.

**Decisões técnicas (minhas, sem regra nova):**
- **Como os apps conversam:** `veiculos` não importa `movimentacoes` (ADR 0011). A baixa publica o evento síncrono `veiculos.veiculo_baixado(veiculo_id, motivo_texto)` dentro da transação. O assinante em `movimentacoes/eventos.py` chama `cancelar_pela_baixa`, e se ele falhar, a baixa inteira é desfeita. As travas seguem a ordem de sempre, veículo e depois a movimentação, a mesma de Iniciar e da chegada.
- **Texto do `{motivo}`:** é o rótulo do motivo em minúsculas ("roubo", "perda total", "sucata"), como nos critérios. No `outro`, vai a `descricao` digitada. Se o produto quiser outro texto para o `outro`, muda só essa linha.
- **Agendada:** sai com o mesmo motivo "Veículo baixado: {motivo}". A regra só fixa o motivo da iniciada, e o mesmo texto nas duas evita um caso à parte.
- **Sugestão da T-300 retirada:** o 409 `MOV-03` na baixa só aparecia no handoff da T-300, nunca no contrato. Fica sem efeito.

**Onde:** `docs/api/movimentacoes.md`, `docs/api/veiculos.md`, `tarefas/feito.md`.
**Contrato:** sem rota nova. Campos novos: `cancelada_em`, `motivo_cancelamento` (movimentação) e `acoes.aviso_baixar` (veículo). O OpenAPI muda quando a T-288 implementar.
**Regras cobertas:** MOV-03, MOV-04, MOV-06 (CA-246-22, CA-246-23).

**Próximo passo para quem recebe:**
- **Backend (T-288):** o evento e o assinante, `cancelar_pela_baixa`, os campos novos, `aviso_baixar` e os testes `test_mov_03_baixa_cancela_movimentacao_iniciada`, `test_mov_03_baixa_na_transferencia_nao_transfere` e `test_mov_03_baixa_cancela_agendada`. Vale também um teste de que a falha no assinante desfaz a baixa.
- **Frontend:** o diálogo de baixa mostra `acoes.aviso_baixar` quando vem.
- **QA:** CA-246-22 e 23.
- **Orquestrador:** abrir o PR desta branch, depois do #321 (ela já o contém).
