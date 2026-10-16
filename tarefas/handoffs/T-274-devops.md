# T-274 · Senha no Postgres e no Redis em homologação e produção · devops → orquestrador, segurança, backend

Branch `t-274-senhas-banco-redis`, **empilhada sobre a `origin/t-264-imagem-producao`** (PR #271) e com a `origin/t-276-papeis-banco` (PR #275, da segurança) **mesclada dentro**, porque o teste de subida com papéis separados só passa com a correção da T-276. Mesclar o #275 e o #271 antes; o diff do PR perde essas partes.

**O que foi feito:**
- `backend/config/settings/prod.py`: recusa subir com `DATABASE_URL` sem senha e com `REDIS_URL`, `CELERY_BROKER_URL` ou `CELERY_RESULT_BACKEND` sem senha. Ausente cai no padrão de `base.py` (sem senha) e também é recusado. Testes `test_t274_*` em `backend/tests/test_producao.py` (e `AMBIENTE_PROD` com as três URLs do Redis com senha).
- `infra/deploy/*.env.example`: `REDIS_URL`, `CELERY_BROKER_URL` e `CELERY_RESULT_BACKEND` (obrigatórias, em branco) e o formato das URLs com senha, para banco e Redis.
- `infra/scripts/teste-subida-producao.sh`: agora com `giro_migracao` e `giro_app` separados (como a segurança pediu na T-276), Redis com `requirepass`, e conferências novas: o Redis responde NOAUTH sem senha e PONG com ela; o Postgres recusa `giro_app` sem senha e atende com ela; a imagem `producao` recusa `DATABASE_URL`, `REDIS_URL` e `CELERY_BROKER_URL` sem senha. Passou: 17 conferências.
- `infra/README.md`: seção "Senha no Postgres e no Redis" e o trecho do teste de subida atualizado (não usa mais o superusuário).

**Verificação:** ruff check, ruff format --check e `mypy .` limpos; `tests/test_producao.py` com 60 passando. Não rodei a suíte completa (mudança só em `prod.py`, que os testes de produção cobrem).

**O que ficou de fora:**
- A rede (Postgres e Redis só alcançáveis pela rede interna) continua regra de rede do deploy, sem teste aqui.
- Senha forte, rotação e TLS do Redis: do cofre e do ambiente; o exemplo cita `rediss://`.
- O `REDIS_URL` vazio em `.env` de desenvolvimento não muda: `prod.py` só vale em homologação e produção.

**Próximo passo para quem recebe:** orquestrador abre o PR (depois do #275 e do #271). Segurança confere se a condição da T-247 está fechada.
