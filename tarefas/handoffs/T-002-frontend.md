# T-002 · Esqueleto do frontend · frontend → design-system (T-004), orquestrador, devops (T-005)

**O que foi feito:** Next.js 15 (App Router) + React 19, TypeScript estrito (`noUncheckedIndexedAccess`), Tailwind 3.4 lendo `src/design-system/tokens.ts`, ESLint 9 (next/core-web-vitals + next/typescript) e Vitest. Grupos de rota `(publico)`, `(empresa)`, `(plataforma)` com uma página marcadora cada (`/entrar`, `/inicio`, `/plataforma`); `/` redireciona para `/entrar`. `package-lock.json` versionado.
**Onde:** `frontend/` (package.json, tailwind.config.ts, src/app, src/lib/config.ts, src/design-system/tokens.ts, scripts/).
**Tokens:** `tokens.ts` é gerado por `scripts/gerar-tokens.mjs` a partir de `docs/design-system/tokens.json` (cores claro/escuro, espaçamento, raio, sombra, fontes, tipografia). O layout injeta as variáveis CSS (`cssDosTemas()`); o Tailwind aponta para `var(--nome)`, então `--brand`, `--brand-soft` e `--on-brand` são trocáveis em execução. A T-004 assume a pasta: pode apagar o gerador e manter `tokens.ts` à mão, ou manter o gerador.
**Scripts:** dev, lint, typecheck, test (Vitest), build, api:gerar.
**Variáveis:** `urlDaApi()` em `src/lib/config.ts` usa `API_URL_INTERNA` no servidor e `NEXT_PUBLIC_API_URL` no navegador (vazio conta como ausente; teste cobre).
**Verificado:** lint, typecheck, 4 testes e build verdes no host (Node 24) e dentro do container Node 22 (`npm ci` na imagem). `docker compose up -d --no-deps frontend` sobe e `/entrar`, `/inicio`, `/plataforma` respondem 200.
**O que ficou de fora:**
- `docker compose up frontend` sem `--no-deps` depende do serviço `backend`, que só existe com a T-001; testei com `--no-deps`.
- `make` não existe neste Windows; rodei os comandos do `frontend-check` à mão no container.
- `api:gerar` avisa e sai com sucesso se `docs/api/openapi.yaml` não existir (T-001/T-005). `src/lib/api/schema.d.ts` está no ignore do ESLint. Quando o OpenAPI existir, decidir com a T-005 se o schema gerado é versionado.
- Sem fontes Geist carregadas (cai no fallback); sem shadcn/ui, TanStack Query, React Hook Form, Zod. Entram com as telas ou com a T-004.
- Sem Playwright (`e2e/` é do agente qa).
**Próximo passo para quem recebe:** design-system (T-004) cria os componentes sobre `tokens.ts`; devops (T-005) usa os scripts acima no CI (Node 22).
