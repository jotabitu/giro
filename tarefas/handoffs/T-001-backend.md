# T-001 · Esqueleto do backend · backend → orquestrador, devops, frontend, qa, seguranca

**O que foi feito:** projeto Django 5.2 (LTS) em `backend/`:
- settings `base`, `dev`, `test`, `prod`;
- django-tenants com `plataforma.Empresa` e `plataforma.Dominio` no public, um schema por empresa;
- apps na ordem da ADR 0011, incluindo `contratos` (vazio);
- `contas.Usuario` nos dois schemas (ADR 0008);
- DRF com drf-spectacular em `/api/schema/` e `/api/docs/`;
- Celery em `config/celery.py`;
- pytest com duas empresas de teste (`empresa_a`, `empresa_b`).

Fundação em `backend/comum/` (ADRs 0009 a 0012), com testes:
- `ModeloBase`, `ModeloAtivavel`, `ModeloComCodigo` e `Sequencia`: código por empresa sem buracos, testado com 6 threads concorrentes;
- campos e funções de dinheiro em centavos com ROUND_HALF_UP;
- `MaquinaDeEstados` + `transicionar`, que audita;
- erros 422/409/403 e handler no formato de `docs/api/README.md`;
- `EventoAuditoria` imutável em 3 camadas (model, queryset, trigger PostgreSQL em cada schema) e expurgo só acima de 5 anos;
- eventos de domínio, tarefas por empresa, JWT preso à empresa, `EmpresaOperando`, paginação por cursor.

Da ADR 0013 (revisão T-032) entram S-01 e S-04:
- tokens com `schema` e `empresa_id`, conferidos por `conferir_empresa` (401 `nao_autenticado`);
- Admin só no public com `OTPAdminSite`; `django.contrib.admin` só em `SHARED_APPS`;
- sem CORS.

Da ADR 0014 nada entrou: tudo fica para a T-033.

**Onde:** `backend/config/`, `backend/comum/`, `backend/apps/{plataforma,contas,auditoria}/models.py` e migrações, `backend/conftest.py`, `backend/tests/`, `backend/README.md` (tabela da fundação e comandos).

**Contrato:** `docs/api/openapi.yaml` gerado, ainda sem paths (a T-001 não tem endpoint de negócio). Erros e listas seguem `docs/api/README.md`.

**Verificado nesta máquina:**
- `ruff check . && ruff format --check . && mypy . && pytest -q` no container do backend: verde, 88 testes, mypy estrito.
- `docker compose up backend worker beat` sobe; `migrate_schemas` aplica tudo.
- `/api/schema/` dá 200 em `localhost` e `admin.localhost`; `admin.localhost/admin/` dá 302 para o login com 2 etapas; host desconhecido dá 404.
- `docker compose up` completo, num worktree temporário com T-001 + T-002 mescladas: os 6 serviços sobem, frontend responde 307 e API 200. O worktree e os volumes foram apagados depois.

**Regras e ADRs cobertas (testes):**
- AUD-01: `test_aud_01_*` em `comum/tests/test_auditoria.py`. Cobre UPDATE e DELETE direto no banco falhando, model e queryset recusando, evento com ator, antes e depois, IP e aparelho, e CPF mascarado.
- AUD-02: `test_aud_02_expurgo_so_apaga_eventos_com_mais_de_5_anos`.
- USR-04: `test_usr_04_token_de_usuario_desativado_recusado`.
- PLT-03: `test_plt_03_limite_do_plano_vira_422`, que testa só o formato do erro.
- ADR 0008/0013:
  - `tests/test_autenticacao.py`: token da A recusado na B mesmo com o mesmo `user_id`, e token sem `empresa_id` recusado;
  - `tests/test_rotas.py`: Admin inexistente no host da empresa.
- Isolamento: `tests/test_isolamento.py`.
- Limites entre apps: `tests/test_limites_entre_apps.py`.
- ADR 0009: `16.068,00 / 12 = 1.339,00` e `3% de 21.068,00 = 632,04`.

**Decisões de implementação (Arquiteto, confira):**
- `Empresa` só tem `nome` e `status`, e `Usuario` só tem `email`, `nome`, `perfil`, `funcao_plataforma` e `ativo`: o django-tenants e o `AUTH_USER_MODEL` precisam existir desde a 1ª migração. A T-010 e a T-011 completam os campos.
- `comum.auditoria` grava `EventoAuditoria` por `apps.get_model`, sem import, porque `auditoria` está abaixo de `comum` na ordem.
- Os status de empresa que o `comum` precisa conhecer ficam em `comum/empresa.py`, e um teste confere que batem com `Empresa.Status`.
- Tirei o `SHOW_PUBLIC_IF_NO_TENANT_FOUND`: host sem domínio cadastrado dá 404, como pede `docs/api/README.md`. A migração `plataforma.0002` cria a linha do public em `Empresa` (ADR 0013), com os domínios `admin.<DOMINIO_BASE>` e, em dev, `localhost` e `127.0.0.1`.
- `Usuario.is_active` é propriedade sobre `ativo`.

**Dependências (registrar no PR):**
- Django, DRF, django-tenants, psycopg 3, simplejwt, drf-spectacular, celery[redis], django-otp, argon2-cffi e sentry-sdk: todas já previstas na stack.
- django-environ: lê `DATABASE_URL` e as listas do `.env`.
- Desenvolvimento: ruff, mypy, django-stubs, djangorestframework-stubs, celery-types, pytest, pytest-django.
- Versões em faixa compatível; o lock fica para a T-005.

**O que ficou de fora:**
- T-011: 2FA no JWT (`pre_2fa`, `amr`, `exige_2fa` como propriedade), token de suporte, cookie `__Host-giro_refresh`, views de entrar/renovar/verificar/sair (devem chamar `conferir_empresa`) e `contas.Sessao`.
- T-033: cifra, hash de busca e `CAMPOS_AUDITORIA`. Até lá a auditoria mascara CPF, CNH e documento pelo nome do campo e ignora `password`.
- T-012: escopo por filial em `comum/permissoes.py`.
- T-014: `comum/arquivos.py` (S3 com URL assinada), que pede django-storages e boto3.
- T-010: telas do Admin para `Empresa`.
- T-019 (qa): comando `seed_moto_rapida`.

**Para o devops:**
1. Pode tirar o desvio de `backend-check` no `Makefile`.
2. `backend-check` usa `run --no-deps`: o db precisa estar de pé, e o entrypoint migra o banco de dev antes do pytest. Funciona, mas vale saber.
3. No Git Bash, `make api-schema` precisa de `MSYS_NO_PATHCONV=1`: sem isso `/tmp/openapi.yaml` vira caminho do Windows.
4. `DJANGO_CORS_ALLOWED_ORIGINS` não é mais lida (ADR 0013). Pode sair do `.env.example`, e falta o proxy de mesma origem (`/api/` → Django).
5. O Beat grava `celerybeat-schedule` no bind mount; ignorado em `backend/.gitignore`.

**Próximo passo para quem recebe:**
- Devops/T-005: o CI roda o mesmo comando do `backend-check` e confere o `openapi.yaml`.
- Frontend: o cliente tipado pode ser gerado, mas está vazio até a T-010/T-011.
- QA: fixtures `empresa_a`, `empresa_b`, `publico` em `backend/conftest.py`; model de exemplo em `backend/tests/app_exemplo/`.
- Segurança: revisar `comum/autenticacao.py`, `comum/auditoria.py` (máscaras) e o trigger em `apps/auditoria/migrations/0002_trigger_imutavel.py`.
- Backend (eu): T-033 em seguida.
