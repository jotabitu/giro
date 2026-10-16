# T-240 · Ocupação do veículo recém-cadastrado (parte do backend) · backend → frontend, qa

**O que foi feito:** `GET /api/veiculos/{id}/` respondia 500 logo depois do `POST /api/veiculos/` (201): com menos de 1 s na frota, `veiculos/selectors._pct` convertia o tempo para 0 segundo inteiro e dividia 0 por 0 (`decimal.InvalidOperation`). Agora confere os segundos inteiros e devolve `"0.00"` quando são 0 (`VEI-06`).
**Onde:** `backend/apps/veiculos/selectors.py` (`_pct`), teste em `backend/tests/aceitacao/test_t013_veiculos.py`.
**Contrato:** sem mudança de API nem de OpenAPI. O veículo recém-cadastrado vem com `ocupacao: { "pct": "0.00", "periodo_dias": 90 }`.
**Regras cobertas:** VEI-06 (`test_vei_06_veiculo_recem_cadastrado_sem_500`: cadastro às 10:00:00, ficha às 10:00:00,5 responde 200 com 0,00%).
**Checagens:** ruff, ruff format --check e mypy limpos; `test_t013_veiculos.py` com 34 passando.
**O que ficou de fora:** a tela (Frontend, branch `t-240-cadastro-veiculo-erro`).
**Próximo passo para quem recebe:** frontend: com este PR, a ficha logo após o cadastro volta 200; o tratamento do erro na tela segue na sua branch.
