# Backend

Django 5 + Django REST Framework + django-tenants + Celery, sobre PostgreSQL 16 e Redis. Dono: agente **backend**. Leia `CLAUDE.md` e `.claude/agents/backend.md` antes de mexer aqui.

## Estrutura

```
backend/
├── config/            settings (base, dev, test, prod), urls, celery, asgi/wsgi
├── apps/              um app por domínio (tabela abaixo)
├── comum/             base de models (auditoria automática, códigos sequenciais, dinheiro), permissões, erros de negócio
├── integracoes/       interfaces + implementações falsas: pagamento, assinatura eletrônica, WhatsApp, NF-e, FIPE
├── templates/pdf/     modelos de contrato, recibo e termo (WeasyPrint)
├── seed/              empresa de exemplo Moto Rápida (agente qa)
└── tests/             testes transversais: isolamento entre empresas, permissões por perfil
```

## Apps

| App | Schema | Regras | Escopo |
| --- | --- | --- | --- |
| `plataforma` | public | PLT, IMP | Planos, empresas (tenants), faturas da assinatura, usuários da plataforma, acesso de suporte, implantações e chamados. |
| `contas` | empresa | USR | Usuários da empresa, perfis, permissões extras, filiais do usuário, convites, sessões, 2FA, login. |
| `empresas` | empresa | IMP | Dados da empresa, marca (cor, logo, nome), configurações gerais, assistente de implantação, integrações. |
| `filiais` | empresa | PLT-03 (limite) | Filiais, matriz, horário de funcionamento. |
| `veiculos` | empresa | VEI | Categorias e tabela de preços, veículos, documentos, leitura de km, histórico de status. |
| `clientes` | empresa | CLI, AUD-04, AUD-06 | Clientes PF/PJ, CNH, documentos, contatos, bloqueio, consentimento LGPD. |
| `contratos` | empresa | LOC, VEN | Modelos de contrato versionados, contratos gerados, assinatura eletrônica, PDF (ADR 0011). |
| `locacoes` | empresa | LOC | Planos especiais, locações, reservas, renovação, cancelamento. |
| `vistorias` | empresa | VIS, DEV | Vistoria de saída e de devolução, fotos, avarias, acerto da devolução e da caução. |
| `vendas` | empresa | VEN | Propostas, funil, simulação de pagamento, troca, venda, recibo. |
| `aprovacoes` | empresa | APR | Pedidos de aprovação (desconto, cancelamento, despesa, correção de km), prazos e lembretes. |
| `financeiro` | empresa | FIN | Contas a receber (parcelas), despesas, caixa do dia, movimentos, conciliação bancária, comissões, DRE. |
| `manutencao` | empresa | MAN | Ordens de serviço, oficinas, preventivas por km e data. |
| `notificacoes` | empresa | AUT (canais) | Envio por WhatsApp, e-mail e push com a marca da locadora; preferências por pessoa; sino. |
| `automacoes` | empresa | AUT | Tarefas Celery AUT-01 a AUT-15, agendadas por empresa no fuso America/Sao_Paulo. |
| `auditoria` | empresa + public | AUD | Eventos imutáveis, exportação de dados, anonimização LGPD, retenção após cancelamento. |
| `relatorios` | empresa | FIN-13, relatórios | Indicadores das telas iniciais, relatórios e DRE (só leitura, a partir dos outros apps). |

Ordem de dependência entre apps e eventos de domínio: ADR 0011. Teste: `tests/test_limites_entre_apps.py`.

## Fundação (`comum/`, T-001 e T-033)

| Módulo | Uso |
| --- | --- |
| `models.py` | `ModeloBase` (sempre), `ModeloAtivavel`, `ModeloComCodigo` (`PREFIXO_CODIGO = "LOC"`), `Sequencia`, `ModeloComCifra` (`id_cifra`, obrigatório com `CampoCifrado`) |
| `codigos.py` | `proximo_numero`, `formatar_codigo`, `ajustar_sequencia` (seed) |
| `campos.py` | `CentavosField`, `CentavosComSinalField`, `PercentualField`, `CampoCifrado` (`obj.definir_<campo>(...)`, `obj.<campo>_claro()`), `CampoHashBusca(de=...)`, `anonimizar_cifrado`, `buscar_por_hash` |
| `cripto.py` | AES-256-GCM com dado associado `empresa_id\|tabela\|campo\|id_cifra`, `hash_busca` (HMAC por empresa) (ADR 0014) |
| `classificacao.py` | `CAMPOS_AUDITORIA = {"omitir", "mascarar", "inteiro"}` e as máscaras da ADR 0014; teste de arquitetura em `tests/test_campos_sensiveis.py` |
| `dinheiro.py` | `aplicar_percentual`, `proporcional`, `dividir_em_parcelas` (ROUND_HALF_UP no centavo) |
| `estados.py` | `MaquinaDeEstados` (`TRANSICOES`, `REGRA_TRANSICAO`) e `transicionar(obj, status, motivo=...)` |
| `erros.py` | `ErroDeValidacao` 400, `NaoAutenticado` 401, `SemPermissao` 403, `ErroDeRegra` 422, `TransicaoInvalida`/`Conflito` 409, `LimiteDoPlano` 422, `EmpresaSemOperacao` 403, `MuitasTentativas` 429, handler do DRF |
| `auditoria.py` | `auditar(obj, acao, categoria)`, `registrar_evento(...)`, `ator_atual()`, `usar_ator(...)`; o diff é feito com os valores reais e só depois classificado |
| `eventos.py` | `publicar("<app>.<fato>", ...)`, `assinar`, `@assinante` |
| `tarefas.py` | `@tarefa_de_empresa`, `na_empresa(schema, ator=...)`, `ator_para_fila()`, `para_cada_empresa(tarefa)`; empresa inexistente, fora de operação ou com schema apagado não roda |
| `worker.py` | antes e depois de toda tarefa Celery: conexão no public e ator Sistema (S-11) |
| `rede.py` | `ip_do_cliente(request)`: `X-Forwarded-For` só de proxy em `GIRO_REDES_PROXY`, entrada `xff[-GIRO_PROXIES_CONFIAVEIS]` (ADR 0018) |
| `autenticacao.py` | `emitir_tokens(usuario, amr=...)` (claims `schema`, `empresa_id`, `amr`), `emitir_pre_2fa`, `conferir_empresa`, `JWTDaEmpresa` (401 `2fa_obrigatorio` sem `otp` para quem `exige_2fa`), `JWTPre2FA`, cookie `__Host-giro_refresh` e `refresh_do_cookie` (ADR 0013) |
| `permissoes.py` | `EmpresaOperando` e `EscopoDeFilial` (padrão: `X-Filial` fora do escopo dá 403 `USR-07`), `exige_perfil(...)`, `filial_pedida`, `filiais_permitidas`, `registrar_escopo_de_filial` |
| `leituras.py` | leituras compostas entre apps (ADR 0015): `registrar_anotacao`/`aplicar`/`blocos` e `registrar_contador`/`contar` (contador ausente vale 0) |
| `paginacao.py` | envelope `resultados`/`proximo`/`anterior`; extras no mesmo corpo com `get_paginated_response(dados, extras={"contagens": ...})`; `envelope_sem_paginas` para listas curtas |
| `relogio.py` | `agora()` e `hoje()` (dia em São Paulo): serviços e selectors leem a hora só daqui; nos testes, fixture `relogio` (07 out 2026, 10:00) |
| `documentos.py` | `so_digitos`, `cnpj_valido` (dígitos verificadores) |
| `arquivos.py` | arquivo privado (ADR 0009, `AUD-05`): `FileField(storage=arquivos.armazenamento_privado, upload_to=arquivos.caminho_privado)`, caminho `<schema>/<app>/<model>/<id>/<uuid>.<ext>` (grave o objeto antes do arquivo), `validar(arquivo)` (PDF, JPG ou PNG pelo conteúdo, até 10 MB), `url_assinada(caminho)` de 15 minutos; `GIRO_ARMAZENAMENTO=falso` (memória) ou `s3` (`S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGIAO`, `S3_CHAVE_DE_ACESSO`, `S3_CHAVE_SECRETA`) |
| `openapi.py` | autenticações do Giro no OpenAPI |

Cache: toda chave leva o schema (`django_tenants.cache.make_key`). Celery: `CELERY_TASK_IGNORE_RESULT = True`; argumentos de tarefa só ids.

Auditoria no banco (ADR 0016): triggers recusam `UPDATE`, `DELETE` e `TRUNCATE`; só `auditoria_expurgar(limite)`, do papel `giro_expurgo`, apaga evento com mais de 5 anos. Os `GRANT` de `giro_app` e `giro_expurgo` em cada schema saem de `apps/auditoria/banco.py` no `post_migrate`.

Exemplo de model de domínio: `tests/app_exemplo/models.py` (instalado só nos testes).

## Comandos

```
docker compose up -d backend worker beat
docker compose run --rm --no-deps backend sh -c "ruff check . && ruff format --check . && mypy . && pytest -q"
docker compose exec backend python manage.py createsuperuser   # no public: dono da plataforma
docker compose exec backend python manage.py convidar_equipe_plataforma larissa@girolocadoras.com.br suporte --nome "Larissa Melo"
docker compose exec backend python manage.py spectacular --urlconf config.urls_openapi --file /tmp/openapi.yaml --validate
```

Os testes criam as empresas `empresa_a` (`empresa-a.localhost`) e `empresa_b` uma vez por banco de teste (`--reuse-db`). Depois de mudar migração, rode `pytest --create-db`.

O Admin só existe em `admin.localhost:8000/admin/` e exige 2 etapas (OTPAdminSite): crie um dispositivo TOTP para o usuário pelo shell antes do primeiro login.
