# T-057 · Revisão de segurança do código da T-010 · seguranca → orquestrador, backend, produto, devops, arquiteto

**O que foi feito:** revisei o código da T-010 na `main` (`35c2bcd`) contra as ADRs 0013 e 0014, `PLT-08`, `PLT-09`, `USR-01` e os achados abertos. O escopo foi o login da equipe da plataforma (`entrar`, 2 etapas, códigos de recuperação, bloqueio, atraso do django-otp desligado), `renovar` e `sair`, o convite, `criar_empresa`, o Django Admin e a separação entre o public e as empresas. Conferi o comportamento no código do django-tenants 3.14.0, do django-otp 1.7.3 e do simplejwt 5.5.1. Confirmei o P-04 executando um teste temporário num Postgres descartável; o teste não foi commitado e o container já foi removido.

**Onde:** `docs/seguranca/2026-10-08-codigo-t010.md`.

**Resultado:** 2 achados altos, 2 médios e 5 baixos. O que as ADRs pedem para este trecho está implementado e testado: as claims de empresa conferidas antes da blacklist, o `amr` e o `pre_2fa`, o cookie `__Host-` com `X-Requested-With`, o Admin só no public e pelos serviços, o hash do token do convite e o token fora da fila.
- **P-01 (alta):** o login do Django Admin não tem bloqueio. O atraso do django-otp está desligado e o formulário não passa pelo bloqueio do `PLT-08`, então quem tem a senha do dono pode tentar códigos sem parar. O login do Admin também não é auditado.
- **P-02 (alta):** o bloqueio de 3 códigos dá para contornar com requisições em paralelo, porque a contagem vem depois da verificação e não trava o usuário.
- **P-03 (média):** a senha da equipe pode ser tentada sem limite nenhum, e não há throttle no DRF nem no proxy. A resposta 400 "Informe o código" mostra que a senha está certa.
- **P-04 (média, confirmado executando):** o subdomínio `information-schema` vira o schema `information_schema`, que já existe. O django-tenants não cria nada, e o administrador da locadora cai em `public.contas_usuario`.
- **P-05 a P-09 (baixas):** o primeiro autenticador pode ser cadastrado sem prazo; convites anteriores continuam valendo; dois `renovar` simultâneos geram duas sessões; a semente TOTP e os códigos de recuperação ficam em claro; o token do convite vai no caminho da URL.

**O que ficou de fora:** sessões (`sid`), token de suporte, login e convite da locadora e o 2FA dos perfis da empresa (T-011). Os textos dos e-mails, que são do produto.

**Próximo passo para quem recebe:**
- **Orquestrador:** criar uma tarefa de backend com P-01, P-02, P-03 (throttle e resposta igual) e P-04, no topo do backlog e antes do primeiro deploy de homologação. P-05 a P-09 vão para a T-011. A tabela "Distribuição sugerida" no fim do relatório tem o detalhe.
- **Produto:** decidir se a equipe da plataforma também fica bloqueada por 15 minutos depois de 5 senhas erradas, como no `USR-06`. Sugiro que sim (P-03).
- **DevOps:** limite de requisições no proxy para `/api/*/auth/` e `/admin/login/` (P-03, S-17).
- **Arquiteto:** contrato do convite com o token no corpo (P-09) e, se o P-08 ficar para depois, registrar isso na ADR 0014.
- O PR #27 já entrou. Nenhum achado pede reverter, mas P-01 e P-02 precisam estar corrigidos antes de qualquer ambiente com dados reais.
