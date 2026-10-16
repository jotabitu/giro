# T-300 · Quem leva e quem recebe; veículo em movimentação · arquiteto → orquestrador, backend (T-288), frontend (T-289), produto, qa

Origem: dúvidas 1 e 2 do handoff da T-289 (`origin/t-289-movimentacoes-telas`, `tarefas/handoffs/T-289-frontend.md`).

**O que foi feito:**

- **Dúvida 1, quem leva e quem recebe** (`docs/api/movimentacoes.md`, seção nova "Quem leva e quem recebe"):
  - `GET /api/movimentacoes/pessoas/?filial=<id>`: quem pode levar. Usuários ativos ligados à filial de saída, menos o financeiro. Só administrador e gerente; o gerente, só nas filiais dele. Erros: 400 `validacao` em `filial`, 403 `permissao`.
  - `GET /api/movimentacoes/{id}/recebedores/`: quem pode receber na transferência. A filial é a de destino da própria movimentação, sem `?filial=`, para que quem leva (vendedor ou vistoriador) não liste as pessoas de qualquer filial. Perfis: quem pode registrar a chegada dela.
  - Resposta das duas: `{ resultados: [ { id, nome, perfil, perfil_rotulo, eu } ] }`, sem e-mail nem celular, ordenada pelo nome, sem paginação.
  - O administrador conta em todas as filiais ativas, como no seletor (`USR-07`).
  - A validação de `levado_por_id` e `recebido_por_id` usa a mesma função das listas (`contas.selectors.pessoas_da_filial`, em "Interface interna"), para a lista e a recusa não divergirem.
- **Dúvida 2, veículo em movimentação** (`docs/api/veiculos.md`, seção nova "Veículo em movimentação"):
  - Exemplos do veículo `em_movimentacao` (`disponivel` que iniciou) e do `indisponivel` com a movimentação agendada, que mantém o status.
  - `movimentacao_aberta` ganhou `rotulo` e `tom` prontos ("Movimentação agendada", "Em movimentação", "No local de apoio"), para a Frota não montar o texto pelo `status`.
  - `acoes` do veículo `em_movimentacao`: sem transição manual e sem `registrar_km` (o km entra na chegada).
  - `historico_status` com origem `movimentacao`.
  - Filtro novo `?movimentavel=true` em `GET /api/veiculos/` para a escolha do veículo na Nova movimentação: só os que dariam `acoes.movimentar = true`. A tela deixa de oferecer veículo alugado e esperar o 409, que continua como última palavra.

**Onde:** `docs/api/movimentacoes.md`, `docs/api/veiculos.md`, `tarefas/feito.md`. Sem seção no backlog (numerada pelo orquestrador ao pedir).
**Contrato:** 2 rotas novas e 1 filtro novo; o OpenAPI muda quando a T-288 implementar.
**Regras cobertas:** MOV-02, MOV-03, MOV-05, MOV-06, USR-07.

**Item 5 da T-289 (dica "rodou 26 km"):** na minha leitura, não pede campo da API. É a diferença entre o km digitado e o `km_saida`, que a representação já traz. Não é valor, desconto, multa nem status: é formatação, como o "1 h 10 min" do `duracao_minutos`. Para a dica aparecer enquanto a pessoa digita, a conta tem de ser na tela, porque uma chamada à API por tecla não faz sentido. A recusa do km menor continua da API (422 `VEI-01`). Se o produto preferir o "rodou" só depois de confirmar, o caminho é um `km_percorrido` em `chegada` na resposta da conclusão. A decisão é do produto; não mudei o contrato por isso.

**Pontos para o produto (não decidi regra):**
- **Recebedor financeiro:** `recebedores/` inclui o financeiro, porque a `MOV-02` e o contrato da chegada pedem só "um usuário ativo ligado à filial de destino". Se o financeiro não deve receber, muda a lista e a validação juntas.
- **Administrador "ligado" a toda filial:** segui o `USR-07`, em que o administrador vê todas as filiais. Ele pode levar e receber em qualquer filial.
- **Baixar veículo em movimentação:** `acoes.baixar` segue a regra de sempre (qualquer status menos `alugado`). A regra não diz o que acontece com a movimentação aberta de um veículo baixado (ex.: roubado no caminho). Vale uma linha do produto. Até lá, o backend da T-288 pode recusar a baixa com movimentação aberta (409 `MOV-03`), que é o lado seguro.

**Próximo passo para quem recebe:**
- **Backend (T-288):** as duas rotas, `pessoas_da_filial` usada também na validação, `rotulo` e `tom` em `movimentacao_aberta`, `?movimentavel=true` e as `acoes` do veículo `em_movimentacao`. Testes sugeridos: `test_mov_02_pessoas_sem_financeiro`, `test_mov_02_gerente_de_outra_filial_403`, `test_mov_06_recebedores_da_filial_de_destino`, `test_mov_03_movimentavel_exclui_alugado_e_reservado`.
- **Frontend (T-289):** trocar `quemPodeLevar` e `quemPodeReceber` pelas duas rotas; a busca de veículo com `?movimentavel=true`; Frota com `movimentacao_aberta.rotulo` ao lado do `situacao`.
- **Produto:** os três pontos acima e o item 5.
- **Orquestrador:** abrir o PR desta branch.
