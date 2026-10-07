# T-039 · Revisão de segurança do código da T-001 · seguranca → orquestrador, backend

**O que foi feito:** revisei o código da branch `t-001` contra as ADRs 0008 a 0013 e o relatório da T-032: autenticação, middleware do ator, auditoria e trigger, tarefas Celery, permissões, erros, usuário, settings e rotas. A ADR 0014 (T-033) ficou fora, como pedido. Confirmei executando código a máscara que esconde a troca de CPF e o `search_path` do django-tenants 3.14.

**Onde:** `docs/seguranca/2026-10-07-codigo-t001.md`.

**Resultado:** nenhum achado alto. S-01, S-04, S-08 (CORS) e S-16 da T-032 estão implementados e com teste. Foram 5 achados médios e 4 baixos:
- C-01 (média): o diff da auditoria é feito depois da máscara, então uma troca de CPF com a mesma máscara não gera registro. Avisei o Backend para corrigir na T-033.
- C-02 (média): tarefa de empresa com schema apagado cai nas tabelas do `public`. Avisei o Backend.
- C-03 (média): o IP da auditoria vem de `REMOTE_ADDR` e, atrás do proxy, será sempre o do proxy.
- C-04 (média): `wsgi`, `asgi` e `celery` usam a configuração `dev` (`DEBUG=True`) quando falta a variável.
- C-05 (média): o trigger não cobre `TRUNCATE` (S-10 continua aberto).
- C-06 a C-09 (baixas): ator anônimo gravado como "Sistema", chave do JWT igual à `SECRET_KEY`, Swagger aberto, `ALLOWED_HOSTS` com padrão de desenvolvimento, superusuário no schema da empresa.

**O que ficou de fora:** ADR 0014 e T-033; teste de integração com o ambiente Docker de pé.

**Próximo passo para quem recebe:**
- Orquestrador: numerar as tarefas propostas no fim do relatório. C-01 entra na T-033; C-02 e C-05 são pequenas e podem ir junto.
- Backend: C-01 na T-033; C-02, C-04 e C-05 quando couber.
- Seguranca: revisar a T-033 e a T-011 quando forem entregues.
