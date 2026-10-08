# T-045 · GIRO_PROXIES_CONFIAVEIS e X-Forwarded-For · devops → arquiteto, backend, seguranca

**O que foi feito:** `GIRO_PROXIES_CONFIAVEIS=1` em `.env.example` (comentário por ambiente); `frontend/src/middleware.ts` descarta o `X-Forwarded-For` do cliente em `/api/`; seção "IP do ator e proxies" em `infra/README.md`.
**Achado:** o rewrite do Next repassa o `X-Forwarded-For` do cliente sem acrescentar o IP real (medido com um servidor de eco: `X-Forwarded-For: 6.6.6.6` chegava intacto). Sem o middleware, o ator poderia forjar o próprio IP na auditoria.
**Homologação e produção (ADR 0018, be93a0d):** `/api/` vai direto do proxy reverso ao Django, sem o Next; `GIRO_PROXIES_CONFIAVEIS=1` e `GIRO_REDES_PROXY` = rede do proxy. `GIRO_REDES_PROXY` entrou no `.env.example` (dev: faixas privadas do Docker). Comentários do `next.config.ts` e do middleware agora dizem só dev. Falta a regra de rede "Django só alcançável pelo proxy", que fecha no deploy (T-035).
**Limite em dev:** o Next também não acrescenta o IP do cliente, então o backend recebe `X-Forwarded-For` vazio e deve cair no endereço da conexão (o container do frontend). O pedido de "acrescentar" só se cumpre em homologação e produção, com proxy reverso de verdade na frente; isso entra com o deploy.
**Contrato para o backend:** com `GIRO_PROXIES_CONFIAVEIS=N`, só se `REMOTE_ADDR` estiver em `GIRO_REDES_PROXY`, pegar o N-ésimo da direita no `X-Forwarded-For`; se faltar elemento ou o cabeçalho vier vazio, usar `REMOTE_ADDR`. O teste deve cobrir os dois casos.
**Verificado:** `/api/schema/` dá 200 em `localhost` e `admin.localhost` com o middleware; lint, tipos, testes e build do frontend verdes; valor forjado descartado.
**Não verificado:** o CI desta branch (sem push de teste ainda); comportamento atrás de proxy reverso real.
**Tocou arquivo do frontend** (`src/middleware.ts`, 1 arquivo novo): frontend, confira.
