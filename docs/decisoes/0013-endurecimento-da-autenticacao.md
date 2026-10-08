# Endurecimento da autenticação (tokens, suporte, 2 etapas, Admin, cookie)

**Status:** aceita · 07 out 2026 · complementa a 0008 (revisão de segurança T-032)

## Contexto

A revisão de segurança da fundação (T-032, `docs/seguranca/2026-10-07-fundacao.md`) encontrou cinco falhas no desenho da 0008:

1. A claim `schema` só era conferida na autenticação das views do DRF; as views do simplejwt (obter, renovar, verificar, sair) não passam por ela. Um refresh da empresa A enviado ao host da B passaria (a blacklist da B não conhece o `jti`) e ainda gravaria `OutstandingToken` no schema B com o `user_id` de outra pessoa.
2. O token de suporte carregava o `user_id` do `public`, que no schema da empresa aponta para outro usuário.
3. O fluxo de 2 etapas com JWT não estava desenhado (o `OTPMiddleware` do django-otp é de sessão), e `exige_2fa` era um campo solto.
4. O Django Admin estaria no urlconf da empresa, com login de sessão, sem 2 etapas e fora dos serviços e da auditoria.
5. O refresh no navegador e o CORS não estavam definidos; com `*.girolocadoras.com.br` todo subdomínio vizinho é *same-site*.

## Decisão

### 1. Todo token é conferido contra a empresa, em todas as views

- Claims obrigatórias em todo token emitido: `schema` (nome do schema) **e** `empresa_id` (PK da `Empresa` no `public`, nunca reaproveitada; o tenant `public` também tem linha em `Empresa`). Nome de schema pode voltar a existir depois que uma empresa cancelada é apagada (`AUD-08`); o `empresa_id` não volta.
- `comum.autenticacao` tem uma função única `conferir_empresa(token)` que exige `schema == connection.schema_name` e `empresa_id == connection.tenant.pk`. Claim ausente ou diferente → 401 `nao_autenticado`.
- Ela é chamada pela classe de autenticação do DRF **e** pelos serializers próprios de obter, renovar, verificar e sair, que substituem os do simplejwt. Os serializers conferem a empresa **antes** de consultar a blacklist ou gravar `OutstandingToken`. As views padrão do simplejwt não são montadas em nenhum urlconf.

### 2. Token de suporte é outro tipo de token

- `token_type = "suporte"`, sem refresh, `exp` = `AcessoSuporte.fim`. Claims: `schema`, `empresa_id`, `acesso_suporte_id`, `permissao`. Sem `user_id`.
- A autenticação reconhece o tipo e **nunca** busca `contas.Usuario` no schema da empresa: monta um `AtorSuporte` (objeto em memória, não é model) com o nome do usuário da plataforma, que age com o alcance de um administrador em todas as filiais.
- A cada requisição confere no `public`: `AcessoSuporte` com status `ativo`, `fim` no futuro, da mesma `empresa_id`, e `Empresa.suporte_bloqueado = False`. Qualquer falha → 401 `{ "codigo": "PLT-07" }`.
- "Só ver" é uma **lista de rotas permitidas**, não "todo GET": cada view marca `suporte_somente_leitura = True` para ficar acessível. Ficam de fora, mesmo sendo GET: exportações (`AUD-07`), geração de URL assinada de documento e foto (`AUD-05`) e dados pessoais completos de cliente (`AUD-04`). Sem a marca → 403 `{ "codigo": "PLT-07" }`.
- O token de suporte é recusado nas rotas de autenticação e em qualquer rota da plataforma.

### 3. Duas etapas com JWT

- `Usuario.exige_2fa` deixa de ser campo e passa a ser propriedade derivada: verdadeiro para todo usuário do `public` (`PLT-08`), para os perfis `administrador` e `financeiro` (`USR-02`), quando `ConfiguracaoEmpresa.exige_2fa_todos` está ligado, e para quem ativou um dispositivo por conta própria.
- Login em duas chamadas: `entrar` (e-mail e senha) devolve tokens só para quem não precisa de 2 etapas. Para os demais, devolve um token `token_type = "pre_2fa"` (5 min, sem refresh, com `schema` e `empresa_id`) que só é aceito em `auth/2fa/verificar/` e, para quem ainda não tem dispositivo, em `auth/2fa/configurar/`. A tela de login da plataforma, que pede e-mail, senha e código num formulário só, envia os três de uma vez e o backend faz as duas etapas na mesma chamada.
- Tokens finais levam a claim `amr`: `["pwd"]` ou `["pwd", "otp"]`. A autenticação recusa com 401 `{ "codigo": "2fa_obrigatorio" }` token sem `"otp"` de usuário que `exige_2fa`. Ligar `exige_2fa_todos` ou promover alguém a administrador ou financeiro derruba, no próximo uso, os tokens sem `otp`.
- O `OTPMiddleware` não é usado na API.

### 4. Django Admin só no `public`, com 2 etapas e pelos serviços

- O Admin é montado só em `PUBLIC_SCHEMA_URLCONF`, no host `admin.<dominio>`, com `django_otp.admin.OTPAdminSite`. Não existe Admin no urlconf da empresa. `django.contrib.admin` sai de `TENANT_APPS` (corrige a tabela da 0011).
- Model de negócio no Admin é só leitura; criar ou mudar algo é por ação ou formulário do Admin que chama o serviço de domínio (ex.: "Criar empresa" chama `plataforma.services.criar_empresa`), o que mantém validação e auditoria.

### 5. Refresh em cookie host-only e API na mesma origem

- O frontend (Next.js) e a API ficam **na mesma origem**: o proxy de cada host manda `/api/` para o Django. Sem CORS: nenhuma origem liberada, nenhum `CORS_ALLOW_CREDENTIALS`.
- No navegador o refresh vai em cookie `__Host-giro_refresh`: `HttpOnly`, `Secure`, `SameSite=Strict`, **sem** `Domain` (host-only), `Path=/` (o prefixo `__Host-` exige `Path=/`; o host-only é o que impede o subdomínio vizinho de ler). `renovar` e `sair` leem o refresh do cookie e exigem o cabeçalho `X-Requested-With: giro`, que formulário de outro site não consegue mandar.
- O access token vai no corpo da resposta e fica só em memória no frontend.

## Consequências

- O contrato de autenticação da plataforma (`docs/api/plataforma.md`) e o futuro `docs/api/contas.md` seguem este fluxo.
- Testes obrigatórios, além dos da 0008: refresh da empresa A recusado no host da B **sem** gravar nada no schema B; token sem `empresa_id` recusado; token de suporte não carrega usuário da empresa e é recusado após `fim`, após bloqueio e em rota sem a marca de "só ver"; token sem `otp` recusado para administrador; Admin inexistente no host da empresa.
- O devops configura o proxy da mesma origem (`/api/` → Django) no Compose e nos ambientes.
