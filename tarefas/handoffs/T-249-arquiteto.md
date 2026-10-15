# T-249 · Contratos das decisões de 15 out · arquiteto → orquestrador, backend (T-250), frontend (T-251), segurança (T-252), qa

**O que foi feito:** os contratos seguem as três decisões do dono de 15 out 2026 (regras da T-248). Branch `t-249-contratos-decisoes-15-out`, **empilhada sobre a `origin/t-248-regras-decisoes-15-out`** (PR #241, ainda não mesclado), porque cita a `CLI-10`, a `APR-09` nova e os CA-248, que só existem nela. Mesclar o #241 antes. Só documentos, sem teste para rodar.

**Onde:**
- `docs/api/clientes.md`, **filtro de filial** (`CLI-10`, CA-248-01 a 07):
  - `?filial=<id>` em `GET /api/clientes/`; sem ele, todos os clientes, e o `X-Filial` é ignorado;
  - a filial mostra os clientes com locação nela, em qualquer estado;
  - filial fora do escopo, desativada ou inexistente: 403 `USR-07`, a mesma resposta nos três casos;
  - contagens e indicadores contam dentro do filtro, mas os números de cada cliente continuam os da empresa;
  - o filtro é registrado por `locacoes` (ADR 0015), com `Exists`; índice `(cliente, filial)` em `Locacao`;
  - as opções vêm de `GET /api/filiais/minhas/`; não há rota nova.
- `docs/api/aprovacoes.md`, **administrador decide o próprio pedido** (`APR-09`, CA-248-08 a 11):
  - a exceção é conferida no serviço, pelo perfil de quem decide;
  - campo `PedidoAprovacao.decidido_pelo_solicitante`. **O `CHECK` do banco** passa a ser `aprovador IS NULL OR aprovador <> solicitante OR decidido_pelo_solicitante`, mais um segundo `CHECK` que impede a marca sem a igualdade. O banco não sabe o perfil, mas garante que toda decisão do próprio pedido fica marcada;
  - `pode_decidir` (o campo que já existe) é o "acoes.aprovar" do backlog; entra também `proprio_pedido` na representação e no `pedido_decidido`;
  - a auditoria mostra "Aprovou o próprio pedido" e "Recusou o próprio pedido";
  - os pedidos do administrador entram nos números dele (`que_decide`).
  - Ajustei as frases de `financeiro.md` e `locacoes.md` que diziam "nunca aprova".
- `docs/api/contas.md`, **copiar link do convite** (`USR-01`, CA-248-12 a 16):
  - rota `POST /api/usuarios/{id}/link-convite/`, só do administrador, só para `convite_pendente` (409 `transicao_usuario` nos outros) e 403 `PLT-07` para o suporte;
  - a resposta traz `link`, `expira_em` e `aviso` uma vez, com `no-store`;
  - `gerar_link_convite` invalida os convites anteriores e é a mesma função interna do reenvio;
  - **limite: 5 por hora por pessoa convidada e 20 por hora por administrador**; acima, 429 `muitas_requisicoes` sem gerar nem invalidar nada;
  - evento `usuario.copiar_link_convite` (`seguranca`) sem o token;
  - `acoes` (`reenviar_convite`, `copiar_link_convite`, `cancelar_convite`) nos itens de `GET /api/usuarios/`.
- `docs/decisoes/modelo-de-dados.md`: o índice de `Locacao`, o campo e os `CHECK` de `PedidoAprovacao` e a tabela de restrições.
- `tarefas/backlog.md` (estado da T-249), `tarefas/em-andamento.md` (saiu) e `tarefas/feito.md` (PR a abrir).

**Regras cobertas:** CLI-10, USR-07, APR-09, APR-10, APR-12, FIN-05, USR-01, PLT-07.

**Testes que o contrato pede (T-250):**
- `test_cli_10_lista_filtra_por_filial`, `test_cli_10_lista_ignora_o_seletor` e `test_cli_10_filial_sem_acesso`. O backlog chamava o primeiro de `test_cli_lista_filtra_por_filial`; pus o código da regra no nome, como pede o CLAUDE.md.
- `test_apr_09_administrador_aprova_o_proprio_pedido`, `..._recusa_o_proprio_pedido`, `test_apr_09_gerente_nao_aprova_o_proprio_pedido`, `test_apr_09_permissao_extra_nao_abre_a_excecao` e `test_apr_09_check_exige_a_marca`.
- `test_usr_01_copiar_link_invalida_o_anterior`, `..._convite_vencido`, `..._so_administrador`, `..._limite_por_hora` e `..._evento_sem_token`.

**O que ficou de fora:**
- Nada das três decisões.
- O `acoes` do usuário cobre só os três botões do convite; os outros botões do painel (desativar, reativar, 2 etapas) continuam como estão.
- A migração dos `CHECK` é da T-250 (`RemoveConstraint` e `AddConstraint`; nenhum pedido que já existe tem `aprovador = solicitante`).

**Próximo passo para quem recebe:**
- **Backend (T-250):** as seções "O que muda para as tarefas (T-249)" dos três contratos, e depois o OpenAPI regenerado.
- **Frontend (T-251):** filtro com as opções de `filiais/minhas/`; Aprovar e Recusar só por `pode_decidir`; "Copiar link do convite" por `acoes.copiar_link_convite`, com o `aviso` e sem guardar o link no estado nem no cache.
- **Segurança (T-252):** confere a rota, o limite, o evento e a ausência do token em log.
- **Qa:** CA-248-01 a 16.
- **Orquestrador:** abrir o PR depois do #241.
