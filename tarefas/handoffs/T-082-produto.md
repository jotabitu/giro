# T-082 · Regra e critério da transferência com categoria de filial · produto → orquestrador, backend, qa

**O que foi feito:**
- **`VEI-04`:** quando a categoria do veículo é só da filial de origem (`FIL-04`), a transferência pede a categoria no destino.
  - Ela tem que estar ativa, ser do mesmo tipo de veículo e ser da empresa ou da filial de destino. Sem ela, a transferência é recusada.
  - Categoria da empresa passa direto, e o veículo continua nela.
  - Como só se transfere veículo `disponivel`, nenhuma locação aberta muda de preço. A categoria nova vale a partir da próxima locação (`LOC-01`).
- **Registro:** nota de mudança de 08 out (T-082) e linha nova em "Decisões de 08 out 2026" (opção B).
- **CA-013-27** em `docs/qa/criterios/T-013.md`.
  - O seed não tem categoria de filial, então o teste cria "Street Centro" (diária 4490) e "Street Caucaia" (diária 4990). Esses preços são só do teste.
  - SAK1D39 na Street Centro, transferido para a Caucaia:
    - sem `categoria_id` → 400 `validacao`, e o veículo não sai da Centro;
    - com uma categoria que não vale no destino, desativada ou de carro → 400;
    - com a Street Caucaia → 200 e diária 4990;
    - com a Street 150–160 → 200 e diária 5490.
  - A `TransferenciaVeiculo` e a auditoria guardam a categoria de antes e a de depois.
  - O caso da categoria da empresa usa o CA-013-13: SAK1D39 continua Street 150–160, com diária 5490.

**Onde:** `docs/regras-de-negocio.md` (`VEI-04`, nota de mudança, "Decisões de 08 out 2026"), `docs/qa/criterios/T-013.md` (CA-013-27), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código ou teste mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend.

**O que ficou de fora:** o código e o contrato ficam para a T-083. Hoje, `POST /api/veiculos/{id}/transferir/` em `docs/api/veiculos.md` não tem `categoria_id`.

**Próximo passo para quem recebe:**
- **Backend (T-083):** `categoria_id` opcional no corpo de `transferir`, obrigatório quando a categoria atual é de filial; categoria de antes e de depois na `TransferenciaVeiculo` e na auditoria; teste `test_vei_04_*` do CA-013-27; contrato e OpenAPI.
- **QA:** conferir o CA-013-27 na entrega da T-083.
