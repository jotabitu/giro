# T-277 · Django Admin pelo proxy · arquiteto → devops, backend, orquestrador

**O que foi feito:** a ADR 0029 decide como o Django Admin da plataforma é alcançado em homologação e produção.
**Onde:** `docs/decisoes/0029-django-admin-pelo-proxy.md`, o índice das ADRs e o estado da T-277 no backlog.

**Decisão:**
- **Onde fica:** `https://admin.<dominio>/admin/`, o caminho que o Django já usa, sem mudança no backend. O proxy ganha um bloco `server` só para o host exato da plataforma, com as `location` de hoje (melhor num arquivo incluído pelos dois blocos) e mais `location /admin/` para o Django. Nos hosts das empresas, `/admin/` continua no Next, que é a Administração da locadora.
- **Quem entra:** só usuário do `public` com `is_staff`, que hoje é só o Dono, pelo `createsuperuser`. Sempre com 2 etapas, bloqueio por tentativas e auditoria do login, que já existem.
- **Proteção no proxy:** uma lista de IPs vinda de um arquivo do cofre (`geo ... include`). Fora dela a resposta é 404, e a lista vazia deixa o Admin fechado, que é o padrão. O login (`/admin/login/`) usa a zona `giro_auth`, e as respostas levam `X-Robots-Tag: noindex, nofollow`.
- **Sem VPN:** pediria infraestrutura nova para uma porta pouco usada.
- **Sessão:** 4 horas e fecha com o navegador (`prod.py`).

**O que fica para o devops:**
- Ajustar o proxy como acima.
- Pôr o arquivo da lista no cofre do deploy, vazio em homologação e em produção.
- Teste de subida:
  - com a lista vazia, 404 no host da plataforma;
  - com o IP do teste na lista, a tela de login com os estáticos;
  - no host de uma empresa, `/admin/contratos` continua no Next.
- Escrever "Como abrir o Admin" no `infra/README.md`.

**O que fica para o backend:** `SESSION_COOKIE_AGE` de 4 horas e `SESSION_EXPIRE_AT_BROWSER_CLOSE` no `prod.py`, e o teste `test_t277_is_staff_so_pelo_createsuperuser`.

**O que ficou de fora:** a VPN. Ela pede ADR nova se a equipe passar a trabalhar de IP variável.
