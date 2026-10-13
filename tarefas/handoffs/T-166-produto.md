# T-166 · Decisões da T-019: Rafael ativo e agenda do vistoriador · produto → orquestrador, qa

**O que foi feito:** registrei as duas decisões do dono do produto de 13 out 2026 sobre as `[decisão]` do QA na T-019 (PR #180), as duas na opção A (análise em `C:/Users/Jota/Documents/giro-produto/analise-t019.md`, fora do git).

- `docs/qa/criterios/T-019.md`:
  - CA-019-12: os 51 clientes têm os 4 documentos, o Rafael também (retirou a LOC-2790, `CLI-03`); nenhum fica `incompleto`; Rafael `bloqueado`, os outros 50 `ativo`.
  - CA-019-24: o João não tem nada marcado para 07 out, e a agenda traz um item só, a devolução atrasada da LOC-2790 (fim previsto em 12 set), situação `atrasada`.
  - CA-019-30: Rafael quitando sai de `bloqueado` e volta a `ativo`, porque o cadastro está completo.
  - `VIS-05` na lista de regras do topo.
- `docs/regras-de-negocio.md`:
  - `VIS-05`: a devolução atrasada continua na agenda, todos os dias, até a locação encerrar, com o exemplo do João em 07 out; nota de mudança no fim de "Vistoria e devolução".
  - Caso "Bloqueio" dos dados de referência: Rafael com cadastro completo, LOC-2790 na agenda como devolução atrasada e, quitando, `ativo`; nota de mudança no fim da seção. Nenhum número muda.
  - Tabela "Decisões de 13 out 2026".
- `tarefas/feito.md`: linha da T-166, PR a abrir. A T-166 não chegou a ter seção no backlog.

**Regras cobertas:** VIS-05, CLI-03, CLI-05.

**O que ficou de fora:**
- **QA, no PR #180:** o seed do Rafael ganha os 4 documentos (`seed/carteira.py`, tirar a exceção do `_completar`), o teste `test_fin_03_seed_019_30_multa_e_juros_no_caixa` passa a conferir `ativo`, e saem do backlog da branch as duas linhas `[decisão]` (Rafael e agenda). O teste da agenda (CA-019-24) já confere o item da LOC-2790 e não muda; vale só ajustar o comentário, se quiser citar a `VIS-05`.
- **Texto, sem mudar comportamento (não feito, fica para quando o produto mexer em clientes):** dizer na `CLI-05` que, ao quitar, o cliente volta a `ativo` ou a `incompleto` conforme o cadastro (já está na `APR-05` e na `CLI-09`); trocar o exemplo do Lucas "incompleto" na `CLI-07`, que já não bate com o seed (o Lucas é `ativo` no CA-019-12).

**Próximo passo:** o orquestrador abre o PR da T-166. Sem conflito esperado com o #180: ele não mexe em `docs/qa/criterios/T-019.md` nem nas regras; em `tarefas/feito.md`, cada um acrescenta a própria linha.
