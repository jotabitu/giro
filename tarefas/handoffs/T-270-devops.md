# T-270 · Sentry sem o token do webhook e sem variáveis locais · devops → orquestrador, segurança, backend

Branch `t-270-sentry-sem-segredos`, a partir da `origin/main`. Resolve o B-01 da T-189 (PR #258) e o M-03 da T-247 (PR #265).

**O que foi feito:**
- `backend/comum/sentry.py` (novo, só `sentry_sdk`): `opcoes_do_sentry(dsn, ambiente)` e `limpar_evento`. `include_local_variables=False`, `max_request_body_size="never"`, `EventScrubber(recursive=True)` com `asaas-access-token`, `creditcardtoken` e afins somados à lista padrão; `before_send` tira `request.data` e cookies, filtra `asaas-access-token`, `Authorization` e `Cookie` dos cabeçalhos (e tira cabeçalhos e query string em `/api/webhooks/`) e deixa só `task_name` em `extra["celery-job"]` (a integração do Celery anexaria `args` e `kwargs`).
- `backend/config/settings/base.py`: o `sentry_sdk.init` usa essas opções; worker e beat herdam.
- `infra/README.md`: seção "Sentry sem segredos".
- Testes `backend/tests/aceitacao/test_t270_sentry.py` (5, passando), com um transporte de mentira (o SDK monta o evento de verdade, sem rede): erro provocado no webhook com o token e o `creditCardToken` não leva nenhum dos dois, nem o corpo, nem cabeçalhos; variável local com CPF e nome fica fora e o rastro da pilha continua; um controle sem a opção mostra o CPF no evento (prova que o teste vale); `creditCardToken` aninhado sai pelo scrubber; `limpar_evento` direto.

**Verificação:** ruff check, ruff format --check e `mypy .` limpos no backend inteiro. Passaram também `tests/test_producao.py`, `comum`, `test_t029_asaas.py` e `test_t184_faturas.py` (227 passaram, 1 xfail). Conferido com um `SENTRY_DSN_BACKEND` de verdade que as opções chegam ao cliente (`include_local_variables=False`, `max_request_body_size="never"`). Não rodei a suíte completa (mudança só em configuração do Sentry).

**O que ficou de fora:**
- Seção da T-270 no backlog: ela está na branch da T-189 (PR #258), não na `main`; não criei outra para não conflitar.
- Sentry do frontend (não existe) e o filtro da mensagem da exceção: a regra é não pôr dado pessoal nem saída do filho em mensagem (B-02 da T-247), do backend da T-265.
- Não testei contra o Sentry real (sem DSN de sandbox).
- `send_default_pii` avisa depreciação no SDK 2.72 (`data_collection`); não troquei porque o comportamento é o mesmo e é fora do escopo.

**Anotado para a T-274:** com a T-276 (PR #275) mesclada, o teste de subida da T-264 (`infra/scripts/teste-subida-producao.sh`) passa a usar `giro_migracao` e `giro_app` separados em vez do superusuário; em banco gerenciado, o mesmo SQL do `01-papeis.sh`.

**Próximo passo para quem recebe:** orquestrador abre o PR; segurança confere o B-01 e o M-03 como fechados.
