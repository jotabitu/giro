# Tarefas Celery por empresa

**Status:** aceita · 07 out 2026 · detalha a 0002

## Contexto

As automações (`AUT-01` a `AUT-15`) rodam por empresa no fuso `America/Sao_Paulo`. O worker do Celery não tem requisição, então não sabe em qual schema entrar. Existem bibliotecas para isso (`tenant-schemas-celery`), mas elas trariam dependência de infraestrutura nova.

## Decisão

1. Sem biblioteca nova. `comum.tarefas` oferece:
   - `na_empresa(schema_name)`: context manager sobre `django_tenants.utils.schema_context` que também define o ator `sistema` da auditoria.
   - `@tarefa_de_empresa`: decorador para tasks Celery cujo **primeiro argumento é sempre `schema_name`**; entra no schema, roda e sai. Task de empresa sem `schema_name` é erro de programação.
   - `para_cada_empresa(task, *args)`: lê no `public` as empresas que operam (status `em_teste`, `ativa`, `inadimplente`; `suspensa` só para tarefas de leitura/cobrança) e enfileira uma task por empresa.
2. Celery Beat tem uma entrada por automação no fuso `America/Sao_Paulo` (`CELERY_TIMEZONE`), que chama `para_cada_empresa`. As tarefas da plataforma (`AUT-13`, `AUT-15`) rodam no `public`.
3. Nome da task com o código da regra: `aut_02_marcar_devolucao_atrasada`. Toda task é idempotente: pode rodar duas vezes sem efeito duplicado (chave natural ou registro de execução por dia).
4. Quem chama uma task a partir de um serviço passa `connection.schema_name` e usa `transaction.on_commit`.

## Consequências

- Uma empresa com erro numa tarefa não para as outras.
- Testes de task rodam com `CELERY_TASK_ALWAYS_EAGER` e dentro de uma empresa de teste.
- Se o número de empresas crescer a ponto de a fila de fan-out pesar, avaliamos a biblioteca numa nova ADR.
