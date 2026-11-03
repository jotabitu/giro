# T-429 · Correções do CI da T-427 (devops)

Branch `t-429-ci-correcoes`, a partir da `origin/develop` (6389eb50).

## 1. Frontend: `git diff HEAD^1...HEAD failed` no passo "Testes (alterados)"

**Causa:** o job `frontend` usava o `actions/checkout` padrão (profundidade 1). No PR o checkout é o commit de merge, e sem o histórico o `HEAD^1` (ponta da base) não existe; o Vitest `--changed HEAD^1` roda `git diff --name-only -z HEAD^1...HEAD` e sai com 1.

**Correção:** `fetch-depth: 2` no checkout do job `frontend` (`.github/workflows/ci.yml`). Mesmo valor que o job `areas` já usa e que funciona. Dois níveis trazem o merge e a ponta da base, e o `HEAD^1` é ancestral do `HEAD`, então a base de comparação (`...`) é ele mesmo.

**Para confirmar:** o PR #469 precisa de uma rodada nova com o workflow corrigido. Re-executar o job antigo não basta, porque ele reaproveita o commit de merge velho; atualize a branch com a `develop` depois do merge desta tarefa (ou feche e reabra o PR) e confira o passo "Testes (alterados)". Não consegui provar no Actions daqui.

## 2. Backend na `develop` (run do a963feb0): `UniqueViolation pg_authid_rolname_index`

**Diagnóstico:** `django_db_setup` de `backend/conftest.py` (`_papeis_de_banco`) fazia `SELECT` em `pg_roles` e, se faltasse, `CREATE ROLE giro_app / giro_expurgo`. Papel é global do cluster, mas cada worker do xdist tem o próprio banco (`test_giro_gw0`, `gw1`...). Dois workers que passam pelo `SELECT` juntos tentam criar o mesmo papel; o segundo cai em `pg_authid_rolname_index`. O worker `gw0` falhou no setup e levou toda a sua fatia: 1161 erros de setup contra 597 passes na run.

**É flaky antigo, não novo.** `_papeis_de_banco` entrou em 08 out 2026 (9714a4ec, AUD-01/02) e o pytest já rodava com `-n auto` nos PRs. A corrida existia desde então; só aparece quando os workers chegam ao setup no mesmo instante. Rodar a suíte inteira em todo push na `develop` (T-427) aumentou a chance de ela aparecer, não a criou.

**Correção, sem esconder falha real:** o `CREATE ROLE` virou um bloco `DO $$ ... EXCEPTION WHEN duplicate_object OR unique_violation THEN NULL; END $$`. Só "papel já existe" é tolerado (o PostgreSQL devolve `unique_violation` quando a corrida é no índice); qualquer outro erro continua subindo. Não usei retry do job: ele repetiria 3 minutos de teste para mascarar um erro de setup determinístico de resolver. Advisory lock não serve, porque é por banco e os workers estão em bancos diferentes.

Provado no Postgres 16 do `giro-backend-pg`: três `DO` simultâneos criando o mesmo papel terminam sem erro. A suíte inteira não foi rodada aqui (pouca memória); este PR altera `conftest.py` e o workflow, então o CI dele roda tudo.

## Arquivos

- `.github/workflows/ci.yml` (checkout do job `frontend`)
- `backend/conftest.py` (`_papeis_de_banco`)
