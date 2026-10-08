# T-077 · Reativar usuário com convite cancelado volta para convite pendente · backend → orquestrador, qa, frontend

**O que foi feito:**
- **`USR-04` (opção B):** `reativar_usuario` agora depende de a pessoa já ter chegado a `ativo`.
  - Quem já foi `ativo` volta `ativo`, sem convite (auditoria `usuario.reativar`).
  - Quem nunca chegou a `ativo` volta para `convite_pendente` (auditoria `usuario.reativar_convite`). Recebe um convite novo de 7 dias pelos mesmos canais (`USR-01`), enviado depois do commit, e os links antigos deixam de valer (P-06).
  - Nos dois casos a pessoa volta a contar no plano. Com o plano no limite, a resposta é 422 `PLT-03`: ela continua `desativado` e nenhum convite sai.
- **Senha anterior:** quem volta para o convite fica sem senha, porque o link novo cria a senha. No login com a senha antiga, a resposta é 403 `convite_pendente`, "Use o link do convite para criar seu acesso". A mudança está no `EntrarView`, que agora também confere `has_usable_password`.
- **Máquina de estados:** `desativado → convite_pendente` entrou na tabela de `Usuario`, e só o `reativar_usuario` usa essa transição.
- **Como saber se a pessoa já foi `ativo` (`services.ja_foi_ativo`):**
  - Quem nunca teve convite foi criado já ativo (seed, `createsuperuser`) e conta como já ativo.
  - Quem teve convite precisa de um evento de auditoria do próprio usuário com `depois.status = "ativo"` (`usuario.ativar` ou `usuario.reativar`).
  - Não houve migração.

**Onde:** `backend/apps/contas/services.py` (`ja_foi_ativo`, `reativar_usuario`), `models.py` (`TRANSICOES`), `api/acesso.py` (login), `api/usuarios.py` (descrição no OpenAPI) e `README.md`. O contrato está em `docs/api/contas.md` e o OpenAPI em `docs/api/openapi.yaml`, que mudou só no texto, sem mudança de esquema.

**Regras e testes** (`tests/aceitacao/test_t011_contas.py`):
- `test_usr_04_ca_011_22_reativar_depende_de_ja_ter_sido_ativo` cobre o CA-011-22 novo:
  - Felipe volta `ativo`, sem e-mail, e o plano vai de 5 para 6.
  - Lúcia, que já tinha senha, tem o convite cancelado em 08 out (plano em 4).
  - Em 09 out, com o plano em 10 de 10: 422 `PLT-03`, ela continua `desativado` e nada sai.
  - Com vaga: 200, `convite_pendente`, `convite_expira_em` em 16 out, um e-mail para a Lúcia e o plano em 5.
  - O link antigo responde 404 ou 410, e a senha antiga responde 403 `convite_pendente`.
  - O link novo cria a senha e leva às 2 etapas. Depois do código, ela passa a `ativo`.
- `test_usr_04_ca_011_22_desativar_encerra_na_hora` continua igual: Bruna volta `ativo`.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `342 passed, 43 xfailed`.
- OpenAPI regerado com `--validate`, sem aviso.
- Rodado no Postgres descartável, com `--rm` e `POSTGRES_HOST`.

**Próximo passo para quem recebe:**
- **QA:** conferir o CA-011-22.
- **Frontend:** em Administração > Usuários, depois de reativar, mostrar o `status` devolvido. Se for `convite_pendente`, a pessoa vai para a aba "Convites", com o prazo do convite novo.
