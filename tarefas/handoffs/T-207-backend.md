# T-207 · Vistoriador sem 403 ao abrir a vistoria (D-05 da T-025) · backend → orquestrador, frontend, qa

**O que foi feito:** branch `t-207-vistoriador-403`, a partir da `origin/main`.

- **Origem do 403:** não é a vistoria. Ao concluir a vistoria de saída, a tela leva a `/locacoes/{id}`, e `DetalheDaLocacao.tsx:262` chamava `GET /api/clientes/{id}/` para mostrar o celular e a CNH, usando o 403 para tirar o link do nome. Pela `USR-09` o vistoriador não abre a ficha do cliente, então o 403 está certo e continua.
- **Combinado com o frontend:** a API passa a mandar o que a tela precisa, e a tela deixa de chamar a ficha do cliente. `GET /api/locacoes/{id}/` traz `cliente = { id, nome, celular, cnh_categoria, ficha_liberada }`. `celular` e `cnh_categoria` são `null` se o cadastro não tem; `ficha_liberada` é `true` para os perfis que abrem a ficha (`clientes.selectors.PERFIS_QUE_VEEM`: administrador, gerente, vendedor e financeiro) e `false` para o vistoriador. A lista (`GET /api/locacoes/`) continua com `{ id, nome }`.
- Celular e CNH para o vistoriador seguem a `USR-09` ("nome, celular e se a retirada está liberada", com a CNH), como a vistoria já mandava. Nenhum valor em dinheiro entra.
- Contrato em `docs/api/locacoes.md` (exemplo do detalhe e nota) e `docs/api/openapi.yaml` regenerado (`ClienteDaLocacao` no `LocacaoDetalhe`).

**Regras cobertas:** USR-09.

**Testes:** `tests/aceitacao/test_t015_locacoes.py::test_usr_09_vistoriador_ve_o_cliente_na_locacao_sem_abrir_a_ficha`: na LOC-2841, João recebe o cliente com `ficha_liberada: false` e toma 403 em `/api/clientes/{id}/`; Mariana, Rodrigo, Bruna e Lúcia recebem `ficha_liberada: true` e abrem a ficha; a linha da lista segue só com id e nome. `make backend-check` (ruff, mypy, pytest) verde.

**Para o frontend:** gere o cliente tipado do `openapi.yaml`, tire `clientes.obter` de `DetalheDaLocacao`, use `l.cliente.celular`, `l.cliente.cnh_categoria` e `l.cliente.ficha_liberada` (link e linha "Telefone"), e ajuste o falso e os testes.

**Para o QA:** quando a tela sair, tire o `joao.vigia.conhecer(403, ..., "D-05", ...)` de `frontend/e2e/celular.spec.ts`.

**Próximo passo:** orquestrador abre o PR; o frontend faz a parte da tela (pode ir no mesmo PR ou numa tarefa à parte, a critério do orquestrador).
