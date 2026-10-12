# T-133 · Login do compose com a chave do JWT vazia · devops → orquestrador, qa

**O que foi feito:** o login do compose respondia 500 `InvalidKeyError: HMAC key must not be empty` porque o `.env` entrega `JWT_SIGNING_KEY=` como string vazia, e `env("JWT_SIGNING_KEY", default=SECRET_KEY)` só usa o padrão quando a variável não existe.
- `config/settings/base.py`: `env_preenchida(nome, padrao)` (ausente, vazia ou só espaços cai no padrão). Vale para `JWT_SIGNING_KEY` (padrão `DJANGO_SECRET_KEY`) e para `GIRO_CHAVE_DADOS_PESSOAIS`, `GIRO_CHAVE_SEGREDOS` e `GIRO_PEPPER_HMAC` (padrão: os valores de exemplo do `.env.example`, agora constantes em `base.py`). `SIMPLE_JWT` ganhou a anotação `dict[str, Any]` (sem ela o mypy tipava os valores como `object`).
- `config/settings/prod.py`: as quatro variáveis vazias ou ausentes recusam subir ("Defina NOME"), antes das conferências que já existiam (igual a `DJANGO_SECRET_KEY`, valor de exemplo, 32 bytes, pepper curto). Em produção nada mudou para quem já preenchia tudo.
- `.env.example`, `infra/README.md` (tabela por ambiente) e `docs/agentes/retomada.md` dizem o que preencher: em dev, nada.

**Onde:** `backend/config/settings/base.py`, `backend/config/settings/prod.py`, `backend/tests/test_producao.py`, `.env.example`, `infra/README.md`, `docs/agentes/retomada.md`.

**Check:** ruff check, ruff format e mypy limpos em todo o `backend`. `tests/test_producao.py`: 29 passed (novos: `test_t133_prod_recusa_chave_vazia_ou_ausente` nas 4 variáveis × `""`, espaços e ausente; `test_t133_dev_com_variaveis_vazias_cai_nos_padroes`; `test_t133_dev_com_chave_dos_tokens_preenchida_usa_a_chave`).
**Conferência no compose:** contêiner avulso (`giro-backend:latest`, meu código montado, rede `giro_default`, o ambiente do `giro-backend-1`, em que `JWT_SIGNING_KEY` tem tamanho 0), porta 8133 com o cabeçalho `Host: motorapida.localhost:3000`: `POST /api/auth/entrar/` com `rodrigo@` e `bruna@motorapida.com.br` respondeu 200 (`etapa: pronto`). Não li o `.env`.

**Atenção:** o banco do compose estava sem a migração `empresas.0004` (marca, T-129); o login dava 500 `nome_exibicao does not exist` até eu rodar `migrate_schemas` nele, o que fiz (só essa migração aplicou). Quem sobe o compose depois de um merge com migração precisa rodar `migrate_schemas` (o `backend` do compose em execução continua com o código antigo até reiniciar).

**Próximo passo:** orquestrador abre o PR e reinicia o `backend` do compose depois do merge; qa refaz a conferência das telas com cada perfil (bloqueio da T-127).
