# T-245 · Despesa ligada ao veículo sem a filial na lista · backend → frontend, qa

**O que foi feito:** a representação da despesa (lista e detalhe) manda `filial` com `{id, nome}`, como contas a receber e caixa. O `FilialRefSerializer` (só `id`) saiu; a despesa usa o `RefSerializer`. `base_das_despesas` passou a trazer a filial no `select_related`, sem consulta a mais por linha.
**Onde:** `backend/apps/financeiro/selectors.py` (`representacao_despesa`, `base_das_despesas`), `backend/apps/financeiro/api/serializers.py` (`DespesaSerializer`).
**Contrato:** `GET /api/financeiro/despesas/` e `GET /api/financeiro/despesas/{id}/`; `docs/api/financeiro.md`, "Despesas" > "Representação"; `docs/api/openapi.yaml` regenerado (schema `FilialRef` removido, `Despesa.filial` aponta para `Ref`).
**Regras cobertas:** FIN-06, FIL-05 (teste: `test_fin_06_fil_05_filial_da_despesa_ligada_a_veiculo`, em `tests/aceitacao/test_t178_despesas.py`, com os pneus do PMZ3E17 na Filial Centro, na lista filtrada pelo veículo e no detalhe).
**Testes rodados:** `test_t178_despesas.py` e `test_t017_financeiro.py` (45 passed), ruff e mypy do app `financeiro`.
**O que ficou de fora:** a tela (parte do frontend da T-245).
**Próximo passo para quem recebe:** frontend: regenerar `frontend/src/lib/api/schema.d.ts` (ele ainda cita `FilialRef`) e mostrar `despesa.filial.nome` na lista e no detalhe, sem deduzir a filial pelo veículo.
