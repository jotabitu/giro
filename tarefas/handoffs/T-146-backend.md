# T-146 · Status do caixa como enum no painel · backend → orquestrador, frontend

**O que foi feito:** branch `t-146-status-caixa-enum`, a partir da `origin/main`.

- `relatorios/api/serializers.py`: `status` de `CaixaHojeSerializer` (`caixa_hoje`) e de `CaixaDoDiaSerializer` (`caixas_do_dia`) passou de `CharField` a `ChoiceField` com os valores de `financeiro.models.StatusCaixa` (`aberto`, `aguardando_aprovacao`, `fechado`, `fechado_sem_conferencia`). A lista é a mesma do caixa em `financeiro`, então o OpenAPI reaproveita o `StatusCaixaEnum` que já existia (`ENUM_NAME_OVERRIDES`), sem enum novo.
- `docs/api/openapi.yaml` regenerado: só os dois `status` mudam (`$ref: StatusCaixaEnum`). `docs/api/painel.md` já dizia os quatro status (T-144); sem mudança no contrato.
- A forma da resposta e os valores não mudam; o selector já devolvia o caixa de hoje em qualquer status.

**Regras cobertas:** FIN-07, FIN-08.

**Testes:** `tests/aceitacao/test_t017_financeiro.py::test_fin_07_caixa_hoje_em_qualquer_status`: a Bruna fecha o caixa da Filial Centro com o esperado na gaveta, e o painel da Mariana traz `caixa_hoje` com `status` `fechado`; o da Lúcia, `caixas_do_dia` com `fechado`; o campo tem os quatro valores. ruff, ruff format, mypy e pytest verdes.

**Para o frontend:** rode `api:gerar`; `caixa_hoje.status` e `caixas_do_dia[].status` passam a ser `StatusCaixaEnum` no cliente tipado (antes `string`). Nada mais muda.

**Próximo passo:** orquestrador abre o PR. Sigo para a T-150.
