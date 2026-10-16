# T-264 · Servidor de aplicação de produção (parte do devops) · devops → orquestrador, arquiteto, backend, segurança

Branch `t-264-imagem-producao`, **empilhada sobre a `origin/t-264-adr-servidor-producao`** (ADR 0027, PR #264). Mesclar o #264 antes (que por sua vez está sobre o #256, da T-258).

**O que foi feito:**
- `infra/docker/backend.Dockerfile` em três etapas: `base` (só o que roda), `producao` (só `requirements.txt`, usuário `giro` uid 10001, `collectstatic` no build, `CMD gunicorn -c /app/gunicorn.conf.py config.wsgi:application`) e `dev` (como era: requirements-dev, root, `runserver`). Sem `--target`, a imagem é o `dev` (compatível com o que já usa o Dockerfile); homologação e produção pedem `--target producao`. Imagem de produção sem build-essential e sem pytest.
- `docker-compose.yml`: `target: dev`; segue com `runserver`.
- `infra/deploy/docker-compose.homologacao.yml` (novo): `estaticos`, `migrar`, `backend`, `worker`, `beat` e `proxy`, com `target: producao` e as `GUNICORN_*` do env. Banco, Redis e frontend externos.
- `backend/requirements.txt`: `gunicorn>=23,<24`. **Motivo para o PR:** servidor WSGI de homologação e produção (ADR 0027); o `runserver` não serve fora do desenvolvimento; a 23 traz as correções de request smuggling.
- `infra/proxy/giro.conf.template`: `location /static/` servindo `ESTATICOS_DIR`.
- `infra/scripts/teste-subida-producao.sh` (novo): ver abaixo. `infra/README.md` sem o aviso "Ainda não há imagem de produção"; seção reescrita.

**Decisão sobre os estáticos do Admin:** o proxy serve `/static/` de um volume, sem whitenoise (sem dependência). `collectstatic` no build; o serviço `estaticos` copia para o volume a cada subida.

**Verificação:** o teste de subida passou com 10 conferências: processo 1 é o Gunicorn, mestre com 2 workers, `gthread` com 4 threads, sem root, sem pytest, requisição pelo proxy responde (HTTP 200), estático do Admin servido, worker e beat de pé, `docker stop` deixa a requisição de 8 s terminar (HTTP 200) e o contêiner sai com 0. A imagem `dev` também builda. Não rodei a suíte do backend: não mudei código Python.

**Desvio da ADR, pequeno:** a ADR põe `RODAR_MIGRACOES=1` num serviço do backend. Fiz um serviço `migrar` à parte que roda com `DATABASE_URL_MIGRACAO` (`giro_migracao`) e sai; o backend só sobe depois e usa `giro_app`, que não tem DDL. Mesma intenção (uma migração por deploy, antes do Gunicorn).

**Achados (não são da imagem):**
1. **Migração com papéis separados falha.** Com `giro_migracao` e `giro_app` de verdade, `migrate_schemas` cai em `ALTER FUNCTION auditoria_expurgar ... OWNER TO giro_expurgo` com `permission denied for schema public`: o novo dono precisa de `CREATE` no schema. Vem de `apps/auditoria/banco.py::aplicar_permissoes`; `infra/postgres/01-papeis.sh` roda certo (conferi: `public` fica de `giro_migracao`). Em dev nunca apareceu porque tudo usa o superusuário (ADR 0016, item 5). Corrigir pede decisão de segurança (dar `CREATE` temporário a um papel sem login, ou outro caminho) e **precisa estar resolvido antes de homologação com papéis separados**. O teste de subida usa o superusuário nas duas URLs por isso. Pede tarefa nova (backend, com a segurança).
2. **Django Admin inalcançável pelo proxy.** O Admin está em `admin.<domínio>/admin/` (`urls_publico.py`), mas o proxy manda `/` para o Next. Os estáticos já saem, mas falta rotear `/admin/` do host da plataforma sem colidir com as rotas do Next. Decisão do arquiteto.

**O que ficou de fora:** rota de saúde para o orquestrador de contêineres (não existe); imagem do frontend de produção (o `frontend.Dockerfile` é de desenvolvimento); medição de memória real (espera o parser da T-265); o frontend e o banco no compose de homologação.

**Próximo passo para quem recebe:** orquestrador abre o PR (depois do #264, que depende do #256); numerar os dois achados.
