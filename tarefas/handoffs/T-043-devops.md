# T-043 · Papéis de banco (ADR 0016, S-10) · devops → arquiteto, backend, seguranca

**O que foi feito:** `infra/postgres/01-papeis.sh` (cria `giro_migracao`, `giro_app`, `giro_expurgo`, ajusta o schema `public`), montado em `docker-entrypoint-initdb.d` no Compose; `DATABASE_URL_MIGRACAO` e as senhas dos papéis em `.env.example`; seção "Papéis de banco" em `infra/README.md`.
**Verificado:** num Postgres 16 limpo, o script roda sem erro; `giro_app` não cria tabela nem schema e lê/escreve em tabela criada por `giro_migracao`; `giro_expurgo` sem login. `check-env.sh` passa.
**Não feito (depende do backend):** em dev e no CI as duas URLs ainda apontam para um papel só, porque o backend não lê `DATABASE_URL_MIGRACAO` nem aplica os `GRANT` por schema. Ligar os papéis separados agora quebraria migrações e testes. Contrato do que o backend faz está em `infra/README.md`.
**Ambientes:** homologação e produção ainda não existem; a seção diz como aplicar o mesmo SQL e onde ficam as credenciais.
**Próximo passo:** backend implementa o item da ADR e me avisa; eu troco o `.env.example`, o entrypoint e o CI para os papéis separados e adiciono o teste com `giro_app` no CI.
