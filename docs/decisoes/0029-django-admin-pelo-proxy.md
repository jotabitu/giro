# Django Admin da plataforma pelo proxy

**Status:** aceita · 16 out 2026 · T-277 (achado do devops na T-264) · detalha a 0013 (item 4) e a 0027

## Contexto

O Django Admin existe só no schema `public`, no urlconf da plataforma (`config/urls_publico.py`, `path("admin/", ...)`), com `OTPAdminSite` (2 etapas obrigatórias, `PLT-08`), login pelo bloqueio e pela auditoria da API (`contas.login_admin`, P-01 da T-057) e model de negócio só leitura (ADR 0013, item 4). O `LoginDoAdmin` só deixa entrar usuário ativo com `is_staff`, e só o `createsuperuser` marca `is_staff` (função Dono).

O proxy de homologação e produção (`infra/proxy/giro.conf.template`) tem um bloco só para `*.<DOMINIO_BASE>`: `/api/` e `/static/` vão ao Django, e `/` vai ao Next. Por isso o Admin está inalcançável (T-264). Não dá para mandar `/admin/` ao Django em todos os hosts, porque `/admin/...` no host da empresa é a Administração da locadora no Next (`frontend/src/app/(empresa)/admin`, ex.: `/admin/contratos`).

Quem usa o Admin é a equipe da Giro, para conferir dados e fazer, por ação que chama o serviço, o que o painel da plataforma (Next, `/plataforma/...`) ainda não faz. É a porta mais poderosa do sistema: lê o `public` inteiro.

## Decisão

### 1. Caminho e host

- O Admin fica em `https://<SUBDOMINIO_PLATAFORMA>.<DOMINIO_BASE>/admin/` (hoje `admin.<dominio>/admin/`), o caminho que o Django já usa. Sem mudança no backend.
- O proxy ganha um bloco `server` próprio para o host exato da plataforma (`server_name ${SUBDOMINIO_PLATAFORMA}.${DOMINIO_BASE}`; no nginx, o nome exato vence o curinga). Ele repete as `location` de hoje (melhor por um arquivo incluído pelos dois blocos, para não divergirem) e acrescenta `location /admin/` para o Django.
- Nos hosts das empresas, nada muda: `/admin/` continua indo ao Next. O urlconf da empresa não tem Admin (ADR 0013), então mesmo um pedido que chegasse ao Django daria 404.
- `/static/` continua como está (T-264).

### 2. Quem acessa

- Só usuário do `public` com `is_staff`, que hoje é só a função Dono (criado pelo `createsuperuser`). Suporte, Financeiro e Sucesso usam o painel da plataforma e não recebem `is_staff`. Dar `is_staff` a mais alguém é ato do Dono, por linha de comando no servidor; não há tela para isso.
- 2 etapas sempre (`OTPAdminSite`), bloqueio por tentativas e auditoria do login, como hoje.

### 3. Proteção na borda: lista de IPs, fechada por padrão

- `location /admin/` só atende os IPs de uma lista do ambiente (ex.: escritório da Giro, máquina de quem está de plantão). A lista vem de um arquivo do cofre do deploy montado no proxy (ex.: `geo $admin_permitido { default 0; include /etc/nginx/admin-ips.conf; }`); fora dela, 404 (não 403, para não confirmar que o Admin existe).
- **Lista vazia = Admin fechado.** É o padrão de homologação e produção até alguém precisar; abrir é mudar o arquivo do cofre e recarregar o proxy, com registro no histórico do cofre.
- Limite de requisições no login: `/admin/login/` usa a zona `giro_auth` (10 por minuto por IP), como `/api/auth/`.
- Cabeçalhos: `X-Robots-Tag: noindex, nofollow`; o `X-Frame-Options: DENY` já vem do `prod.py`.
- **Por que não VPN:** pediria um serviço de infraestrutura novo (e outra ADR) para uma porta usada poucas vezes por mês. A lista de IPs com 2 etapas resolve hoje; se a equipe crescer ou trabalhar de IP variável, a VPN entra por ADR nova.

### 4. Sessão do Admin curta

O Admin é a única parte do sistema que usa a sessão do Django (a API usa os tokens da ADR 0013). No `prod.py`: `SESSION_COOKIE_AGE = 4 horas` e `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`, além do `SESSION_COOKIE_SECURE` e do `CSRF_COOKIE_SECURE` que já existem. O cookie fica preso ao host da plataforma (sem `SESSION_COOKIE_DOMAIN`), e o host das empresas nunca o recebe.

## Consequências

- **Devops:** o bloco `server` do host da plataforma, a `location /admin/` com a lista de IPs (arquivo do cofre, vazio por padrão), o limite no login e o `X-Robots-Tag`. Teste de subida: com a lista vazia, `/admin/` responde 404 no host da plataforma; com o IP do teste na lista, responde a tela de login do Django (com os estáticos); no host de uma empresa, `/admin/contratos` continua no Next. `infra/README.md` ganha "Como abrir o Admin" (editar a lista no cofre e recarregar o proxy).
- **Backend:** a sessão curta no `prod.py` e um teste de que nenhum serviço, fora do `createsuperuser`, marca `is_staff` (`test_t277_is_staff_so_pelo_createsuperuser`). O resto já existe.
- Quando o painel da plataforma cobrir o que hoje só o Admin faz, a lista pode ficar vazia para sempre, sem mudança de código.
