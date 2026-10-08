# T-035 · Endurecimento de produção · devops → orquestrador, backend, frontend, seguranca

**Branch:** `t-035-endurecimento` (a partir da main; traz T-043/ADR 0016 e T-045/ADR 0018 por merge).
**Feito (S-16, S-17, S-18, C-04):** `prod.py` com `SHOW_PUBLIC_IF_NO_TENANT_FOUND=False`, HSTS 1 ano com preload e subdomínios (variáveis para homologação), `Referrer-Policy`, `X-Frame-Options: DENY`; `JWT_SIGNING_KEY` própria (base cai em `SECRET_KEY` só em dev e testes; prod recusa igual ou ausente); `GIRO_REDES_PROXY` obrigatória em prod; `/api/schema/` e `/api/docs/` só com `EXPOR_DOCUMENTACAO_DA_API` (fechado em prod); `wsgi`, `asgi` e `celery` sem padrão dev; CSP com nonce no `middleware.ts` e cabeçalhos fixos no `next.config.ts`. Tabela por ambiente em `infra/README.md`.
**Achado:** com CSP por nonce, página pré-renderizada em build fica sem nonce nos scripts inline e seria bloqueada. Por isso `export const dynamic = "force-dynamic"` em `app/layout.tsx`. Custo: sem cache estático de página, aceitável (app autenticado).
**Verificado:** ruff, format e mypy do backend; `tests/test_producao.py` (8 testes, processo limpo por caso); lint, tipos, 56 testes, build do frontend; no servidor de produção, cabeçalhos presentes e todos os `<script>` com nonce.
**Não verificado:** `tests/test_rotas.py` e o restante dependem de Postgres e o Docker daqui não respondeu; confiar no CI. Comportamento atrás de proxy reverso real e a CSP num navegador (só conferi o HTML).
**Frontend, confira de novo:** o `middleware.ts` revisado na T-045 mudou: o matcher agora cobre as páginas (exceto `_next/static`, `_next/image`, favicon e prefetch) e `/api/` mantém só a remoção do `X-Forwarded-For`; arquivo novo `src/lib/csp.ts` com teste; `layout.tsx` ganhou `force-dynamic`. Sobre o seu ponto 3: medi com servidor de eco na T-045 que o valor forjado era descartado, mas não confirmei se o Next acrescenta o IP do socket; o comentário "vazio" pode estar impreciso.
**Backend:** `GIRO_PROXIES_CONFIAVEIS` e `GIRO_REDES_PROXY` ainda precisam ser lidas (T-034); T-043 também pede `DATABASE_URL_MIGRACAO`.
**Pendente (deploy):** regra de rede Django só via proxy; certificado curinga; Sentry no frontend.

**Revisão do frontend (middleware, csp e layout: lógica aprovada). Pontos abertos:**
- `img-src 'self' data: blob:` bloqueia logo, foto de veículo e prévia de documento (URL assinada de 15 min, AUD-05) se vierem do armazenamento S3. Quando o contrato de empresas e fotos definir o host, acrescentar a origem em `img-src` (e `frame-src`/`object-src` se houver PDF embutido) em `src/lib/csp.ts`. Hoje nenhuma tela carrega imagem externa.
- `connect-src 'self'`: em dev, `NEXT_PUBLIC_API_URL` com outro host seria bloqueado. O `.env.example` já manda deixá-la vazia.
- `force-dynamic` na raiz tira o pré-render de todas as páginas, inclusive `/design-system` e `/entrar`. Aceito; registrar no PR.
- O cabeçalho `X-Forwarded-For` que chega ao Django em dev segue sem medição; o comentário do middleware fica como está até alguém olhar o cabeçalho no backend.

**CI do PR #17 (após merge da main, 524ccdb):** Backend (inclui os testes com Postgres e o OpenAPI), Frontend e Infra verdes. O conflito inicial era só em `tarefas/em-andamento.md`.
