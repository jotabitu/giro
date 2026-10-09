# T-013 · Veículos, categorias, preços, status, km e ocupação · backend → orquestrador, frontend, qa, arquiteto, produto

Esta é a parte 1 da divisão combinada, mais a ida do pedido `APR-06` (ADR 0019). Os documentos e a `AUT-06` ficam na T-079, e a lista e a decisão das aprovações na T-081.

**O que foi feito:**
- **App `veiculos`** (`docs/api/veiculos.md`), com as rotas de veículos, categorias, preços e extras:
  - `GET` e `POST /api/veiculos/`, com as contagens das abas, a busca por placa (com ou sem hífen), modelo e chassi, e a ordem;
  - `GET` e `PATCH /api/veiculos/{id}/`. A ficha traz `ocupacao` e `historico_status`;
  - `corrigir-identificacao`;
  - `bloquear`, `desbloquear`, `colocar-a-venda`, `voltar-para-frota` e `baixar`;
  - `transferir`, `km` e `corrigir-km`;
  - `/api/categorias/`, com editar, desativar, reativar, os preços (`GET`, `POST`, e `PUT` do agendado) e `/api/precos/historico/`;
  - `/api/extras/`, com editar e desativar.
- **Status (`VEI-07`):** `services.transicionar` é o único caminho para mudar o status.
  - Ela confere a tabela das regras e grava o `HistoricoStatusVeiculo` com a origem genérica e a auditoria.
  - Fora da tabela, responde 409 `transicao_veiculo`, com `detalhes = {de, para}`.
  - Ao entrar em `vendido` ou `baixado`, o veículo devolve a vaga do plano; ao sair deles, ocupa a vaga de novo.
  - `receber_na_troca` reaproveita o cadastro pelo chassi.
- **Plano e filiais:**
  - o contador `veiculos` do plano (`PLT-03`);
  - o contador `veiculos` da operação que impede desativar a filial (`FIL-06`);
  - os `indicadores` `veiculos` e `ocupacao_pct` da lista de filiais.
- **Km:**
  - leitura avulsa, só para cima (422 `VEI-01` com a mensagem do CA);
  - correção pelo gerente ou administrador, na hora, com leitura de correção e auditoria;
  - o evento `veiculos.km_atualizado`.
- **`APR-06` pela porta da ADR 0019:**
  - `comum/aprovacoes.py`, com `pedir`, `pendente`, `cancelar_pendentes`, `PedidoRef` e `PedidoPendente`;
  - o model `aprovacoes.PedidoAprovacao`, com `CHECK APR-09` e um `pendente` por origem;
  - `aprovacoes.services.pedir`, com auditoria `APR-10`, registrado no `ready()`.
  - O vistoriador em `corrigir-km` recebe 202 `{ pedido_aprovacao: {id, tipo, status} }`, e o km não muda. Pedir de novo responde 409 `pedido_pendente`.
- **`GIRO_MODULOS_ATIVOS`:** `veiculos` entrou no padrão. `aprovacoes` ainda não entrou, porque falta a lista (T-081).

**Onde:**
- `backend/apps/veiculos/`: `models.py`, `services.py`, `selectors.py`, `api/`, a migração `0001` e o `README.md`.
- `backend/apps/aprovacoes/`: `models.py`, `services.py`, `selectors.py`, `apps.py`, a migração `0001`, `tests/` e o `README.md`.
- `backend/comum/aprovacoes.py`, `config/urls.py` e `config/settings/base.py` (o módulo e o enum `StatusVeiculoEnum`).
- Testes: `tests/aceitacao/test_t013_veiculos.py`, a frota do seed em `tests/aceitacao/frota.py` (86 veículos, contagens do CA-013-01, alugados 20/16/3/3) e `tests/test_limites_entre_apps.py`, que agora recusa `import aprovacoes` nos seis apps de origem.

**Testes:**
- Passam sem xfail: CA-013-01 a 16 e 21 a 26. O CA-013-16 cobre também o 202, o km parado e o 409 `pedido_pendente`.
- Testes extras:
  - isolamento entre empresas;
  - o uso do plano com `vendido` e `baixado`;
  - os obrigatórios da ADR 0019: `pedir` sem implementação falha, 409, `APR-09` no banco e auditoria;
  - `cancelar_pendentes`.
- Os CA-013-17 a 20 continuam xfail com `T-079`.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `375 passed, 21 xfailed`. Antes eram 345 e 43.
- O OpenAPI foi regerado com `--validate`, sem aviso.
- Rodei no Postgres descartável, com `--rm` e `POSTGRES_HOST`.

**Ajustes em testes de outras tarefas:**
- `test_t012_filiais.py`: a fixture `operacao` agora devolve o contador real de veículos depois de usar o falso.
- `apps/plataforma/tests/test_plataforma.py`: o teste do recálculo tira o contador de veículos para continuar testando "item sem contador fica".
- `test_t011_contas.py`: a lista de rotas que o suporte lê ganhou as 6 rotas de leitura de veículos.

**Diferenças em relação ao contrato** (para o arquiteto conferir):
1. `historico_status` traz também `origem_tipo` e `motivo`.
2. `GET /api/extras/` mostra só os ativos, e `?ativo=false` mostra os desativados.
3. O `PUT` do preço agendado responde com o preço e `locacoes_em_andamento_mantidas`, como o `POST`. Quando a data já chegou, responde 409 `preco_ja_vigente`.
4. `acoes.corrigir_km` vem `true` para o vistoriador, porque ele pede a correção. Se o km pedido não for menor que o atual, responde 400: ele usa Registrar km.
5. `tom` da `situacao`: `sucesso` (disponível), `info` (reservado), `solido` (alugado), `alerta` (manutenção) e `neutro` (indisponível, à venda, vendido, baixado). São os mesmos do `falso-frota.ts`.
6. `documentos_resumo` vem `null` até a T-079. O `desbloquear` ainda não confere CRLV e seguro (`VEI-03`, T-079), e o `voltar-para-frota` ainda não confere venda aberta (`VEN-10`).
7. O `PATCH` de categoria também recusa trocar a `filial` com veículos na categoria (422 `categoria_com_veiculos`), para nenhum veículo ficar com categoria de outra filial.
8. A ocupação conta o tempo exato entre as mudanças de status. Com mudanças em dias inteiros, dá o mesmo que contar dias.
9. Ainda não há exportação da frota (`AUD-07`).

**Dúvida para o produto:** está em `tarefas/backlog.md` com a etiqueta `[decisão]`. É sobre transferir um veículo cuja categoria é só da filial de origem.

**Próximo passo para quem recebe:**
- **Frontend:** trocar o `falso-frota.ts` pela API. Os nomes e o formato seguem `tipos-frota.ts`, com as diferenças 1, 4 e 5 acima. As categorias do seed são da empresa (`filial: null`).
- **QA:** a frota do seed está em `tests/aceitacao/frota.py`, e a T-019 pode partir dela. As placas dos não citados são geradas (`GEN0001`…).
- **Backend:** T-079 (documentos, arquivo privado, notificações mínimas e `AUT-06`), depois T-081 (lista e decisão das aprovações, com o assinante do km em `veiculos/eventos.py`).
