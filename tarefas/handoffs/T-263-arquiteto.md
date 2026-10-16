# T-263 · Ação gerar_contrato na locação · arquiteto → backend, frontend

**O que foi feito:** a [decisão] da T-208 virou contrato. O detalhe da locação ganha `acoes.gerar_contrato`, com as mesmas condições do `POST /api/locacoes/{id}/contrato/`, e a tela deixa de deduzir por estado.
**Onde:** `docs/api/locacoes.md` (exemplo do detalhe e o item `acoes.gerar_contrato`), `docs/api/contratos.md` (recusas do `POST`), `tarefas/backlog.md` (seção da T-263 no lugar da [decisão]).
**Contrato:** `acoes.gerar_contrato` = perfil que cria locação (administrador, gerente, vendedor) e `aguardando_retirada` e sem desconto pendente (`APR-01`) e sem cancelamento em curso (`LOC-12`) e sem contrato vigente (nenhum, ou `cancelado`). Não olha o modelo publicado: sem ele, o `POST` responde 422 `IMP-04` com o atalho, como a regra pede.
**Conferência da condição da tela** (`podeEnviarContrato`, `frontend/src/lib/locacoes.ts`):
- status, contrato vigente e desconto pendente batiam com o serviço (`apps/locacoes/contrato.py`, `gerar`) e com `contratos.selectors.contrato_vigente`.
- "quem cria" era lido por `acoes.cancelar`, que depende da permissão `locacoes_cancelar` e fica `false` com cancelamento em curso; agora é o perfil, como a permissão `CRIAM` da rota.
- Com cancelamento em curso, a tela escondia o botão e o serviço aceitava. O contrato fica com o comportamento da tela e o serviço passa a recusar com 409 `cancelamento_em_curso`, para a ação e o `POST` concordarem. Antes da retirada, o cancelamento aprovado cancela os contratos não assinados (`cancelar_nao_assinados`), então gerar um nesse meio-tempo não serve.
**Regras cobertas:** IMP-04, APR-01, LOC-12, fluxo da retirada (passo 3). Testes pedidos ao backend na seção da T-263 do backlog.
**O que ficou de fora:** o código (backend e frontend), que fica para as duas partes da T-263. Produto: se quiser liberar o envio do contrato com o pedido de cancelamento pendente, basta tirar a condição.
**Próximo passo para quem recebe:** backend implementa `gerar_contrato` em `acoes()` e o 409 no `gerar`, regenera o OpenAPI; frontend troca `podeEnviarContrato` por `l.acoes.gerar_contrato`.
