# T-427 · CI testa só o que mudou no PR (devops)

Branch `t-427-ci-so-o-que-mudou`, a partir da `origin/develop` (de02c7bf). Pedido do dono em 03 nov 2026.

## O que mudou

- `.github/workflows/ci.yml`: gatilhos `pull_request` (para `develop` e `main`) e `push` na `develop`. O job `areas` chama `infra/scripts/selecionar-testes.sh` e passa adiante `backend_testes` (tudo, lista ou nenhum), `backend_alvos` e `frontend_testes` (tudo ou alterados).
  - Backend: lint, tipos e a conferência do OpenAPI rodam sempre que o backend é tocado; o pytest roda os alvos da lista, ou tudo, ou nada (só texto em `backend/`).
  - Frontend: lint, typecheck e build como antes; Vitest com `--changed HEAD^1 --passWithNoTests` ou inteiro.
  - Concorrência: PR cancela a rodada anterior; push na `develop` tem uma rodada por commit, sem cancelar.
  - Nomes dos jobs inalterados (proteção de branch que dependa deles continua valendo).
- `infra/scripts/selecionar-testes.sh` (novo, só sh, git e grep): lê os arquivos alterados da entrada padrão. `EVENTO` e `BASE` mandam: fora de PR para a `develop`, tudo roda.
- `infra/scripts/check-selecao-testes.sh` (novo): 17 casos de PR de exemplo; roda no job de infra.
- `infra/README.md`: seção "CI: o que cada gatilho roda (T-427)" com a tabela, as regras de seleção, como ver a falha na `develop` e o risco.

## Decisão sobre o mapa app → testes

Quase todos os testes do backend moram em `backend/tests/aceitacao`, não em `apps/<app>/tests` (só 5 apps têm essa pasta). Então, além da pasta do app, entram os `test_*.py` de `tests/`, `comum/tests` e `integracoes` que citam o app pelo nome (palavra inteira). Também entram os apps que importam o alterado (fecho transitivo por `from apps.x`) com os testes deles. Sem dependência nova, sem pytest-testmon.

## Resultados da seleção (PRs de exemplo)

| PR de exemplo | Resultado |
| --- | --- |
| só `backend/apps/filiais/services.py` | pytest em lista: `apps/filiais/tests`, `apps/aprovacoes/tests`, `apps/importacao/tests` (importam filiais) e os testes de aceitação que citam esses apps; frontend não roda |
| só `frontend/src/app/page.tsx` | backend não roda; frontend com Vitest `alterados` |
| só `docs/` e `tarefas/` | nenhum job de código roda |
| `backend/config/settings/base.py` | pytest inteiro |
| `backend/comum/erros.py`, `conftest.py`, `requirements.txt`, migração de app | pytest inteiro |
| `docs/api/openapi.yaml` | pytest e Vitest inteiros |
| `frontend/package.json`, `vitest.config.ts`, `src/testes/*` | Vitest inteiro |
| `backend/apps/locacoes/README.md` | lint e OpenAPI; pytest não roda |
| `.github/workflows/ci.yml` | tudo |
| push na `develop` / PR para a `main` | tudo |

`sh infra/scripts/check-selecao-testes.sh` passou localmente (17 casos).

## Não conferido

O Vitest `--changed` e o fluxo completo do Actions só se confirmam no primeiro PR e no primeiro push na `develop` depois do merge; o `npm ci` não foi rodado aqui (pouca memória). O YAML foi lido com o PyYAML e carrega, mas não rodou no Actions. Este PR altera `.github/workflows`, então ele mesmo roda tudo.

## Como o dono vê a falha na `develop`

Cada merge na `develop` roda a suíte inteira. Se falhar, o job "Backend (testes, OpenAPI)" ou "Frontend (lint, tipos, testes, build)" fica vermelho: X vermelho ao lado do commit na `develop`, na aba Actions (CI, branch `develop`) e no e-mail do GitHub. Corrigir antes do PR de promoção para a `main`.

## Risco

Um PR pode passar sem pegar quebra em app que depende do alterado sem importá-lo nem citá-lo (casos #437 e #436). Só aparece no vermelho da `develop` depois do merge. Descrito em `infra/README.md`.

## Próximo

Orquestrador: avisar o QA para olhar o primeiro push na `develop` depois do merge. Nenhuma variável de ambiente nova.
