# T-084 · Documento vencido com o veículo reservado ou em manutenção · produto → orquestrador, backend, qa

**O que foi feito:**
- **`VEI-03`:** no dia em que vence o CRLV ou o seguro, o veículo `alugado`, `reservado` ou `em_manutencao` não muda de status, e os gerentes da filial recebem uma tarefa urgente (`FIL-02`). A retirada de veículo com CRLV ou seguro vencido é recusada até renovar, na conclusão da vistoria de saída.
- **`AUT-06`:** a linha da tabela diz o que acontece em cada status.
- **`APR-11` (nova, decisão da T-081):** aprovar uma correção de km depois que outra leitura mudou o km responde 409 `km_mudou`, e o pedido continua `pendente`. O gerente recusa, e a correção é pedida de novo a partir do km atual. A leitura mais nova nunca é apagada. O código da T-081 já faz isso.
- **Registro:** notas de mudança de 08 out em Veículos e em Aprovações, e duas linhas em "Decisões de 08 out 2026".
- **CA-013-28** (`docs/qa/criterios/T-013.md`, para a T-085). A `AUT-06` roda às 07:00 de 25 out:
  - RHT9F02 `reservado`, com CRLV vencendo, continua `reservado`, e os gerentes recebem a tarefa urgente;
  - PMZ3E17 `em_manutencao`, com seguro vencendo, continua `em_manutencao`, com tarefa urgente;
  - rodar de novo no mesmo dia não repete as tarefas;
  - IPVA ou rastreador só geram o alerta.
- **CA-016-21** (`docs/qa/criterios/T-016.md`, para a T-016). RHT9F02 reservado, com retirada em 26 out e CRLV vencido em 25 out:
  - concluir a saída responde 422 `VEI-03`, com `detalhes.documentos: ["crlv"]`, e a locação e o veículo não mudam;
  - com o seguro também vencido, vem `["crlv", "seguro"]`;
  - depois de renovar o CRLV, a vistoria conclui;
  - IPVA ou rastreador não impedem a retirada.

  A locação da reserva do RHT9F02 não é do seed: o teste cria.
- **Numeração:** usei CA-013-28 porque o CA-013-27 está na branch `t-082-regra-transferencia`, que ainda não entrou na main.

**Dúvida nova para o dono do produto** (em "Pontos em aberto"): o veículo `em_manutencao` cujo documento venceu durante a OS, ao concluir a OS, voltaria a `disponivel` com o documento vencido, e a `AUT-06` não roda de novo para ele.
- A) Volta para `indisponivel` até renovar.
- B) Volta para `disponivel`, e só a retirada é recusada.
- Padrão: **A**. Com B, a recusa da retirada ainda protege.

**Onde:** `docs/regras-de-negocio.md` (`VEI-03`, `AUT-06`, `APR-11`, notas de mudança, "Decisões de 08 out 2026", "Pontos em aberto"), `docs/qa/criterios/T-013.md` (CA-013-28), `docs/qa/criterios/T-016.md` (CA-016-21 e `VEI-03` na lista de regras), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código ou teste mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend.

**O que ficou de fora:** a linha `[decisão]` da T-079 no backlog fica com o PR #75 do orquestrador.

**Próximo passo para quem recebe:**
- **Orquestrador:** levar a dúvida da manutenção ao dono.
- **Backend (T-085):** tarefa urgente da `AUT-06` para `reservado` e `em_manutencao`, com o teste `test_vei_03_aut_06_*` do CA-013-28.
- **Backend (T-016):** recusa na conclusão da vistoria de saída, com o teste do CA-016-21.
- **QA:** conferir os dois critérios nas entregas.
