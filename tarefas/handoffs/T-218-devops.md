# T-218 · Fotos do desenvolvimento que sobrevivem ao reinício do backend (D-07 da T-212) · devops → orquestrador

**Causa:** o armazenamento "falso" (`comum/arquivos.py::guardados`) é um dicionário na memória. Com o backend recriado, as fotos somem e `/api/arquivos-dev/` responde 404. Worker e beat também não enxergavam o que o backend guardava.

**O que foi feito:**
- `config/settings/dev.py`: nova `GIRO_ARQUIVOS_FALSOS_DIRETORIO`, lida da variável de ambiente de mesmo nome. Vazia ou ausente = memória, como antes. `base.py` (testes, homologação e produção) não mudou.
- `comum/arquivos.py`: `ProvedorFalso` grava em disco quando a pasta está definida (arquivo mais um `.tipo` ao lado com o tipo de conteúdo) e continua na memória quando não está. Novo `ler_falso()`, usado pela rota; caminho que sai da pasta é recusado.
- `comum/arquivos_dev.py`: lê por `ler_falso()` em vez do dicionário.
- `docker-compose.yml`: volume nomeado `arquivosdev` em `/arquivos-dev`, compartilhado por backend, worker e beat, com a variável definida nos três.
- `tests/test_arquivos_dev.py`: 2 testes novos [AUD-05] (a foto em disco abre depois de a memória ser esvaziada e some ao apagar; caminho fora da pasta é recusado).

**Não mexi:** testes existentes, `.env` e `.env.example`, homologação e produção (S3).

**Verificação:** ruff check, ruff format --check e mypy do backend inteiro limpos; `tests/test_arquivos_dev.py` com 6 passando. Suíte completa do backend: 911 passaram, 6 ignorados, 6 xfail. Não subi o compose para reiniciar o backend e ver a foto na tela.

**Para quem já tem o ambiente:** `docker compose up -d` cria o volume. Fotos enviadas antes disso estavam só na memória e precisam ser reenviadas (ou refazer o `make seed`). `docker compose down -v` apaga o volume junto com o banco.

**Quem recebe:** orquestrador abre o PR; avisar o backend que `comum/arquivos.py` e `config/settings/dev.py` mudaram. O QA (T-212) pode tirar o contorno do D-07.
