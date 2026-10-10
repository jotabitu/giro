# T-119 · Encerramento aprovado com devolução no fim previsto: teste e status final · backend → orquestrador, frontend, qa

**O que foi feito** (decisão do dono, opção A, em `tarefas/handoffs/T-118-produto.md`):

1. **`locacoes.services.encerramento_antecipado_vale(locacao, momento)`:** função nova. Ela diz se o encerramento antecipado aprovado vale, o que só acontece com a devolução antes do dia do fim previsto, no fuso da filial (`DEV-07`). Todos os pontos que antes olhavam só `encerramento_antecipado_aprovado_em` passaram a usá-la:
   - **`locacoes.services.encerrar`:** decide `cancelada` ou `encerrada` pelo dia de `devolvida_em`. Quando o encerramento antecipado não vale, a locação fica `encerrada`, com o motivo "Devolução concluída", sem `cancelada_em` e sem a regra `LOC-12` no evento `locacao.encerrar`. Os dados do pedido aprovado continuam gravados: `encerramento_antecipado_aprovado_em`, `motivo_cancelamento` e a estimativa.
   - **`vistorias.services.iniciar_devolucao`:** a `forma_devolucao` só vem da `cancelamento_forma` quando o encerramento antecipado vale na hora em que a devolução é aberta. Senão, ela fica vazia e é escolhida no acerto, como numa devolução comum.
   - **`vistorias.services.calculados`:** no dia do fim previsto ou depois, o acerto não traz o item `multa_encerramento` nem o crédito. Antes, o item vinha com valor 0.
   - **`vistorias.services.encerrar_devolucao`:** o cancelamento das parcelas que vencem depois do dia da devolução só roda quando o encerramento antecipado vale. Na prática, nada mudou: depois do fim previsto não há parcela a cancelar.
2. **Contrato:**
   - `docs/api/vistorias.md`: a linha `multa_encerramento` (o item não vem no fim previsto ou depois), o status final e o cancelamento das parcelas.
   - `docs/api/locacoes.md`: o fim da seção "Cancelamento e encerramento antecipado".
   - O OpenAPI não muda, porque nenhum serializer mudou.

**Regras cobertas:** DEV-01, DEV-02, DEV-06, DEV-07, LOC-10, LOC-12, FIN-03.

`test_dev_07_encerramento_aprovado_devolucao_no_fim_previsto_sem_multa`: o Carlos (LOC-2841) tem o encerramento aprovado para 07 out e devolve em 28 out às 09:00.
- No acerto: `parcela_aberta` 30818, 30749, 30679 e 30609; nenhuma `multa_encerramento`, nenhum crédito, atraso 0; cobranças 122855, caução 30000 e saldo −92855; botão "Encerrar e cobrar R$ 928,55"; `forma_devolucao` nula; sem avisos.
- Ao encerrar:
  - as parcelas 2 a 5 ficam `renegociada`, e nenhuma conta da locação fica `cancelada`;
  - nasce a conta `acerto` de 92855 com vencimento em 31 out;
  - não há multa nem reembolso;
  - a LOC-2841 fica `encerrada`, sem `cancelada_em`, com o pedido aprovado registrado e o evento "Devolução concluída" sem regra.

`test_dev_07_loc_10_encerramento_aprovado_devolucao_depois_do_fim_previsto`: a variante de 30 out às 09:00.
- No acerto: parcelas 30838, 30769, 30699 e 30629; atraso de 2 diárias, 10980; sem multa de encerramento; cobranças 133915; saldo −103915.
- Ao encerrar: a locação fica `encerrada`, como no caso de 28 out.

O CA-016-24, o CA-016-25 e o CA-016-14 da Patrícia continuam `cancelada`, sem mudar os números.

**Check** (imagem `giro-backend:latest`, um processo por vez; o CI roda a suíte toda):
- pytest de `test_t016_vistorias.py`, `test_t091_locacao_fim.py` e `test_t111_decisoes_t091.py`: `94 passed, 2 xfailed`.
- ruff, `ruff format --check` e mypy nos dois services: limpos.
- Não rodei a suíte inteira.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR.
- **Frontend (T-022):** no acerto de uma locação com o encerramento aprovado e devolvida no fim previsto ou depois:
  - o item `multa_encerramento` não vem;
  - a `forma_devolucao` vem nula até ser escolhida;
  - o status final é `encerrada`.
- **QA:** conferir o caso "Encerramento aprovado e devolução no fim previsto" e a variante. A caução de 30000 da LOC-2841 vai na fixture.
