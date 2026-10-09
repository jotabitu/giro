# T-081 · Aprovações: lista e decisão · backend → orquestrador, frontend, qa, arquiteto, produto

**O que foi feito:**
- **Rotas de `docs/api/aprovacoes.md`:**
  - `GET /api/aprovacoes/`, com `?status=` (padrão `pendente`), `?tipo=`, `?minhas=true` e `contagens.pendente`. A ordem é do mais antigo para o mais novo.
  - `POST /api/aprovacoes/{id}/aprovar/`, com `{ motivo? }`.
  - `POST /api/aprovacoes/{id}/recusar/`, com `{ motivo }` obrigatório (`APR-07`). Sem motivo, responde 400 `validacao`.
  - `POST /api/aprovacoes/{id}/cancelar/`, só para quem pediu.
- **Quem decide** (`selectors.QUEM_DECIDE`):
  - `APR-01`: gerente, administrador ou a extra `aprovar_desconto`.
  - `APR-02`: gerente, administrador ou a extra `cancelar_contrato`.
  - `APR-03` a `APR-06`: gerente e administrador.
  - O gerente decide os pedidos das filiais dele. O administrador decide os de todas, inclusive das desativadas.
  - A lista mostra os pedidos que a pessoa decide no `X-Filial`, sem os que ela fez. Com `X-Filial: todas`, mostra todas as filiais do escopo.
- **`APR-09`:**
  - O pedido não aparece na lista de quem pediu (só em `?minhas=true`, com `pode_decidir: false`).
  - Aprovar ou recusar o próprio pedido responde 403 `{ codigo: "APR-09", mensagem: "Outra pessoa precisa decidir este pedido" }`.
  - O `CHECK` do banco da T-013 continua valendo.
- **Erros:** fora do escopo, 404. Pedido já decidido, 409 `transicao_pedido`.
- **Decisão (`APR-10`):**
  - Quem decidiu e quando entram no mesmo `save` e na mesma auditoria da mudança de status (`pedido_aprovacao.aprovar`, `.recusar` e `.cancelar`).
  - Para isso, `comum.estados.transicionar` ganhou `mais_campos`.
  - A decisão publica `aprovacoes.pedido_decidido` na mesma transação. Se o efeito na origem falha, a decisão volta inteira.
- **`APR-06` de ponta a ponta (CA-013-16):**
  - O assinante fica em `veiculos/eventos.py` e chama `services.aplicar_correcao_aprovada`.
  - Ela corrige o km como o gerente faria: grava a leitura de correção com o motivo do pedido e a auditoria `veiculo.corrigir_km`, e publica `veiculos.km_atualizado`.
  - A leitura tem a origem `aprovacao` com o id do pedido, e `por` é quem aprovou.
  - Recusado ou cancelado, o km fica como estava.
- **`GIRO_MODULOS_ATIVOS`:** `aprovacoes` entrou no padrão. O item "Aprovações" aparece no menu de quem decide.

**Onde:**
- `backend/apps/aprovacoes/`: `services.py` (`aprovar`, `recusar`, `cancelar`), `selectors.py` (`QUEM_DECIDE`, `decisor`, `que_decide`, `visiveis`, `representacao`), `api/` e o `README.md`.
- `backend/apps/veiculos/`: `eventos.py`, `services.aplicar_correcao_aprovada`, `apps.py` e o `README.md`.
- `backend/comum/estados.py` (`mais_campos`), `config/urls.py` e `config/settings/base.py`.
- Testes: `tests/aceitacao/test_t081_aprovacoes.py`.
- `docs/api/openapi.yaml`.

**Testes:**
- `test_apr_06_ca_013_16_gerente_aprova_e_o_km_e_corrigido`: João pede, Rodrigo vê e aprova, o km vai a 3.400, com a leitura, o evento e a auditoria. Depois, decidir de novo responde 409.
- `test_apr_07_recusar_exige_motivo_e_o_km_fica`.
- `test_apr_06_km_mudou_depois_do_pedido`: ver a dúvida abaixo.
- `test_apr_09_quem_pediu_nao_decide_o_proprio_pedido`.
- `test_apr_01_a_apr_06_quem_decide_cada_tipo`: inclui as extras da vendedora.
- `test_apr_06_gerente_decide_so_as_suas_filiais`.
- `test_apr_01_a_apr_06_lista_mais_antigo_primeiro_e_filtros`.
- `test_apr_10_quem_pediu_cancela`.
- `test_usr_05_aprovacoes_no_menu_do_gerente`.
- `test_apr_10_pedido_da_empresa_a_nao_aparece_na_b`: isolamento entre empresas.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `385 passed, 21 xfailed`. Antes eram 375 e 21.
- O OpenAPI foi regerado com `--validate`, sem aviso.
- Rodei no Postgres descartável, com `--rm` e `POSTGRES_HOST`.

**Diferenças em relação ao contrato** (para o arquiteto conferir):
1. O evento `aprovacoes.pedido_decidido` leva também `motivo_pedido`, para a origem gravar o motivo de quem pediu. No `APR-06`, ele é o motivo da leitura de correção.
2. No `cancelar`, `decidido_por_id` do evento é quem pediu. No pedido, `decidido_por` fica `null`, porque o `CHECK APR-09` não deixa o aprovador ser quem pediu. Em `cancelar_pendentes`, ele vem `null`.
3. Cancelar o pedido de outra pessoa responde 403 `so_quem_pediu` ("Só quem fez o pedido pode cancelar"). O contrato não dizia.
4. Aprovar não guarda o `motivo` no pedido, porque o modelo só tem `motivo_recusa`. Ele vai para a auditoria e para o evento.
5. `pct` sai como texto com 2 casas (`"8.00"`), como os outros percentuais.
6. O padrão de quem não decide nada (vendedor sem extra, vistoriador e financeiro) é uma lista vazia, com 200. Os próprios pedidos aparecem com `?minhas=true`.

**Dúvida para o produto:** está em `tarefas/backlog.md` com a etiqueta `[decisão]`. É sobre aprovar uma correção de km depois que o km já mudou. Hoje responde 409 `km_mudou` e o pedido continua pendente.

**Falta (fora desta tarefa):**
- O aviso ao gerente quando o pedido nasce, e a quem pediu quando ele é decidido. Isso entra com o app `notificacoes`.
- `APR-08` e `AUT-09` (lembrete de 4 horas úteis) e a tela `Gerente` são da fase 2.

**Próximo passo para quem recebe:**
- **Frontend:** a lista e as ações seguem `docs/api/aprovacoes.md`. Use `pode_decidir` para mostrar os botões e `contagens.pendente` para o sino.
- **QA:** o CA-013-16 pode ganhar a volta: Rodrigo aprova e o km vai a 3.400.
- **Backend:** as próximas origens (T-014 com `APR-05`, T-015 e T-017) assinam `aprovacoes.pedido_decidido` em `<app>/eventos.py`, como `veiculos`.
