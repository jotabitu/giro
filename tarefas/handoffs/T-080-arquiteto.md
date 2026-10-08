# T-080 · Como um app abaixo de aprovações abre um pedido · arquiteto → orquestrador, backend, qa

**Decisão (ADR 0019, detalha a 0011):**
- Os pedidos são abertos por uma porta em `comum`: `comum.aprovacoes.pedir(...) -> PedidoRef(id, tipo, status)`.
- O app `aprovacoes` registra a implementação no `ready()`, no mesmo padrão de `comum.permissoes` e `comum.empresa`. `veiculos` e `clientes` (nível 6) abrem pedidos sem importar `aprovacoes` (nível 7).
- A chamada roda na transação da origem e devolve o `id`. Por isso o endpoint responde 202 `{ "pedido_aprovacao": { "id", "tipo", "status": "pendente" } }` sem evento de ida. Um evento não serve, porque `publicar` não devolve valor.
- Sem implementação registrada, `pedir` falha (`RuntimeError`), para nenhum pedido se perder em silêncio.
- **Caminho único:** `clientes`, `veiculos`, `financeiro`, `manutencao`, `locacoes` e `vendas` abrem pedidos só por `comum.aprovacoes.pedir`, mesmo os que a 0011 deixaria importar `aprovacoes`. O teste de limites passa a recusar `import aprovacoes` nesses seis apps.
- **Volta:** continua o evento `aprovacoes.pedido_decidido`. Cada origem assina em `<app>/eventos.py` e aplica o efeito pelo próprio serviço, com o que ficou em `dados` (APR-06: `{ km_novo, km_anterior }`).
- **Origem:** a genérica da 0011 (`origem_tipo`, `origem_id`, `origem_codigo`). `filial_id` é a da origem; no `APR-05`, como o cliente é da empresa, vale a filial da requisição de quem pediu.
- **Pedido repetido** com o mesmo `(tipo, origem)` ainda pendente: 409 `pedido_pendente` com `detalhes.pedido_id`.

**Onde:**
- `docs/decisoes/0019-pedido-de-aprovacao-pela-porta-em-comum.md` e o índice em `docs/decisoes/README.md`.
- `docs/decisoes/modelo-de-dados.md`: o `PedidoAprovacao` ganhou `filial`, `motivo_pedido`, `titulo` e `detalhe`. O contrato já mostrava esses campos, mas o modelo não tinha.
- `docs/api/aprovacoes.md`: interface interna e `dados` por tipo.
- `docs/api/veiculos.md` (APR-06) e `docs/api/clientes.md` (APR-05, e a nota antiga "enquanto o dono não decide" trocada pela decisão de 07 out).
- `tarefas/em-andamento.md`.

**Em qual tarefa entra o APR-06 do CA-013-16:** na **T-013**, só a ida, porque o CA pede o 202 com o `id` e o km parado em 3.500. Isso inclui:
- o model `PedidoAprovacao` com a migração;
- `comum/aprovacoes.py`;
- `aprovacoes.services.pedir` com auditoria `APR-10`;
- o registro no `ready()`;
- os testes obrigatórios da ADR 0019.

A decisão (endpoints de `aprovacoes.md`: lista, aprovar, recusar, cancelar, o evento e o assinante de `veiculos` que corrige o km) fica numa **tarefa nova de backend "Aprovações: lista e decisão"**, que o orquestrador cria. Ela também serve ao `APR-05` da T-014 e aos pedidos de T-015 e T-017.

**Check:** só documentação; nenhum arquivo de `backend/` ou `frontend/` mudou, então não rodei os checks de código.

**Próximo passo para quem recebe:**
- **Orquestrador:** acrescentar à T-013 o item da ida acima e criar a tarefa de lista e decisão das aprovações, antes da T-015.
- **Backend:** seguir a ADR 0019 na T-013.
- **QA:** o CA-013-16 vale como está; ele pode ganhar o caso do 409 `pedido_pendente` (João pede de novo).
