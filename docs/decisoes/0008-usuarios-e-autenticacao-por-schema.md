# Usuários e autenticação por schema

**Status:** aceita · 07 out 2026

## Contexto

Existem dois tipos de usuário: a equipe da plataforma (dono, suporte, financeiro, sucesso) e os usuários de cada locadora (administrador, gerente, vendedor, vistoriador, financeiro). As regras pedem que eles sejam separados (entidade "Usuário da plataforma") e a ADR 0002 põe dado da empresa no schema dela. O Django só aceita um `AUTH_USER_MODEL`, e o Admin, o django-otp e o simplejwt dependem dele. Com um schema por empresa, o mesmo `id` de usuário existe em várias empresas.

## Decisão

1. `AUTH_USER_MODEL = "contas.Usuario"`. O app `contas` é instalado em `SHARED_APPS` **e** em `TENANT_APPS`, então a tabela existe no schema `public` e em cada schema de empresa.
   - No `public`, as linhas são os usuários da plataforma (campo `funcao_plataforma` preenchido, `perfil` vazio).
   - No schema da empresa, as linhas são os usuários da locadora (`perfil` preenchido, `funcao_plataforma` vazio).
   - O serviço de criação valida qual dos dois campos pode ser preenchido conforme o schema atual. Uma `CheckConstraint` garante que só um dos dois está preenchido.
2. O app `contas` só tem models sem chave estrangeira para apps exclusivos da empresa: `Usuario` e `Convite`. A ligação do usuário com as filiais (`UsuarioFilial`) fica no app `filiais`. Permissões extras (`USR-03`) são uma lista de valores fechados no próprio `Usuario`.
3. Convite cria o `Usuario` com status `convite_pendente` na hora (assim ele conta no limite do plano, `USR-01`), e o `Convite` guarda só o hash do token, a validade de 7 dias e o canal. O mesmo mecanismo serve aos convites da equipe da plataforma.
4. Login por subdomínio: `admin.<dominio>` autentica contra o `public`; `<subdominio>.<dominio>` autentica contra o schema da empresa. Não há usuário que entre em duas empresas com a mesma conta; a mesma pessoa em duas locadoras tem duas contas.
5. JWT (simplejwt) com a claim `schema` (nome do schema em que o token foi emitido). A classe de autenticação do DRF (`comum.autenticacao.JWTDaEmpresa`) recusa com 401 qualquer token cuja `schema` difira de `connection.schema_name`. Isso impede que um token da empresa A, com `user_id=7`, seja aceito na empresa B. Access token de 5 minutos; refresh de 12 h no desktop e 30 dias no celular (`USR-06`), com rotação e blacklist (`rest_framework_simplejwt.token_blacklist`, instalado nos dois schemas).
6. A autenticação carrega o usuário em toda requisição e recusa quem não está `ativo`; desativar (`USR-04`) também põe na blacklist todos os refresh tokens dele. Assim a sessão cai na hora.
7. `django.contrib.auth`, `contenttypes`, `admin`, `sessions`, `django_otp` e seus plugins ficam nos dois schemas. Senhas com Argon2 (`PASSWORD_HASHERS`).
8. "Entrar como suporte" (`PLT-07`) **não** cria usuário na empresa: o usuário da plataforma recebe um token emitido para o schema da empresa com as claims `suporte=true`, `acesso_suporte_id` e `permissao` (`ver` ou `ver_editar`), com expiração igual ao fim do acesso. A autenticação monta um ator "Suporte Giro" e bloqueia escrita quando a permissão é `ver`.

## Consequências

- Isolamento de usuários garantido pelo schema, sem tabela global de pessoas.
- O Django Admin funciona no `public` (empresa piloto do MVP) e, se precisar, em cada empresa.
- Testes obrigatórios em `backend/tests/`: token da empresa A recusado na B; token de usuário desativado recusado; token de suporte "só ver" recusado em escrita.
- A entidade "Usuário da plataforma" das regras é o `contas.Usuario` no schema `public`; o app `plataforma` não tem model de usuário próprio.
