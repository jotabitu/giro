# T-117 · Código da devolução depois da data aprovada · backend → orquestrador, frontend, qa

**O que foi feito** (passos 1 a 7 de `tarefas/handoffs/T-116-produto.md`):

1. **A aprovação não cancela parcelas.** Em `_aplicar_cancelamento`, no ramo depois da retirada, saiu o `financeiro.cancelar_abertas(..., vencendo_depois_de=dia)`. O ramo antes da retirada não mudou: cancela tudo na hora, sem multa (`LOC-12`).
2. **O encerramento da devolução é o único que cancela.** O passo de `encerrar_devolucao` já cancelava as parcelas que vencem depois do dia da devolução, em `America/Sao_Paulo`. Agora ele é o único cancelamento. As parcelas que vencem até esse dia entram no acerto como `parcela_aberta` (`DEV-01`).
3. **O acerto recalcula pelo dia da devolução.** `credito_do_encerramento` deu lugar a `locacoes.services.encerramento_na_devolucao(locacao, momento)`. Ela devolve a multa, o crédito e a descrição do crédito, e usa `calcular_encerramento` no momento da chegada, que é o mesmo cálculo de `cancelamento/simular`.
   - O acerto não lê mais `multa_encerramento_centavos` nem `credito_encerramento_centavos`. Esses dois campos ficam como a estimativa do pedido e da aprovação.
   - No mensal em 4 semanais, as parcelas do mês que o encerramento cancela saem de `_parcelas_do_mes_a_cancelar(locacao, dia)`. É a mesma função para a simulação e para o acerto. Ela conta as parcelas que estão em aberto no dia da devolução, e não mais as canceladas na aprovação.
   - A diária continua pela hora real da devolução.
   - Saiu `financeiro.selectors.parcelas_canceladas_vencendo_entre`, que mais nada usava.
4. **Devolução antes do dia pedido:** usa o mesmo caminho, pelo dia da devolução, sem tratamento à parte.
5. **Entre a aprovação e a devolução,** as parcelas vencem, atrasam e acendem `pagamento_atrasado` como qualquer outra. Uma parcela paga nesse intervalo não entra no acerto, porque só entram as que estão em aberto.
6. **Testes:** abaixo.
7. **Contrato:**
   - `docs/api/locacoes.md`: o campo `cancelamento` ganhou `data`, que a API já devolvia. A seção "Cancelamento e encerramento antecipado" agora diz que `multa_centavos` e `devolver_centavos` são a estimativa para `data`, que a aprovação não cancela parcelas e que o acerto recalcula pelo dia da devolução.
   - `docs/api/vistorias.md`: a linha `multa_encerramento` diz "pelo dia da devolução". O texto do `semanas_nao_usadas` no mensal em 4 semanais também.
   - O OpenAPI foi gerado com `--validate` e não mudou.

**Onde:**
- `backend/apps/locacoes/services.py`: `calcular_encerramento`, `_parcelas_do_mes_a_cancelar`, `encerramento_na_devolucao`, `_aplicar_cancelamento`.
- `backend/apps/locacoes/selectors.py`: docstring de `_cancelamento`.
- `backend/apps/vistorias/services.py`: `calculados` e o comentário em `encerrar_devolucao`.
- `backend/apps/financeiro/selectors.py`.

**Regras cobertas:** DEV-01, DEV-07, LOC-12, LOC-13.
- `test_dev_07_ca_016_25_devolucao_depois_da_data_aprovada`: o Carlos é aprovado para 07 out e devolve em 16 out às 10:00.
  - Parcelas 30699, 30629 e 30559; multa 5490 (e não os 5988); cobranças 97377; saldo −67377; botão "Encerrar e cobrar R$ 673,77".
  - Ao encerrar: a parcela 5 fica `cancelada` e as parcelas 2, 3 e 4 ficam `renegociada`. A multa de 5490 é paga com a caução. Nasce a conta `acerto` de 67377, com vencimento em 19 out, vinda das parcelas 2, 3 e 4. Não há reembolso, e a locação fica `cancelada`.
- `test_dev_07_loc_12_ca_016_25_aprovacao_deixa_as_parcelas_4_e_5_em_aberto`:
  - Depois da aprovação, `cancelamento.multa_centavos` é 5988 (a estimativa para 07 out), e as parcelas 4 e 5 continuam `aberta`.
  - Em 15 out, `pagamento_atrasado` está aceso e aparece "R$ 898,20 em aberto" (parcelas 2, 3 e 4).
- O CA-016-24 (36537), o CA-016-14 da Patrícia (8480 e 78620) e o CA-015-29 (26500, e a tabela de 25 set, 05 out e 07 out) continuam verdes, sem mudar os números.
- Dois testes afirmavam a regra antiga e mudaram só no status das parcelas:
  - CA-015-29 (`test_loc_13_ca_015_29_mensal_em_4_semanais_mesmo_saldo_do_mes_a_vista`): depois da aprovação, as parcelas que não foram pagas ficam `aberta`, e não mais `cancelada`.
  - `test_loc_12_encerramento_antecipado_cancela_as_parcelas_seguintes` passou a se chamar `test_loc_12_encerramento_antecipado_aprovado_nao_cancela_parcelas`, com as parcelas 2 e 3 em `aberta`. A comissão continua `confirmada`.
- O CA-015-28 (diária, blocos de 24 h) passou a chamar `encerramento_na_devolucao`, com os mesmos números.

**Check** (com `rodar.sh`, imagem `giro-backend:latest`, um processo por vez):
- ruff, `ruff format --check`, mypy e `makemigrations --check`: limpos.
- pytest: `600 passed, 3 xfailed`. Na entrega da T-114 eram 598 e 3; os dois a mais são os testes novos.

**Leitura para o produto confirmar:** a locação tem o encerramento antecipado aprovado, mas o veículo volta no dia do fim previsto ou depois. Nesse caso, o acerto traz `multa_encerramento` 0 e nenhum crédito, como uma devolução comum. Quando passa do prazo, o atraso da `LOC-10` é cobrado.
- **Por quê:** pela `DEV-07`, a multa vale "sobre o período em curso nesse dia", e no fim previsto não sobra período. A `cancelamento/simular` já responde 409 `sem_dias_restantes` nesse dia.
- **Antes:** a multa congelada da aprovação era cobrada mesmo assim.
- Não há caso de referência para isso, e não abri `[decisão]`. Se o produto quiser outra coisa, vira tarefa.

**O que ficou de fora:**
- O aviso no acerto quando o valor final é diferente da estimativa. A T-116 diz que ele só existe se o produto pedir, por `acerto.avisos`.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR.
- **Frontend (T-022):**
  - no pedido e na aprovação, mostrar a estimativa com `cancelamento.data`;
  - no acerto, mostrar o que a API devolve;
  - as parcelas de uma locação aprovada e ainda não devolvida vêm em aberto ou atrasadas.
- **QA:** validar pelo CA-016-25 e conferir de novo o CA-016-24 e o CA-015-29. A caução de 30000 da LOC-2841 vai na fixture.
