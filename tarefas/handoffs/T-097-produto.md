# T-097 · Dados de referência: LOC-2836 confirmada em 01 out · produto → orquestrador, qa, backend

**O que foi feito:**
- **Dados de referência:** linha nova "Preço da LOC-2836".
  - Juliana, Factor 150, semanal com início em 30 set e fim em 07 out, confirmada em 01 out.
  - Paga R$ 329,00 pela tabela da Street de 01 out (`LOC-15`), com parcelas vencendo em 30 set e 07 out.
  - A `LOC-06` ganhou as datas no exemplo. O "Total pago LOC-2836" continua R$ 958,00.
- **Registro:** nota de mudança de 09 out nos dados de referência e linha em "Decisões de 09 out 2026" (opção A).
- **Consequência da decisão:** as contas nascem na confirmação (`docs/api/locacoes.md`, `confirmar`), e por isso nada podia ser pago em 30 set. A retirada (vistoria de saída, contrato e 1º pagamento: parcela 1 e caução) passa para 01 out. Corrigi o "saiu em 30 set" do `T-016.md` para 01 out.
- **Critérios:**
  - **CA-015-15:** a confirmação em 01 out congela `valor_periodo_centavos: 32900` pela tabela. Se fosse confirmada em 30 set, daria 29940.
  - **`T-016.md`:** a saída da LOC-2836 é em 01 out. O km e o tanque não mudam.
- **Carteira de outubro:** não muda. As parcelas, os vencimentos e os status são os mesmos. O pagamento da parcela 1 em 01 out não entra no "Recebido" de outubro, porque ela vence em setembro (`FIN-15`).

**[decisão] nova em "Pontos em aberto":** a parcela 1 vence em 30 set, mas só pode ser paga em 01 out. Pela `FIN-03`, isso cobra multa de 2% (R$ 6,58) e 1 dia de juros, e o total pago passaria de R$ 958,00.
- A) Conta que já nasce vencida só conta atraso a partir do dia seguinte à confirmação.
- B) Cobra pela `FIN-03`, e o caso "Total pago" e o CA-015-15 mudam.
- Padrão: **A**. É multa e juros, então a decisão é do dono.

**Onde:** `docs/regras-de-negocio.md` (`LOC-06`, "Preço da LOC-2836", nota de mudança, "Decisões de 09 out 2026", "Pontos em aberto"), `docs/qa/criterios/T-015.md` (CA-015-15), `docs/qa/criterios/T-016.md` (dados do seed), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código, teste ou CSV mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend.

**O que ficou de fora:** o teste e o `carteira.py` ficam com a T-098.

**Próximo passo para quem recebe:**
- **Orquestrador:** levar a decisão da multa ao dono.
- **QA (T-098):** em `backend/tests/aceitacao/carteira.py`, confirmar a LOC-2836 em 01 out, com o preço pela tabela. `CAUCOES` e o pagamento da parcela 1 passam para 01 out, sem multa (padrão A). Se o código cobrar multa, `xfail` com o motivo até a decisão.
