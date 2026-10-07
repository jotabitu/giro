# T-045 · GIRO_PROXIES_CONFIAVEIS e X-Forwarded-For · devops → arquiteto, backend, seguranca

**O que foi feito:** `GIRO_PROXIES_CONFIAVEIS=1` em `.env.example` (comentário por ambiente); `frontend/src/middleware.ts` descarta o `X-Forwarded-For` do cliente em `/api/`; seção "IP do ator e proxies" em `infra/README.md`.
**Achado:** o rewrite do Next repassa o `X-Forwarded-For` do cliente sem acrescentar o IP real (medido com um servidor de eco: `X-Forwarded-For: 6.6.6.6` chegava intacto). Sem o middleware, o ator poderia forjar o próprio IP na auditoria.
**Limite em dev:** o Next também não acrescenta o IP do cliente, então o backend recebe `X-Forwarded-For` vazio e deve cair no endereço da conexão (o container do frontend). O pedido de "acrescentar" só se cumpre em homologação e produção, com proxy reverso de verdade na frente; isso entra com o deploy.
**Contrato para o backend:** com `GIRO_PROXIES_CONFIAVEIS=N`, pegar o N-ésimo da direita no `X-Forwarded-For`; se faltar elemento ou o cabeçalho vier vazio, usar `REMOTE_ADDR`. O teste deve cobrir os dois casos.
**Verificado:** `/api/schema/` dá 200 em `localhost` e `admin.localhost` com o middleware; lint, tipos, testes e build do frontend verdes; valor forjado descartado.
**Não verificado:** o CI desta branch (sem push de teste ainda); comportamento atrás de proxy reverso real.
**Tocou arquivo do frontend** (`src/middleware.ts`, 1 arquivo novo): frontend, confira.
