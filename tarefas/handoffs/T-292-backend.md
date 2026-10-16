# T-292 · Sessão do Admin em produção · backend → devops, seguranca, orquestrador

**O que foi feito:** a parte do backend da ADR 0029 (item 4 e Consequências).
- `prod.py`: `SESSION_COOKIE_AGE = 4 horas` e `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`, junto do `SESSION_COOKIE_SECURE` e do `CSRF_COOKIE_SECURE` que já existiam. Sem `SESSION_COOKIE_DOMAIN`: o cookie fica no host da plataforma. Só o Django Admin usa a sessão; a API segue com tokens.
- `test_t277_is_staff_so_pelo_createsuperuser`: fora de testes e migrações, só `apps/contas/models.py` (o campo e o `create_superuser`) e `apps/contas/login_admin.py` (que só lê) citam `is_staff`; o campo nasce `False`; o OpenAPI gerado na hora não tem `is_staff` (nenhuma rota lê nem grava). Um serviço ou serializer novo que cite `is_staff` derruba o teste.

**Onde:** `backend/config/settings/prod.py`, `backend/tests/test_producao.py` (`test_t277_prod_sessao_do_admin_de_4_horas_que_fecha_com_o_navegador`), `backend/tests/test_admin_da_plataforma.py`.
**Contrato:** sem mudança na API nem no OpenAPI.
**Regras cobertas:** PLT-08 (Admin), ADR 0029.
**Testes:** ruff, ruff format, mypy e os testes afetados (`test_producao.py`, `test_admin_da_plataforma.py` e os de PLT-08 da `test_t058_seguranca.py`): 19 passaram. Suíte toda não rodada (pouca memória).
**Branch:** `t-292-sessao-admin`, empilhada sobre a `t-277-admin-pelo-proxy` (PR #290). Abrir o PR depois do merge do #290, ou contra a branch dele.
**O que ficou de fora:** o proxy (lista de IPs, bloco da plataforma, limite no login) é da T-291 (devops).
**Próximo passo para quem recebe:** devops, no teste de subida da T-291, conferir que o cookie `sessionid` do Admin sai com `Secure`, sem `Expires` e só no host da plataforma.
