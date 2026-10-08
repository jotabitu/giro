# T-010 · Plataforma: planos, empresas, criação de schema · backend → frontend, qa, arquiteto, devops, orquestrador

**O que foi feito:**
- `plataforma`: `Plano` (Essencial, Profissional e Completo na migração 0005, com recursos da tela Compra-Planos), `Empresa` completa e como máquina de estados (`transicao_empresa`), `UsoEmpresa` (resumo no public). `services.criar_empresa` (chamado pelo Django Admin, "Criar empresa" só para o dono) cria a empresa `em_teste` (teste de 14 dias, preço contratado = preço do plano), o domínio, o schema com as migrações, o uso, o evento de auditoria `empresa.criar` e publica `plataforma.empresa_criada`; tudo numa transação (falha não deixa schema nem e-mail).
- Limites (`PLT-03`): `exigir_limite(item)` com `SELECT ... FOR UPDATE` no `UsoEmpresa`, `atualizar_uso(item, delta)` com aviso de 90% por e-mail aos administradores (uma vez por item e por mês, depois do commit), `registrar_contador` para os apps de baixo e a tarefa noturna `plataforma_recalcular_uso_de_todas` (Beat, 03:30).
- `situacao` da empresa decidida numa anotação SQL só (`selectors.com_situacao`), usada pela lista (filtro `?situacao=` e `contagens`) e pelo detalhe, na ordem da tabela do contrato.
- API fase 1: `GET /api/plataforma/planos/`, `/empresas/` (cursor, filtros, `?ordem=`, `contagens`), `/empresas/{id}/`; `GET /api/assinatura/` no host da empresa. Método de fase 2 em rota de fase 1 responde 404 (CA-010-14).
- `PaginacaoPorCursor.get_paginated_response(dados, extras={...})` e `envelope_sem_paginas` (ponto 6 da T-045).
- `contas`: `Usuario.status` (`convite_pendente`, `ativo`, `desativado`) no lugar de `ativo`, pela máquina de estados (`transicao_usuario`); `tentativas_erradas`, `bloqueado_ate`, `celular`; `exige_2fa` como propriedade (sempre na plataforma). `Convite` com hash do token e 7 dias. Assinante de `plataforma.empresa_criada` convida o administrador (`convite_pendente`, conta no plano; e-mail pela tarefa `contas_enviar_convite`, que recebe só ids e gera o token na hora).
- Login da equipe (`PLT-08`): `entrar` (e-mail, senha e código ou código de recuperação numa chamada), `2fa/configurar`, `2fa/verificar` (8 códigos de recuperação, só nessa resposta), `renovar` e `sair` (cookie `__Host-giro_refresh`, cabeçalho `X-Requested-With: giro`, empresa conferida antes da blacklist), `eu` com `pode` (`PLT-09`), convite (`convites/{token}/`, `aceitar/`) e o comando `convidar_equipe_plataforma`. 3 códigos errados bloqueiam por 15 minutos com evento de segurança no public.
- `comum`: `relogio.py` (hora do domínio; fixture `relogio` nos testes, 07 out 2026 10:00), `documentos.py` (CNPJ com dígito verificador), `erros.py` (`ErroDeValidacao` 400, `NaoAutenticado` 401, `SemPermissao` 403, `MuitasTentativas` 429), `autenticacao.py` (claim `amr`, token `pre_2fa`, `2fa_obrigatorio`, cookie), `openapi.py`.

**Onde:** `backend/apps/plataforma/` (models, migrations 0003 a 0005, services, selectors, permissoes, tasks, admin, api/), `backend/apps/contas/` (models, migrations 0002 e 0003, services, dois_fatores, eventos, tasks, api/, management/), `backend/comum/`, `backend/config/` (urls, urls_publico, urls_openapi, settings), `backend/tests/aceitacao/`, `docs/api/openapi.yaml`.

**Contrato:** `docs/api/plataforma.md` (fase 1) e `docs/api/openapi.yaml`.

**Regras cobertas:** PLT-01, PLT-03, PLT-08, PLT-09, IMP-05. Os 17 critérios de `docs/qa/criterios/T-010.md` saíram de `xfail` e passam (20 testes em `tests/aceitacao/test_t010_plataforma.py`, `test_plt_*`/`test_imp_05_*`), mais `apps/plataforma/tests/`, `comum/tests/test_paginacao.py`, `comum/tests/test_documentos.py` e os novos casos de `tests/test_autenticacao.py`.

**Check:** ruff check, ruff format --check, mypy e pytest limpos: `215 passed, 88 xfailed` (os xfail são de T-011 a T-014). Os 47 avisos são `InsecureKeyLengthWarning` da `DJANGO_SECRET_KEY` curta de `config/settings/test.py` (anterior a esta tarefa). Como o compose desta máquina ainda não estava de pé, rodei contra um Postgres descartável, com autorização do Orquestrador, e o removi no fim:

```
MSYS_NO_PATHCONV=1 docker run -d --rm --name giro-backend-teste-db -p 55432:5432 \
  -e POSTGRES_DB=giro -e POSTGRES_USER=giro -e POSTGRES_PASSWORD=giro-teste-local \
  -e POSTGRES_PASSWORD_MIGRACAO=migracao-teste-local -e POSTGRES_PASSWORD_APP=app-teste-local \
  -v "C:/Users/Jota/Documents/giro-backend/infra/postgres:/docker-entrypoint-initdb.d:ro" postgres:16
# no backend/, com as dependências de requirements-dev.txt num venv local:
DJANGO_SETTINGS_MODULE=config.settings.test DATABASE_URL=postgres://giro:giro-teste-local@localhost:55432/giro \
  sh -c "ruff check . && ruff format --check . && mypy . && pytest -q --create-db"
docker rm -f giro-backend-teste-db
```

**Arquivos do devops que mexi (a pedido do Orquestrador, commit `ci(infra): ...`):** `Makefile` (alvo `api-schema`), `.github/workflows/ci.yml` (passo do OpenAPI) e `infra/README.md`: o `spectacular` passou a usar `--urlconf config.urls_openapi`, que junta as rotas da empresa e as da plataforma (as da plataforma ficam no urlconf do public e não apareciam). **DevOps: revise esse trecho.**

**Decisões de implementação (Arquiteto, confira):**
1. `plataforma` não pode importar `contas` (ADR 0011). O login da equipe ficou em `contas/api/plataforma.py`, montado em `/api/plataforma/` pelo `urls_publico`; o administrador da empresa nova é criado por `contas` assinando `plataforma.empresa_criada`.
2. Etapa do funil (`IMP-05`) a partir dos 10 passos: `dados` = passo `importar`; a etapa é a primeira do funil ainda não concluída. "Parada no passo N" usa o primeiro dos 10 passos ainda aberto.
3. `Empresa.TRANSICOES` só tem as saídas da tabela de estados das regras; pausar e cancelar entram com as ações da fase 2.
4. `contagens`: `em_teste` e `ativa` contam o status; `com_problema` e `saindo`, a aba da situação; `pagantes` = todas menos `em_teste` (bate com o exemplo 148 = 125 + 23). O filtro `?situacao=` segue a mesma regra.
5. Fora da tabela: empresa `cancelada` depois de `acesso_ate` sai com `{codigo: "cancelada", rotulo: "Cancelada", tom: "neutro"}`; `fatura_atrasada` sai como "Fatura atrasada" sem os dias, que dependem das faturas (fase 2).
6. No detalhe, `acoes` vem todo `false` na fase 1 (as ações são da fase 2) e `chamados_abertos: 0`.
7. Bloqueio do `PLT-08` é do Giro; o atraso progressivo do django-otp foi desligado (`OTP_*_THROTTLE_FACTOR = 0`), porque recusaria o código certo logo depois de errar.
8. O token do convite nunca vai para a fila: a tarefa de envio gera outro na hora (o link anterior deixa de valer, como no "reenviar").

**Produto, confira os textos:** `faixa_aviso` de `inadimplente`, `suspensa` e `pausada` (`selectors.FAIXA_AVISO`), o e-mail "limite do plano em 90%" e o e-mail do convite foram escritos por mim, sem tela de referência.

**O que ficou de fora:**
- `sid` (sessões, ADR 0014), token de suporte, 2 etapas dos perfis da empresa, login e convite da locadora, e-mail único com `Lower(email)`: T-011. O `Usuario.status` que a T-011 pedia já está feito.
- `ConfiguracaoEmpresa` padrão na criação (app `empresas`, sem model ainda).
- `registrar_acesso` existe, mas ninguém chama ainda (login da empresa, T-011). `registrar_passo_implantacao("conta")` deve ser chamado quando a administradora criar a senha (T-011).
- Contadores de `veiculos` e `filiais` para o recálculo noturno: T-012 e T-013 registram com `registrar_contador`.
- Aviso de 90% sai por e-mail direto na tarefa da plataforma; troca para `notificacoes.enviar` quando o app existir.
- A AUT-16 (expurgo mensal, T-053) não faz parte desta tarefa.

**Próximo passo para quem recebe:**
- Frontend: login da plataforma e telas Plat-* podem usar a API real (`docs/api/openapi.yaml`). Dados de exemplo: `convidar_equipe_plataforma` e o "Criar empresa" do Django Admin.
- QA: os testes de T-010 estão preenchidos e sem `xfail`; a fixture `relogio` está no `conftest.py` da raiz e `criar_empresa`/`equipe` em `tests/aceitacao/conftest.py`. Atualize a cobertura em `docs/qa/cobertura-de-regras.md`.
- T-012/T-013/T-011: chamem `exigir_limite` e `atualizar_uso` na mesma transação do cadastro e registrem o contador no `ready()` (ver `apps/plataforma/README.md`).
