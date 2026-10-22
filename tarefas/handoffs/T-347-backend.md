# T-347 · Rota para reconfirmar as 2 etapas · backend → orquestrador, frontend (T-348), qa, segurança

Branch `t-347-reconfirmar-2-etapas`, criada da `origin/main` (d868fd6, com o contrato da T-346, #383). Contrato: `docs/api/contas.md`, "Reconfirmar as 2 etapas"; ADR 0032.

**O que foi feito:**

- **Rota:** `POST /api/auth/2fa/reconfirmar/` (`contas.api.acesso.Reconfirmar2FAView`, base `Logada`), com o serializer do `2fa/verificar/`: `{ codigo }` ou `{ codigo_recuperacao }`, nunca os dois. Responde 200 `{ "access" }` com `Cache-Control: no-store`.
- **Token:** `comum.autenticacao.emitir_access_reconfirmado(token_atual)` monta um `AccessToken` com `user_id`, `sid`, `schema`, `empresa_id` e `amr` do token que chamou, mais `auth_time` = agora.
  - Antes, confere a empresa do token.
  - Não chama `emitir_tokens`: não abre `Sessao`, não emite refresh, não vincula `jti` e não grava cookie.
  - O comentário de `CLAIM_AUTH_TIME` cita o login e a reconfirmação.
- **Ordem das conferências:**
  1. corpo (400 `validacao`);
  2. sem autenticador: 409 `2fa_inativo`, antes de contar tentativa;
  3. `dois_fatores.verificar_codigo`, com a linha travada. O bloqueio dá 429 `USR-06` antes de olhar o código, e o limite soma senhas e códigos e grava `usuario.bloqueado`, com o aviso aos administradores. O acerto zera a contagem.
  4. Código errado: 400 `validacao` no campo enviado (`codigo` ou `codigo_recuperacao`), com a mensagem do login.
- **Suporte:** 403 `PLT-07` (`suporte_proibido` da `Logada`).
- **Auditoria** (`seguranca`, `USR-02`, objeto o usuário, sem o código):
  - `usuario.reconfirmar_2fa`, "Confirmou o código do autenticador";
  - `usuario.reconfirmar_2fa_falhou`, "Errou o código do autenticador", com o motivo `código` ou `código de recuperação`;
  - com código de recuperação, também `usuario.usar_codigo_recuperacao`.
  - Os textos estão em `auditoria.textos`.
- A view entrou em `VIEWS_DE_ACESSO`: sem `EmpresaOperando`, como as outras rotas da própria conta. A `cancelada` continua barrada pelo `EmpresaCanceladaMiddleware`.
- O OpenAPI foi regenerado (`docs/api/openapi.yaml`, rota nova) e o `backend/apps/contas/README.md` foi atualizado.

**Onde:** `backend/comum/autenticacao.py`, `backend/apps/contas/api/acesso.py` e `api/urls.py`, `backend/apps/auditoria/textos.py`, `backend/apps/contas/README.md`, `docs/api/openapi.yaml`.

**Regras cobertas:** USR-02, USR-06, PLT-06, PLT-07. Testes em `backend/tests/aceitacao/test_t347_reconfirmar_2_etapas.py`:

- `test_usr_02_reconfirmar_devolve_access_na_mesma_sessao`: mesmo `sid`, `schema`, `empresa_id`, `amr` e `user_id`; `auth_time` = agora; nenhuma `Sessao` nova; sem `Set-Cookie`; `no-store`.
- `test_usr_02_reconfirmar_libera_o_cancelamento`: login, relógio 16 min à frente, `renovar`, 403 `2fa_recente`; depois de reconfirmar, o cancelamento passa.
- `test_usr_02_renovar_depois_de_reconfirmar_continua_sem_auth_time`: o refresh do cookie continua valendo, e o access renovado tem o mesmo `sid` e não tem `auth_time`.
- `test_usr_06_reconfirmar_conta_tentativas_e_bloqueia`:
  - 2 senhas erradas no login e 3 códigos errados aqui bloqueiam;
  - no bloqueio, o código certo também recebe 429, e o `auth/entrar/` também;
  - a sessão aberta continua;
  - passado o bloqueio, o acerto zera a contagem.
- `test_usr_02_reconfirmar_com_codigo_de_recuperacao`: o código vale uma vez (restam 7); repetido, dá 400 no campo `codigo_recuperacao`; sem campo ou com os dois, 400.
- `test_usr_02_reconfirmar_sem_autenticador`: 409, sem contar tentativa.
- `test_plt_07_reconfirmar_recusa_suporte`: 403 nos dois modos.
- `test_usr_02_reconfirmar_evento_sem_o_codigo`: os dois eventos sem o código, com os textos.

**Testes rodados** (num contêiner avulso na rede `giro-backend-teste`, banco `giro`, uma rodada por vez):

- `ruff check`, `ruff format --check` e `mypy` (401 arquivos) passaram.
- `makemigrations --check`: sem mudança.
- OpenAPI com `--validate`: 0 erros; a diferença é só a rota nova.
- Pytest, no banco recriado com `--create-db` na primeira rodada da branch, em `test_t347`, `test_t068`, `test_t345`, `test_t011`, `test_t018`, `test_t202`, `tests/test_permissoes_das_rotas.py`, `test_autenticacao.py`, `test_rotas.py`, `test_limites_entre_apps.py` e `apps/contas`: 129 passaram e 1 falhou. A falha foi `test_toda_view_da_empresa_tem_as_permissoes_padrao`, porque faltava a view em `VIEWS_DE_ACESSO`. Depois da correção:
  - `test_permissoes_das_rotas.py`: 2 passaram;
  - `test_t347`: os 8 passaram de novo, junto com o mypy.

**O que ficou de fora:** nada do contrato. O achado da T-346 continua como estava: o `renovar` não leva o `auth_time`, então o access reconfirmado vale só enquanto não vence (5 min). A tela repete o pedido logo depois.

**Próximo passo para quem recebe:**

- **Frontend (T-348):** a rota está pronta para o diálogo da `Admin-Cancelar`. Os erros são 400 no campo enviado, 409 `2fa_inativo` e 429 `USR-06` com `detalhes.tentar_de_novo_em`. Rode `npm run api:gerar`.
- **QA:** os testes acima.
- **Segurança:** se quiser, conferir a rota junto com a T-345.
