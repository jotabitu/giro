# T-101 · Conta que nasce vencida não cobra atraso antes da confirmação · produto → orquestrador, backend, qa

**O que foi feito:**
- **Regra (`FIN-03`):** item novo "Conta que nasce vencida". O atraso para multa e juros conta a partir do dia seguinte ao dia em que a conta nasceu (na locação, a confirmação), e não do dia seguinte ao vencimento.
  - Dias de atraso = dia do pagamento − o mais tarde entre o vencimento e o dia em que a conta nasceu, em datas de `America/Sao_Paulo`.
  - Só a cobrança muda: o vencimento gravado, o estado e as faixas seguem a `FIN-01` e a `FIN-02`.
- **Registro:** nota de mudança de 09 out no fim da seção de financeiro e linha em "Decisões de 09 out 2026" (opção A). O ponto "Multa da 1ª parcela da LOC-2836" saiu de "Pontos em aberto".
- **Critérios:**
  - **CA-017-23** (novo, `docs/qa/criterios/T-017.md`): parcela 1 da LOC-2836 (32900, vence 30 set, nasce 01 out). Paga em 01 out: multa 0, juros 0, total 32900. Em 02 out: 658 + 11 = 33569. Em 08 out: 658 + 77 = 33635. Carlos e Rafael do CA-017-08 não mudam.
  - **CA-015-15:** passou a citar a `FIN-03` em vez do ponto em aberto.

**Onde:** `docs/regras-de-negocio.md` (`FIN-03`, nota de mudança, "Decisões de 09 out 2026", "Pontos em aberto"), `docs/qa/criterios/T-017.md`, `docs/qa/criterios/T-015.md`, `tarefas/em-andamento.md`.

**Regras cobertas:** `FIN-03`, `LOC-06`. O total pago da LOC-2836 continua R$ 958,00.

**Check:** só documentação; nenhum código, teste ou CSV mudou. Contas conferidas em `Decimal` com `ROUND_HALF_UP`.

**O que ficou de fora:** o código entra na T-017.

**Próximo passo para quem recebe:**
- **Orquestrador:** a T-017 no backlog diz "CA-017-01 a 22"; agora vai até o 23. Não mexi no backlog para não brigar com o PR #97.
- **Backend (T-017):** `juros_pro_rata` e a multa usam a data em que a conta nasceu quando ela é depois do vencimento. Teste com o código no nome, ex.: `test_fin_03_conta_que_nasce_vencida`.
- **QA (T-098):** se houver `xfail` da multa da parcela 1, ele cai quando a T-017 entrar.
