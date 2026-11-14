# Criação do schema de empresa com os papéis de banco separados

**Status:** proposta · 14 nov 2026 · T-477 · detalha a 0016 (item 1), a 0025 (item 2) e a 0033 (M-01 da T-355) · revisão da segurança na T-477

## Contexto

Em produção (giro.ceo, tag v0.1.2, 14 nov 2026) nenhuma empresa nasce, nem pela compra pública nem pelo Django Admin:

- `plataforma.services.criar_empresa` chama `empresa.create_schema(check_if_exists=False)` do django-tenants (`CREATE SCHEMA` e as migrações do tenant) pela conexão padrão. Em produção ela é do `giro_app`, que não tem `CREATE ON DATABASE` (ADR 0016; `infra/postgres/01-papeis.sh` só dá ao `giro_migracao`).
- O `ProgrammingError` que resulta é tratado como "schema já existe" e vira `RESERVADO` ("Este endereço é reservado"). O erro real some.
- Mesmo com o schema criado pelo `giro_migracao`, o `01-papeis.sh` só concede privilégio ao `giro_app` no `public`. O `apps.auditoria.banco.aplicar_permissoes` concede no schema de empresa, mas só no `post_migrate`, e só se a migração rodar com os papéis existentes. Num `create_schema` pela conexão de migração ele roda; o worker do convite (`on_commit`) pode, porém, chegar antes do fim e não ler o schema.
- A ADR 0016 já dizia que a criação "pede uma conexão própria para criar o schema"; o código nunca fez isso. Desenvolvimento e testes usam um papel só, por isso nunca apareceu.

A Moto Rápida (`motorapida`) foi criada à mão: `criar_empresa` num contêiner avulso com `DATABASE_URL` do `giro_migracao`, worker parado; depois, como superusuário, `GRANT USAGE` no schema, DML em todas as tabelas, `USAGE, SELECT` nas sequências, `ALTER DEFAULT PRIVILEGES FOR ROLE giro_migracao IN SCHEMA motorapida` (tabelas e sequências) e `REVOKE UPDATE, DELETE, TRUNCATE` em `auditoria_eventoauditoria`.

Restrições:

- O backend web não recebe a `DATABASE_URL_MIGRACAO` (M-01 da T-355; `infra/ci/check-migracao-so-no-worker.sh`). Hoje só o worker que lê a fila `apagamento` a recebe.
- A compra pública já cria a empresa numa tarefa Celery (`compra.executar_pedido_compra`), e a tela `Compra-Pronto` acompanha o `andamento` do pedido por consulta. Ela não depende de a criação ser síncrona na requisição.
- O Django Admin chama `criar_empresa` na requisição, no processo web.
- A auditoria do schema da empresa tem de continuar só `SELECT, INSERT` para o `giro_app` (ADR 0016, item 1).

## Decisão

### 1. Onde e com que papel o schema nasce (a)

**A criação da empresa roda sempre no worker privilegiado, e o schema nasce pela conexão de migração.**

- A fila `apagamento` passa a se chamar `banco` (o worker `worker-apagamento` vira `worker-banco`). Ela leva as tarefas que precisam da `DATABASE_URL_MIGRACAO`: `aud_08_apagar_empresas` e a nova `plataforma.criar_empresa`. O check de CI passa a conferir a fila `banco`; a regra dele não muda (a credencial chega a um worker só, e só ele lê a fila).
- A compra pública manda `executar_pedido_compra` para a fila `banco`. O Django Admin deixa de chamar `criar_empresa` na requisição: grava um `PedidoCompra` com `origem=admin` (ou um registro equivalente do mesmo modelo, ver item 6) e enfileira a mesma tarefa. A tela do Admin mostra o andamento do pedido, como a `Compra-Pronto`.
- Nova função `plataforma.banco.criar_schema(empresa_id)`, irmã de `apagar_schema` e único lugar do código que faz `CREATE SCHEMA`:
  - lê o `schema_name` da `Empresa` no `public` (nunca de fora) e confere o padrão de `schema_apagavel`;
  - abre o alias de banco `migracao` (`DATABASES["migracao"]`, montado de `DATABASE_URL_MIGRACAO` só quando ela existe; sem ela, nos testes e no desenvolvimento de um papel só, usa `default`);
  - `CREATE SCHEMA <nome> AUTHORIZATION giro_migracao` por `psycopg.sql.Identifier`;
  - aplica as concessões do item 2 **antes** das migrações (as `DEFAULT PRIVILEGES` precisam existir antes das tabelas);
  - roda `migrate_schemas --schema=<nome> --database=migracao` (o `post_migrate` reaplica as concessões no fim, item 2);
  - nunca usa `create_schema` do django-tenants; `auto_create_schema` segue desligado.

### 2. Concessões ao `giro_app` no schema novo e nas migrações futuras (b)

Um lugar só: `apps.auditoria.banco.aplicar_permissoes(cursor, schema)` (já existe), ampliado para:

- `GRANT USAGE ON SCHEMA`; DML em todas as tabelas; `USAGE, SELECT` em todas as sequências;
- `ALTER DEFAULT PRIVILEGES FOR ROLE giro_migracao IN SCHEMA <s>` para tabelas e sequências (com `FOR ROLE` explícito, para não depender de quem roda);
- `REVOKE UPDATE, DELETE, TRUNCATE ON <s>.auditoria_eventoauditoria FROM giro_app` sempre por último;
- a parte da função `auditoria_expurgar` como hoje.

Quando roda:

- na criação, antes e depois das migrações (item 1);
- no `post_migrate` de cada schema, como hoje, o que cobre o `migrate_schemas` do deploy em todos os schemas de empresa: tabela nova recebe DML pela regra padrão, e o `REVOKE` da auditoria é refeito mesmo se uma migração recriar a tabela;
- por um comando novo, `python manage.py conceder_privilegios [--schema X | --todos]`, idempotente, que o deploy roda depois do `migrate_schemas` e que serve para regularizar (item 5).

O `01-papeis.sh` não muda: as concessões por schema continuam sendo do backend, como o comentário dele já diz.

Um check novo, `python manage.py conferir_privilegios`, roda no deploy depois do `conceder_privilegios` e falha se, em algum schema de empresa, o `giro_app` não tiver `USAGE`, faltar DML numa tabela ou sequência, ou tiver `UPDATE`, `DELETE` ou `TRUNCATE` na auditoria (consulta a `has_table_privilege` e `has_schema_privilege`).

### 3. Transação, atomicidade e o convite (c)

O DDL roda numa conexão e as linhas do `public` em outra, então não voltam mais juntos numa transação. A ordem passa a ser:

1. **Reserva (public, `giro_app`, transação):** `validar_criacao`, a `Empresa` e o `Dominio`. A `Empresa` nasce com o campo técnico novo `schema_pronto_em = NULL`. É campo de infraestrutura, não um status de negócio: o `status` continua `em_teste` ou `ativa` como na `PLT-01` e na `PLT-16`, e nenhuma regra muda. O `TenantMainMiddleware` e o login recusam empresa com `schema_pronto_em` nulo (404, como subdomínio que não existe). A `UNIQUE` de `schema_name` e `subdominio` resolve a corrida entre duas criações (`Conflito subdominio_em_uso`, como hoje).
2. **Schema (conexão `migracao`):** `banco.criar_schema(empresa_id)`, item 1.
3. **Resto (public e schema da empresa, `giro_app`, transação):** `UsoEmpresa`, `FormaPagamentoAssinatura`, evento `empresa.criar`, 1ª fatura, `plataforma.empresa_criada` (o administrador `convite_pendente` em `contas`) e `schema_pronto_em = agora`. O e-mail do convite sai no `on_commit` desta transação, quando o schema já existe e as concessões já valem. A corrida com o worker deixa de existir.
4. **Falha:** se o passo 2 ou o 3 falhar, a tarefa compensa: `DROP SCHEMA IF EXISTS` pela conexão de migração (pela mesma conferência de `apagar_schema`, mas aceitando só empresa com `schema_pronto_em` nulo, criada por esta tarefa) e, no `public`, remove as linhas do passo 1 (`Dominio` e `Empresa` sem schema pronto nunca foram vistas por ninguém; é desfazer a reserva, não apagar dado de negócio). Se a compensação falhar, a empresa fica com `schema_pronto_em` nulo, invisível, e o Sentry avisa; `conferir_privilegios` e um alarme diário listam empresas sem schema pronto há mais de 1 hora.
5. O `andamento` mantém os passos de hoje (`banco`, `endereco`, `assinatura`, `administrador`), gravados pela tarefa.

### 4. Erro real em vez de `RESERVADO` (d)

- O schema que já existe no Postgres é conferido **antes**, em `validar_criacao`, por `SELECT 1 FROM pg_namespace WHERE nspname = %s` (o `giro_app` lê o catálogo). Só aí a resposta é `RESERVADO`.
- No `CREATE SCHEMA`, só `psycopg.errors.DuplicateSchema` (SQLSTATE `42P06`) vira `RESERVADO` (corrida rara). `InsufficientPrivilege` (`42501`) e qualquer outro erro sobem como exceção: a tarefa registra no Sentry com o SQLSTATE, o pedido vai a `falhou` com a `MENSAGEM_FALHA` de sempre, e o `except ProgrammingError` genérico sai do código.

### 5. Regularizar a Moto Rápida (e)

O contorno fez à mão o que o item 2 faz, com uma diferença: rodou como superusuário. A regularização:

- o deploy da versão com esta ADR roda `conceder_privilegios --todos` e `conferir_privilegios`; para `motorapida` o efeito é nulo (já está concedido) e o check passa a vigiar o schema;
- uma migração de dados do `public` preenche `schema_pronto_em` das empresas cujo schema existe (`pg_namespace`), com a data de criação delas;
- o devops confere que o dono de `motorapida` e das tabelas é o `giro_migracao` (o contorno criou pelo `giro_migracao`, então deve ser) e registra no `infra/README.md` que nenhuma concessão manual é mais necessária.

### 6. O Django Admin

A action de criar empresa grava o pedido e enfileira a tarefa; o formulário devolve para a página do pedido, com o andamento e o erro, se houver. Se o modelo `PedidoCompra` não couber (campos da compra pública que o Admin não tem), o backend propõe no PR um modelo mínimo (`CriacaoEmpresa`) com `status`, `andamento`, `erro` e `empresa`; a decisão desta ADR (a criação nunca roda no processo web) não depende disso.

## Alternativas descartadas

- **Conexão de migração no processo web, como `apagar_schema` faz no worker.** Mantém a criação síncrona e atômica com compensação, mas exige a `DATABASE_URL_MIGRACAO` no backend web, o que a M-01 da T-355 proíbe: qualquer falha do web (injeção, SSRF, leitura de ambiente) passaria a ter DDL em todos os schemas.
- **Função `SECURITY DEFINER` do `giro_migracao` (`criar_schema_empresa(nome)`).** Resolve o `CREATE SCHEMA` sem credencial no web, mas não as migrações do tenant, que são o grosso: o Django teria de migrar como `giro_app` (sem DDL) ou a função teria de executar SQL arbitrário, o que é pior. Serviria só junto com outra das opções.
- **O worker privilegiado roda a criação inteira com o `giro_migracao` como conexão padrão.** Mantém uma transação só, mas grava o `public` e a auditoria como dono, e dono contorna a imutabilidade. O ganho de atomicidade não paga isso; a compensação do item 3 resolve.
- **Dar `CREATE ON DATABASE` ao `giro_app`.** Desfaz a ADR 0016: o papel da aplicação passaria a ser dono dos schemas que cria e poderia apagar os triggers da auditoria.
- **Concessão no `01-papeis.sh` por `ALTER DEFAULT PRIVILEGES` global (sem `IN SCHEMA`).** Cobre tabelas novas, mas não o `USAGE` do schema nem o `REVOKE` da auditoria, que é por tabela; continuaria precisando do passo por schema.
- **Criar o schema por `create_schema` dentro da transação, com `SET ROLE giro_migracao`.** Exige o `giro_app` ser membro do `giro_migracao`, o que equivale a ter a credencial.

## Consequências

- A criação de empresa fica assíncrona também no Admin. A compra pública não muda para quem compra (já era tarefa e já mostrava o andamento).
- O worker `banco` (antes `worker-apagamento`) passa a rodar também a criação. O volume é baixo (uma criação por compra); a fila é a mesma e a credencial continua em um serviço só.
- Surge um estado técnico, empresa reservada sem schema pronto, que precisa ser invisível e vigiado (item 3).
- Desenvolvimento e testes continuam com um papel só, exceto os testes do item "Especificação", que sobem com os dois.
- O devops renomeia a fila e o serviço nos três composes, no check e no `infra/README.md`, e acrescenta `conceder_privilegios` e `conferir_privilegios` ao serviço `migrar`.

## Especificação para o backend

1. `config/settings`: alias `DATABASES["migracao"]` só quando `DATABASE_URL_MIGRACAO` existe; `CELERY_TASK_ROUTES` com `aud_08_apagar_empresas`, `plataforma.criar_empresa` e `executar_pedido_compra` na fila `banco`.
2. `plataforma.banco.criar_schema(empresa_id)` e `plataforma.banco.desfazer_schema(empresa_id)` (compensação, só com `schema_pronto_em` nulo), pelos critérios do item 1 e do item 3.
3. `Empresa.schema_pronto_em` (`DateTimeField`, nulo), migração de dados do item 5, e recusa no middleware e no login para empresa sem schema pronto.
4. `services.criar_empresa` dividido nos três passos do item 3, chamado só pela tarefa; o Admin enfileira (item 6).
5. `validar_criacao` com a conferência de `pg_namespace`; fim do `except ProgrammingError` genérico (item 4).
6. `auditoria.banco.aplicar_permissoes` ampliado (item 2) e os comandos `conceder_privilegios` e `conferir_privilegios`.
7. Testes, com os dois papéis separados num banco de teste próprio (precedente: os testes de imutabilidade que sobem com `giro_app`; o fixture cria `giro_migracao` e `giro_app` como no `01-papeis.sh` e aponta `default` para o `giro_app` e `migracao` para o `giro_migracao`):
   - `test_plt_01_cria_empresa_com_papeis_separados`: a tarefa cria a empresa; o schema é do `giro_migracao`; o `giro_app` lê e grava numa tabela de negócio e cria o administrador;
   - `test_plt_01_giro_app_nao_cria_schema`: `banco.criar_schema` sem o alias `migracao`, com o `default` no `giro_app`, falha com `InsufficientPrivilege`, e o pedido vai a `falhou` com a `MENSAGEM_FALHA`, não `RESERVADO`;
   - `test_plt_01_schema_existente_e_reservado`: schema que já existe no `pg_namespace` dá `RESERVADO` antes de qualquer DDL;
   - `test_plt_01_falha_desfaz_reserva`: falha no passo 3 apaga o schema e as linhas do passo 1;
   - `test_plt_01_convite_depois_do_schema`: o `on_commit` do convite roda com o schema pronto e o `giro_app` lê o administrador;
   - `test_aud_02_auditoria_so_select_insert_em_empresa_nova`: no schema criado, `UPDATE`, `DELETE` e `TRUNCATE` na auditoria falham para o `giro_app`;
   - `test_aud_02_migracao_futura_mantem_privilegios`: uma tabela criada depois (migração de teste) recebe DML para o `giro_app`, e a auditoria segue sem `UPDATE`;
   - `test_conferir_privilegios_acusa_schema_sem_concessao`.
8. O CI roda esses testes com os dois papéis (o job de imutabilidade já sobe o `giro_app`).

## O que a segurança revisa

- Que a `DATABASE_URL_MIGRACAO` continua num serviço só (`worker-banco`) e que o check de CI cobre a fila renomeada nos três composes.
- Que a tarefa `plataforma.criar_empresa` só aceita `empresa_id` (ou `pedido_id`) e nunca um nome de schema; e que `criar_schema` e `desfazer_schema` conferem o padrão do nome e, no caso do `desfazer`, recusam empresa com `schema_pronto_em` preenchido (não pode virar um segundo caminho de `DROP SCHEMA` fora do `apagar_schema`).
- Que quem pode enfileirar a criação é só a compra pública confirmada e o Admin com 2 etapas; que a fila `banco` não aceita tarefa de outro produtor (o Redis tem senha, T-274).
- As concessões: `FOR ROLE giro_migracao` explícito, `REVOKE` da auditoria sempre por último, `conferir_privilegios` no deploy; e que o contorno da Moto Rápida não deixou concessão a mais (por exemplo, a `PUBLIC` ou ao `giro_expurgo` além da tabela de eventos).
- Que a empresa com `schema_pronto_em` nulo não é alcançável por subdomínio, login nem API, e que a remoção das linhas da reserva na compensação não atinge empresa que já foi vista.
- Que o erro real (SQLSTATE) vai só ao Sentry e ao log, e que a resposta ao cliente segue genérica.
