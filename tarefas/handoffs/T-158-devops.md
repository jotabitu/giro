# T-158 · (M-04) Proxy reverso: tamanho do corpo e cabeçalhos X-Forwarded-* · devops → orquestrador

**O que foi feito:**
- `infra/proxy/giro.conf.template` (nginx): corpo até 12 MB (webhook 1 MB), `X-Forwarded-Host/Proto/For` sempre sobrescritos (`$host`, `$scheme`, `$remote_addr`) e `Forwarded` apagado, rate limit de borda em `/api/auth/` (10/min por IP) e `/api/webhooks/` (120/min), 429; host desconhecido recusado (444), HTTP redireciona para HTTPS, `/api/` direto ao Django. `nginx -t` passa (imagem 1.27, certificado de teste).
- `infra/README.md`: seção "Proxy reverso" com o checklist para homologação e produção.
- Backend (combinado no escopo da tarefa, só settings): `USE_X_FORWARDED_HOST` passa a `False` em `base.py` (vale para testes) e é ligado em `dev.py` (o rewrite do Next precisa) e `prod.py`. `GIRO_REDES_PROXY` e `GIRO_PROXIES_CONFIAVEIS` não mudaram. Teste `test_t158_x_forwarded_host_so_em_dev_e_prod`.

**Decisão a confirmar:** a tarefa diz "só em `prod.py`", mas o dev depende do cabeçalho, então `dev.py` também liga. O produto do proxy (nginx) é suposição: o deploy ainda espera a ADR; se for outro, vale o checklist.

**Verificação:** ruff check, ruff format --check e `mypy .` limpos; `tests/test_producao.py` e `comum` passam (179). Suíte completa do backend: 912 passaram, 6 ignorados, 6 xfail. Não testei o proxy com tráfego real.

**Não mexi:** `.env` e `.env.example`, compose, CI.

**Quem recebe:** orquestrador abre o PR; avisar o backend que `base.py`, `dev.py` e `prod.py` mudaram. Seguro: revisar o checklist antes da homologação.
