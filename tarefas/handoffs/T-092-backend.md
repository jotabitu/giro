# T-092 · Troca de veículo durante a locação · backend → orquestrador, frontend, qa, arquiteto, produto

**O que foi feito** (`LOC-09`; `docs/api/locacoes.md` e `docs/api/vistorias.md`):

- **Pedir a troca:** `POST /api/locacoes/{id}/trocar-veiculo/` com `{veiculo_novo_id, motivo}`. Quem pode: administrador, gerente e vendedor. Responde 202 `{troca: {id, status: "pendente", devolucao_vistoria_id, saida_vistoria_id}}`. Na mesma transação:
  - a troca nasce `pendente` (uma por locação) e o veículo novo fica `reservado`;
  - abrem a chegada do veículo atual e a saída do novo, em rascunho;
  - a devolução da locação nasce em `rascunho`, com a chegada do veículo antigo: o acerto é um só;
  - se a caução da nova categoria for maior, a diferença vira conta `caucao` aberta, com vencimento hoje (Juliana: 20000). Caução menor não gera conta: o acerto final desconta da caução total paga.
  - Recusas: 409 `transicao_locacao` fora de `ativa`, 409 `cancelamento_em_andamento`, 409 `troca_pendente`, e 422 `CLI-02`, `FIL-05` e `LOC-03` para o veículo novo.
- **Vistorias da troca:**
  - `POST /api/locacoes/{id}/vistorias/` com `{tipo: "saida"}` devolve a saída do veículo novo (200, o rascunho).
  - A saída do novo só conclui com a diferença paga: 422 `LOC-09`, "Receba a diferença da caução antes de entregar o veículo". Ela também confere os impedimentos da retirada (`CLI-02`, `CLI-03`, `CLI-05`, `VEI-03`) e não chama `registrar_vistoria_saida`.
  - A chegada do antigo não gera conta. A avaria e o combustível dele ficam como itens do acerto, editáveis em `PATCH /api/devolucoes/{id}/acerto/itens/{item_id}/`.
- **Troca concluída** (as duas vistorias concluídas, em qualquer ordem), numa transação:
  - o trecho atual fecha e o novo começa;
  - a locação passa ao veículo novo (`alugado`), com o preço, a diária e a caução da nova categoria;
  - as parcelas em aberto que vencem depois do dia da troca são refeitas (Juliana: 32900 → 44900);
  - o veículo antigo fica `disponivel`, ou `em_manutencao` com "vai para oficina" (`DEV-04`);
  - sai o evento `vistorias.troca_concluida`, com `avarias_para_oficina`;
  - a auditoria grava `locacao.pedir_troca`, `locacao.trocar_veiculo` e `locacao.concluir_troca`, com `LOC-09`.
- **Acerto único:**
  - Depois da troca, `POST /api/locacoes/{id}/devolucao/` devolve a mesma devolução (200), já com a chegada do veículo novo.
  - O acerto soma as avarias e o combustível das chegadas dos veículos trocados. O combustível do trocado traz o nome dele ("Combustível da NMax 160 GEN0001 (faltou 1/2 tanque, ...)"). A caução do acerto é a caução total paga (Juliana: 50000).
  - Com a troca pendente, o acerto traz o aviso `LOC-09` e encerrar responde 409 `troca_pendente`. Sem a chegada do veículo atual concluída, encerrar responde 422 `vistoria_pendente`.
- **Detalhe da locação:** `acoes.trocar_veiculo` fica `false` com uma troca pendente ou um cancelamento em curso.

**Onde:**
- `backend/apps/locacoes/`: o model `TrocaVeiculo` e a migração `0004`; em `services.py`, `pedir_troca`, `preco_da_troca`, `concluir_troca`, `troca_pendente`, `caucao_da_troca_paga` e `vincular_vistorias_da_troca`; em `selectors.py`, `acoes`; o `README.md`.
- `backend/apps/vistorias/`: `ItemAcerto.veiculo` e a migração `0003`; em `services.py`, `trocar_veiculo`, `concluir`, `iniciar_saida`, `iniciar_devolucao`, `recalcular` e `encerrar_devolucao`; a rota, a view e os serializers; o `README.md`.
- `docs/api/openapi.yaml`, regerado.
- `tarefas/backlog.md`: as dúvidas abaixo.

**Testes:**
- `test_loc_09_ca_015_18_troca_de_veiculo` (`test_t015_locacoes.py`) e `test_loc_09_ca_016_15_troca_de_veiculo_acerto_unico` (`test_t016_vistorias.py`) saíram do `xfail` e passam com os números dos critérios.
- No CA-015-18, a LOC-2836 é renovada por 1 semana antes da troca. Pela carteira, as parcelas 1 e 2 já estão pagas, e sem a renovação não haveria parcela aberta depois de 07 out para passar a 44900.
- Novos em `test_t016_vistorias.py`:
  - `test_loc_09_troca_pendente_abre_as_duas_vistorias`: as duas vistorias, a NMax `reservado`, a saída pela rota de saída, a troca repetida, a ação, o aviso, encerrar com a troca pendente e o 422 da caução;
  - `test_loc_09_troca_recusas`: `LOC-03`, o vistoriador com 403 e a locação atrasada com 409;
  - `test_loc_09_segunda_troca_com_caucao_menor_fica_para_o_acerto`: NMax → Street, sem conta, 3 trechos, o combustível da NMax com o nome dela (3200) e a caução de 50000 no acerto.

**Check** (com o `rodar.sh`, na imagem `giro-backend:latest` e no Postgres de teste do worktree):
- `ruff check`, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Rodei só os testes afetados, um arquivo por vez:
  - `test_t015_locacoes.py`: 45 passed;
  - `test_t016_vistorias.py`: 54 passed e 1 xfailed (o CA-016-18, da T-017);
  - `test_t091_locacao_fim.py`: 21 passed;
  - `test_t090_contratos.py`: 16 passed;
  - `test_t056_carteira_outubro.py`, `test_limites_entre_apps.py` e `test_fundacao.py`: passam.
- O resto fica com o CI do PR.
- O OpenAPI foi regerado com `--validate`, sem aviso e só com acréscimos: a rota e os schemas `TrocarVeiculo`, `Troca` e `TrocaPedida`.

**Para o produto** (`tarefas/backlog.md`, com o que o código faz):
1. [decisão] O preço da nova categoria vale pelo dia de hoje, como na renovação. O plano de preço fixo continua se valer para a nova categoria.
2. [decisão] A taxa de combustível de R$ 10,00 é cobrada por veículo que volta com menos combustível. A `DEV-01` diz "uma vez por devolução".
3. [decisão] Nas parcelas refeitas, só a parte do período muda, com o mesmo desconto. O desconto do plano especial por período não é recalculado.
4. [decisão] Não há rota para cancelar uma troca pendente, e a locação com troca pendente não encerra.
5. [decisão] O cancelamento e a renovação continuam permitidos com uma troca pendente.

**Para o arquiteto (diferenças do contrato):**
- A rota `trocar-veiculo` fica em `apps/vistorias/api`, porque abre as duas vistorias (ADR 0011). O caminho é o do contrato.
- `TrocaVeiculo` guarda `vistoria_devolucao_id`, `vistoria_saida_id` e `conta_caucao_id` sem FK, porque `vistorias` fica acima de `locacoes`. Também tem `pedida_por` e `concluida_em`.
- `ItemAcerto` ganhou `veiculo` (FK nula), para separar o combustível de cada veículo.
- Códigos novos: 409 `troca_pendente` (pedir de novo ou encerrar a devolução) e o aviso `LOC-09` em `acerto.avisos`.
- Evento novo: `vistorias.troca_concluida(troca_id, locacao_id, veiculo_antigo_id, veiculo_novo_id, avarias_para_oficina)`, para o app `manutencao` abrir a OS do veículo antigo, como no `vistorias.devolucao_encerrada`.
- O status `cancelada` da troca existe, mas não tem rota (item 4 acima).

**Para o frontend:**
- **Detalhe da locação:** o botão "Trocar veículo" (`acoes.trocar_veiculo`) chama `trocar-veiculo`. O 202 traz os ids das duas vistorias.
- **Vistoria:** a chegada do antigo e a saída do novo usam as telas de sempre. No 422 `LOC-09` da saída, mostre a mensagem e o caminho para receber a conta da caução.
- **Devolução:** com a troca pendente, mostre o aviso de `acerto.avisos`. Depois da troca, `POST .../devolucao/` abre a chegada do veículo novo, e o acerto já traz os itens do antigo.

**Para o qa:**
- O seed (T-105/T-019) pode montar a troca da Juliana pelos serviços: `vistorias.services.trocar_veiculo` e as duas vistorias.
- A agenda do vistoriador (`VIS-05`) ainda não mostra as vistorias da troca. Ela lista retiradas e devoluções pela locação, e a T-092 não pediu isso.

**Próximo passo:** o orquestrador abre o PR.
