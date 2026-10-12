# T-145 · CI: só o `openapi.yaml` liga backend e frontend · devops → orquestrador

**O que foi feito:** no job `areas` de `.github/workflows/ci.yml`, o padrão `docs/api/*` (que ligava backend e frontend) virou `docs/api/openapi.yaml`. Os textos do contrato (`docs/api/*.md`) deixam de ligar qualquer coisa: o PR roda só o job `areas`, uns 10 segundos, em vez dos 11 minutos da suíte.

**Por que é seguro:** o que o CI confere do contrato é o OpenAPI gerado contra `docs/api/openapi.yaml` (passo do job `backend`) e o cliente tipado do frontend, e os dois dependem só desse arquivo. Mudou o `openapi.yaml`, roda tudo como antes. Mudou código do backend ou do frontend, roda a área respectiva como antes.

**Onde:** `.github/workflows/ci.yml` (uma linha), `tarefas/feito.md`.

**Conferência:** este PR mexe em `.github/workflows/*`, que liga backend, frontend e infra, então roda tudo uma vez. Esse é o teste de que o workflow continua válido. Para ver a regra nova funcionando, o próximo PR só de `docs/api/*.md` deve mostrar `backend=false frontend=false infra=false` no log do job `areas`. Não rodei o Actions daqui.

**Sugestão (não implementada): reduzir os 11 minutos da suíte do backend**
Os testes do seed (`tests/aceitacao/test_t127_seed.py`, T-127 e T-138) usam a fixture `semeado`, de escopo de função: cada teste roda `seed_moto_rapida` inteiro (empresa, 86 veículos, 42 locações pelos serviços) dentro da transação. São ~16 testes, então o seed roda ~16 vezes.
1. **Semear uma vez por sessão ou por módulo.** Uma fixture `scope="module"` (ou `session`) que roda o seed e confirma fora de transação, mais limpeza do schema da empresa no fim. Os testes só leem, então compartilham o resultado. Cuidado: o seed precisa ser idempotente (é, `test_seed_127_02`) e os testes que mexem em dados (`test_seed_127_02` roda duas vezes) ficam num grupo à parte. Ganho esperado: tirar ~15 execuções do seed, que é o maior item individual.
2. **`pytest-xdist` (`-n auto`).** O runner `ubuntu-latest` tem 4 vCPUs, então a suíte cairia para perto de um terço. Precisa de um banco por worker (`pytest-django` já cria `test_giro_gw0`, etc.) e o `django_db_setup` do `conftest.py` já é por sessão; os schemas `empresa_a` e `empresa_b` seriam criados em cada worker. O `--reuse-db` do `addopts` deve ficar fora do CI (banco novo toda vez). Testes que dependem de ordem ou de dados globais aparecem na primeira rodada.
3. **Medir antes:** `pytest --durations=25 -q` no CI mostra quais testes pesam de fato; vale rodar uma vez antes de escolher entre 1 e 2 (as duas se somam).
4. **Menor:** separar o `mypy .` e o `ruff` em job próprio, em paralelo com os testes, tira o tempo deles do caminho crítico.

**Próximo passo:** orquestrador abre o PR. Se o dono quiser a redução da suíte, vira tarefa nova no quadro (backend ou qa para a fixture, devops para o xdist).
