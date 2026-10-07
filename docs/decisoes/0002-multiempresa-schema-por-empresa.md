# Multiempresa com um schema por empresa (django-tenants)

**Status:** aceita · 07 out 2026

## Contexto

SaaS white label; vazamento de dado entre locadoras é o pior erro possível.

## Decisão

`django-tenants` com schema `public` para a plataforma (planos, empresas, faturas, usuários da plataforma, acessos de suporte) e um schema por empresa para todo o resto. Empresa identificada pelo subdomínio.

## Consequências

Isolamento forte, backup e exclusão por empresa simples. Migrações rodam em todos os schemas (`migrate_schemas`); tarefas Celery precisam entrar no schema da empresa explicitamente.
