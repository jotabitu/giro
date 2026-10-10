# T-120 · CI por área alterada · devops → orquestrador

**O que foi feito:**

1. **Job `areas` em `.github/workflows/ci.yml`:** roda `git diff --name-only HEAD^1 HEAD` (o checkout de `pull_request` é o commit de merge, e o primeiro pai é a ponta da base; `fetch-depth: 2`) e expõe `backend`, `frontend` e `infra`. Sem action de terceiros.
2. **Regras:** backend com `backend/**` ou `docs/api/**`; frontend com `frontend/**` ou `docs/api/**`; infra com `infra/**`, `docker-compose*.yml`, `.env.example` ou `Makefile`; `.github/workflows/**` roda tudo. PR só de `docs/` (fora de `docs/api/`) ou `tarefas/` roda só o job `areas`, uns 10 segundos.
3. **Gatilho `push` na `main` removido.** Fica só `pull_request`.
4. **`tarefas/README.md`:** seção "Antes do push".

**Jobs pulados e PR travado:** `gh api` de proteção de branch e de rulesets responde 403 (plano gratuito em repo privado), então não existe check obrigatório e job pulado não trava o merge. Se o plano mudar e o dono criar check obrigatório, o job pulado conta como sucesso, mas vale conferir.

**Cuidados:**
- Um job `areas` custa 1 minuto arredondado por execução; é o preço da detecção.
- O `concurrency` continua cancelando execuções antigas do mesmo ref.
- Não testado em execução: o próprio PR mexe em `.github/workflows/`, então roda os três jobs e serve de teste. Conferir ali que `areas` mostra os três como `true`.
- Sem CI na `main`, o OpenAPI e os testes só são conferidos no PR; por isso a regra de dar merge da `origin/main` na branch antes do PR.

**Próximo passo para quem recebe:** o dono abre o PR; conferir o job `areas` e os três jobs verdes. Depois, abrir um PR só de `tarefas/` para ver que nenhum job pesado roda.
