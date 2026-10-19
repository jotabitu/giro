# T-263 · Ação gerar_contrato na locação · backend → frontend, qa

**O que foi feito:** `acoes.gerar_contrato` no detalhe da locação, pelas mesmas condições do `POST /api/locacoes/{id}/contrato/`: perfil que cria (administrador, gerente, vendedor), `aguardando_retirada`, sem pedido de desconto pendente (`APR-01`), sem cancelamento pedido ou aprovado (`LOC-12`) e sem contrato vigente (volta a `true` com o contrato cancelado). Não olha o modelo publicado: sem ele o botão aparece e o `POST` responde 422 `IMP-04`. O `POST` ganhou o 409 `cancelamento_em_curso` ("A locação tem um cancelamento em andamento."), conferido depois de `contrato_fora_de_hora` e `desconto_pendente`.

**Onde:** `backend/apps/locacoes/selectors.py` (`acoes`), `backend/apps/locacoes/contrato.py` (`gerar`), `backend/apps/locacoes/api/serializers.py`; no frontend, só o falso `src/testes/falsos/falso-locacoes.ts` com a ação nova (o typecheck quebrava com o OpenAPI novo).

**Contrato:** `docs/api/locacoes.md` (`acoes.gerar_contrato`) e `docs/api/contratos.md` (409 `cancelamento_em_curso`); `docs/api/openapi.yaml` regenerado, `npm run api:gerar` e `typecheck` limpos.

**Regras cobertas:** IMP-04, APR-01, LOC-12 (testes em `tests/aceitacao/test_t263_gerar_contrato.py`: `test_loc_acoes_gerar_contrato_por_perfil`, `test_loc_acoes_gerar_contrato`, `test_loc_gerar_contrato_com_cancelamento_em_curso`). t015, t090, t091, t123 e `apps/locacoes` seguem passando.

**O que ficou de fora:** o cartão Contrato de `DetalheDaLocacao` (frontend).

**Próximo passo para quem recebe:** (frontend) mostrar "Enviar contrato" só por `l.acoes.gerar_contrato`, tirar `podeEnviarContrato` de `frontend/src/lib/locacoes.ts` e o teste dele, e testar o componente com a ação `true` e `false`; o 422 `IMP-04` continua com o atalho para publicar o modelo.
