# T-104 · Regra e critérios da LOC-2836 até 14 out · produto → orquestrador, qa, backend

**O que foi feito:** aplicada a opção B decidida pelo dono do produto em 09 out 2026. A LOC-2836 tem 2 semanas, de 30 set 18:00 a 14 out 18:00. Nenhum valor muda; mudam só datas.
- **Regras** (`docs/regras-de-negocio.md`):
  - `LOC-06` diz o período (30 set 18:00 a 14 out 18:00), com nota de mudança na seção Locação.
  - O exemplo do sinal `devolve_hoje` passou a ser "LOC-2836 em 14 out".
  - Dados de referência: o caso "Preço da LOC-2836" diz o fim em 14 out, e há um caso novo, "Fim previsto da LOC-2836": em 07 out ela fica `ativa`, sem sinal, com ação "Abrir", e nenhuma locação do seed devolve hoje; em 14 out ela vem `devolve_hoje`, com ação "Receber devolução" e a devolução às 18:00 na agenda. Nota de mudança no fim da seção.
  - A decisão entrou em "Decisões de 09 out 2026", e o item saiu de "Pontos em aberto".
- **Critérios** (só o texto):
  - CA-015-15: período de 2 semanas até 14 out.
  - CA-015-16: em 07 out, LOC-2836 `ativa`, sem sinal, "Abrir"; com o relógio em 14 out, `devolve_hoje`, "Receber devolução".
  - CA-015-19: fim 14 out 18:00; tabela 14 out 19:00 → 0, 14 out 19:01 → 5490, 15 out 17:59 → 5490, 15 out 18:01 → 10980; `ativa` até 14 out 23:59 e `aut_02` em 15 out 00:00.
  - CA-016-08: em 07 out, a agenda não tem a LOC-2836 (nenhuma devolução prevista no seed); ela aparece na agenda de 14 out às 18:00.
  - CA-016-09: devolução em 14 out às 17:40; o acerto continua R$ 183,00.
  - CA-016-12: chegada em 14 out às 19:01 → 5490; às 19:00 → 0.
  - T-014: Juliana na lista de clientes passa de "LOC-2836, devolve hoje" para "LOC-2836 (devolve em 14 out)".

**Onde:** `docs/regras-de-negocio.md`, `docs/qa/criterios/T-014.md`, `T-015.md`, `T-016.md`, `tarefas/em-andamento.md`.

**Regras cobertas:** `LOC-01`, `LOC-05`, `LOC-06`, `LOC-10`.

**Check:** só documentação. Valores conferidos: total pago R$ 958,00, caixa de 07 out R$ 1.111,90, carteira de outubro e acerto de R$ 183,00 sem mudança. 14 out é quarta-feira, como 07 out, então o horário da filial não muda o CA-015-19.

**O que ficou de fora:**
- **Seed e testes:** ficam para a T-105, com a QA. Até lá, os testes atuais (com o fim forçado em 07 out) continuam passando contra o seed velho, mas não batem com o texto novo.
- **`docs/api/clientes.md`** (do backend): o exemplo de `locacao_atual` da LOC-2836 traz `"detalhe": "devolve hoje"`; com a data de referência 07 out, o certo é sem esse detalhe. Só muda o exemplo, não o código.
- **Telas** (do design-system): `Locacoes`, `Locacao-Detalhe` e `Clientes` mostram "30 set → hoje 18:00" e "Devolve hoje" para a LOC-2836. Pela decisão, o certo é "30 set → 14 out 18:00" e sem "Devolve hoje" em 07 out. Esta `[divergência]` vai para o backlog. Não pus no backlog aqui para não conflitar com o PR #103.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR; registrar a `[divergência]` das telas no backlog para o design-system.
- **QA (T-105):** em `backend/tests/aceitacao/carteira.py`, tirar `FIM_DAS_CONFIRMADAS` e o ajuste de `fim_previsto`; o início da LOC-2836 passa a 30 set 18:00 com 2 períodos. Os testes de CA-015-16, CA-015-19, CA-016-08, CA-016-09 e CA-016-12 passam a usar o relógio em 14 out para a LOC-2836.
- **Backend (T-091):** o CA-015-19 mudou só nas datas; o código de produção não muda.
