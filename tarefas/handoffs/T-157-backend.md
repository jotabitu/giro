# T-157 · (M-03) Produção recusa e-mail no console e armazenamento falso · backend → devops, seguranca

**O que foi feito:** `config/settings/prod.py` não sobe (`ImproperlyConfigured`) com:
- `EMAIL_BACKEND` de console, locmem, arquivo (`filebased`) ou `dummy`, inclusive quando a variável falta (o padrão de `base.py` é o console). O `dummy` entrou além dos três da tarefa: não vaza o token, mas descarta os e-mails de senha, convite e assinatura sem avisar;
- SMTP sem `EMAIL_HOST`;
- `GIRO_ARMAZENAMENTO` diferente de `s3` (ausente, vazio ou `falso`);
- `GIRO_PROVEDOR_PAGAMENTOS` diferente de `asaas`, já que a integração real existe (T-029), e `GIRO_ASAAS_CHAVE_API` vazia ou ausente.

**Onde:** `backend/config/settings/prod.py`, `backend/tests/test_producao.py` (o ambiente de produção dos testes ganhou SMTP, S3 e Asaas), `infra/deploy/producao.env.example` e `homologacao.env.example` (variáveis novas obrigatórias; `GIRO_ASAAS_URL` de produção em `https://api.asaas.com/v3`, homologação no sandbox).
**Contrato:** sem mudança de API nem de OpenAPI.
**Testes:** `test_t157_*` (cada backend de desenvolvimento, variável ausente, SMTP sem servidor, armazenamento e pagamentos falsos ou vazios, Asaas sem chave, e o caso que sobe). `ruff`, `ruff format --check` e `mypy` limpos; `tests/test_producao.py` e `tests/test_data_de_referencia.py` passam (56).
**O que ficou de fora:**
- WhatsApp: só existe o `falso`; entra na trava quando houver integração real (comentário no `prod.py`).
- `GIRO_PROVEDOR_CEP=falso` em produção não é recusado (fora da tarefa; devolveria só os CEPs do seed). Se a segurança ou o devops quiserem, é uma linha a mais.
- `S3_BUCKET` e as chaves do S3 não são conferidos ao subir (a falha aparece no primeiro upload).
**Próximo passo para quem recebe:** devops: preencher no cofre de homologação e produção `EMAIL_*`, `S3_*` e `GIRO_ASAAS_*` antes do primeiro deploy, senão o backend não sobe.
