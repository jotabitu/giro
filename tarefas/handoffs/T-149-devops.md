# T-149 · Suíte do backend em paralelo e lint em job próprio (passos 3 e 4) · devops → orquestrador

**O que foi feito:** o job `backend` do CI roda `pytest -q -n auto --dist loadfile --create-db --durations=15` (pytest-xdist) e `ruff` e `mypy` saíram dele para o job novo `backend-lint`, que roda em paralelo.

**Medição (local, mesma máquina e mesmo container, 738 testes, banco novo):**
- Antes, um processo (`pytest --create-db --durations=25`): 669 s de testes, 11 min 9 s. A máquina estava ocupada com outros containers; o QA mediu 4 min 48 s na dele, então compare só a razão.
- Depois, `-n 4 --dist loadfile --create-db`: 181 s de testes, 3 min 1 s (3 min 9 s com o `pip install` do xdist). Todos passaram.
- Os mais lentos antes: `test_t127_seed.py::test_seed_127_01` com 67 s de setup (o seed, uma vez por módulo, como o QA deixou), `test_auditoria.py::test_aud_01` com 48 s de setup (primeiro schema da sessão), `test_t010_plataforma.py` (cinco testes de 10 a 24 s, cada um cria empresa e schema de verdade), `test_t011_seguranca.py::test_usr_02` com 11 s; o resto abaixo de 7 s. Em paralelo o custo fixo (criar `empresa_a` e `empresa_b` em cada worker, 30 a 48 s de setup no primeiro teste de cada um) passa a pesar mais; ele não encolhe com mais workers.
- O CI tem 4 vCPUs (`-n auto` dá 4 workers), o mesmo `-n 4` do teste. Não rodei o Actions daqui: o tempo real do job aparece no PR.

**Por que a dependência (`pytest-xdist>=3.6,<4`, em `requirements-dev.txt`, só desenvolvimento):** é a única forma de usar os 4 vCPUs do runner sem reescrever os testes; sem ele a suíte fica em um processo (4 a 7 min no CI mesmo com o seed uma vez por módulo). Cada worker usa o banco `test_giro_gwN` do pytest-django, então não há colisão. `--dist loadfile` mantém cada arquivo num worker só, que é o que a fixture de módulo do seed (T-149 passo 2) exige; com `--dist load` o seed de 30 s rodaria em mais de um worker. `--create-db` anula o `--reuse-db` do `addopts` no CI (banco novo toda vez). Localmente nada muda: `make backend-check` segue em um processo, por causa da memória.

**Onde:** `.github/workflows/ci.yml` (job `backend-lint` novo; job `backend` sem lint e com xdist), `backend/requirements-dev.txt`, `backend/README.md` (uma frase), `tarefas/`.

**Cuidados:**
- O job `backend` mudou de nome: "Backend (lint, tipos, testes, OpenAPI)" virou "Backend (testes, OpenAPI)", e há o job novo "Backend (lint e tipos)". Se a `main` tiver proteção de ramo com checks obrigatórios por nome, atualizar a lista (não consegui ver essa configuração daqui).
- O `backend-lint` não instala Postgres, Redis nem as bibliotecas do WeasyPrint: ruff e mypy não abrem o banco, e o WeasyPrint só é importado dentro de funções. Se um dia o mypy passar a importar o WeasyPrint no topo de um módulo, volta o `apt-get` ali.
- Não rodei `ruff` e `mypy` no formato novo do job; os comandos são os mesmos de antes, só em outro job.
- Se um teste novo depender de ordem ou de dado global entre arquivos, ele aparece no CI e não local; hoje os 738 passam em 4 workers.

**Regras cobertas:** nenhuma (infraestrutura).

**Próximo passo para quem recebe:** abrir o PR e olhar a duração do job `backend` no Actions; a meta é perto de 5 min. Se passar, a sobra é a criação de empresas e schemas (`test_t010_plataforma.py` e o setup por worker), e o ganho seguinte é do backend/QA, não de infra.
