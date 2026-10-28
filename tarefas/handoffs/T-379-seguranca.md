# T-379 · Backend do controle do suporte (PLT-07) · segurança → orquestrador, frontend

A segurança fez esta tarefa no lugar do Backend. O contrato é o da T-358 (`docs/api/contas.md`, "Tela `Admin-Suporte`"; `docs/api/configuracoes.md`, cartão `suporte`).

**O que já existia:** `GET /api/suporte/` com `bloqueado` e `acessos`, e as rotas `bloquear/`, `liberar/` e `acessos/{id}/revogar/`, com os eventos `suporte.bloquear`, `suporte.liberar` e `suporte.revogar` nas duas auditorias. Também já existia o 403 `PLT-07` para o token de suporte (`suporte_proibido`).

**O que foi feito:**
- `plataforma/selectors.py`:
  - `controle_do_suporte(empresa, situacao)` é o corpo do `GET /api/suporte/`: `situacao_rotulo`, `contagens` (`todos`, `ativos`, `encerrados`, independentes do filtro), o filtro `?situacao=` (valor desconhecido vale `todos`) e, em cada item, `permissao_rotulo` (o rótulo do `PermissaoSuporte`), `status_rotulo` e `acoes.revogar`.
  - Não vem o e-mail do operador.
  - O `ativo` com o `fim` já passado (antes da rodada da `AUT-15`) já vem como `encerrado`, sem `revogar`.
  - `item_do_acesso` é o item da lista. O `revogar/` devolve o item no mesmo formato.
  - `situacao_do_suporte(empresa)` devolve `{bloqueado, ativos}` numa consulta só ao `public`.
- `plataforma/api/suporte.py`: a view usa os selectors. Serializers novos: `AcoesDoAcesso` e `ContagensDoSuporte`. O parâmetro `situacao` entrou no OpenAPI.
- `relatorios/configuracoes.py` e `relatorios/selectors.py`:
  - Cartão `suporte`, com o título "Controle do suporte", que vem com o app `plataforma`.
  - Resumo "Suporte liberado" ou "Suporte bloqueado", com " · 1 acesso ativo" ou " · {n} acessos ativos".
  - O cartão não vem para o token de suporte (`SO_FORA_DO_SUPORTE`).
- `docs/api/openapi.yaml` regenerado. Em `docs/api/contas.md`, a regra do acesso vencido, o filtro desconhecido, a ordem da lista e o formato do revogar.

**Testes:**
- `tests/aceitacao/test_t011_contas.py`:
  - `test_plt_07_controle_do_suporte_contagens_e_filtro`: contagens, filtro, rótulos e `acoes`; o cartão antes e depois do bloqueio; o 403 e a ausência do cartão para o token de suporte.
  - `test_plt_07_controle_do_suporte_vencido_conta_como_encerrado`.
  - `test_plt_07_controle_do_suporte_sem_email_do_operador`.
- `tests/aceitacao/test_t181_configuracoes.py`:
  - O seed ganha o cartão `suporte`. O suporte não o vê.
  - O teto de queries sobe para 12, com o teste renomeado para `test_usr_05_configuracoes_no_maximo_12_queries`.
  - `test_plt_07_configuracoes_textos_do_cartao_suporte` testa a função pura.
- ruff, ruff format e mypy sem erro. O spectacular valida, com os 2 avisos de nome de enum que já existiam.
- Regressão nos 31 arquivos de teste que tocam suporte, Configurações ou `plataforma.selectors`: 649 passed, 5 xfailed.

**Para o Frontend (T-372):** o cliente precisa de `npm run api:gerar`. A tela lê `situacao_rotulo`, `contagens`, `status_rotulo`, `permissao_rotulo` e `acoes.revogar`, e não calcula nada.

**Próximo passo:** o orquestrador revisa e abre o PR. Depois, a T-372 do Frontend fica destravada.
