# T-083 · Transferência pede a categoria do destino · backend → orquestrador, frontend, qa, arquiteto

**O que foi feito (`VEI-04`, `FIL-04`, `LOC-01`, opção B da T-082):**
- `POST /api/veiculos/{id}/transferir/` ganhou `categoria_id?`.
  - Quando a categoria atual é só da filial de origem, ele é obrigatório. Sem ele, responde 400 `validacao` em `categoria_id`, e o veículo não sai da filial.
  - Ele precisa ser uma categoria ativa, do mesmo tipo de veículo, da empresa ou da filial de destino. Fora disso, também responde 400 em `categoria_id`.
  - Quando a categoria atual é da empresa, ele pode faltar, e o veículo continua nela.
- A `TransferenciaVeiculo` ganhou `categoria_origem` e `categoria_destino`. Nas transferências antigas, os dois ficam nulos. A auditoria `veiculo.transferir` guarda o `categoria_id` de antes e o de depois.
- O veículo só é transferido `disponivel`, então nenhuma locação aberta muda de preço. A categoria nova vale a partir da próxima locação.

**Onde:**
- `backend/apps/veiculos/`: `services.py` (`transferir` e `_categoria_no_destino`), `models.py`, a migração `0003`, `api/serializers.py`, `api/views.py` e o `README.md`.
- `docs/api/veiculos.md` (seção `transferir`) e `docs/api/openapi.yaml`.
- Testes: `test_vei_04_fil_04_ca_013_27_categoria_so_da_filial_na_transferencia`. O `test_vei_04_ca_013_13` agora também confere que a Street 150–160 continua com diária 5490.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `400 passed, 17 xfailed`. Antes eram 399 e 17.
- O OpenAPI foi regerado com `--validate`, sem aviso.
- Rodei no Postgres descartável, com `--rm` e `POSTGRES_HOST`.

**Diferença para o arquiteto conferir:** com a categoria atual da empresa, um `categoria_id` válido também é aceito, e o veículo vai para ela. A regra só diz que, sem `categoria_id`, o veículo continua na mesma categoria.

**Próximo passo para quem recebe:**
- **Frontend:** no diálogo de transferir, peça a categoria quando a categoria atual tiver `filial` preenchida. Ofereça as categorias ativas do mesmo tipo, da empresa ou do destino (`GET /api/categorias/?filial=<destino>&tipo_veiculo=...`).
- **QA:** o CA-013-27 está coberto.
