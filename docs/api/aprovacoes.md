# Aprovações

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-043, mínimo para a fase 1) · **App:** `aprovacoes` (schema da empresa) · **Regras:** APR-01 a APR-10, CLI-05, LOC-03, LOC-12, FIN-05, FIN-07 · **ADR:** 0011 (origem genérica, evento `aprovacoes.pedido_decidido`) · **Telas:** Gerente (fase 2), e os avisos do sino

Convenções gerais em `docs/api/README.md`. Modelo: `PedidoAprovacao` em `docs/decisoes/modelo-de-dados.md`.

Os pedidos **nascem** nos outros módulos (desconto e cancelamento em `locacoes.md`, desbloqueio em `clientes.md`, correção de km em `veiculos.md`, despesa e diferença de caixa em `financeiro.md`). Aqui ficam só a lista e a decisão. A tela `Gerente` com aprovação de 1 toque (`APR-07`) e o lembrete de 4 horas úteis (`APR-08`) são da fase 2; os endpoints abaixo já servem a eles.

## Quem decide

| Tipo | O que | Quem aprova |
| --- | --- | --- |
| `APR-01` | desconto acima de 5% em locação (venda na fase 2) | gerente, administrador, ou quem tem `aprovar_desconto` |
| `APR-02` | cancelamento de locação | gerente, administrador, ou quem tem `cancelar_contrato` |
| `APR-03` | despesa ou orçamento de OS acima de R$ 500 | gerente, administrador |
| `APR-04` | diferença no fechamento do caixa | gerente, administrador |
| `APR-05` | desbloqueio manual de cliente (pedido do vendedor) | gerente, administrador |
| `APR-06` | correção de km para baixo | gerente, administrador |

- Quem pediu nunca decide o próprio pedido (`APR-09`): 403 `{ "codigo": "APR-09", "mensagem": "Outra pessoa precisa decidir este pedido" }`.
- Gerente decide pedidos das suas filiais; administrador, de todas.

## Representação

```json
{
  "id": 91, "tipo": "APR-03", "status": "pendente",
  "titulo": "Despesa de R$ 1.200,00", "detalhe": "Pneus (2 unidades) · PMZ-3E17",
  "origem": { "tipo": "despesa", "id": 801, "codigo": null },
  "filial": { "id": 1, "nome": "Filial Centro" },
  "solicitante": { "id": 4, "nome": "João Silva" }, "pedido_em": "...", "motivo_pedido": null,
  "valor_centavos": 120000, "pct": null,
  "decidido_por": null, "decidido_em": null, "motivo_recusa": null,
  "pode_decidir": true
}
```
`titulo` e `detalhe` são textos prontos da API; o vistoriador nunca vê pedidos com valor.

## GET /api/aprovacoes/
Query: `?status=pendente|aprovado|recusado|cancelado` (padrão `pendente`), `?tipo=`, `?minhas=true` (pedidos que eu fiz). Ordem: mais antigo primeiro (quem espera há mais tempo).
200: `{ "contagens": { "pendente": 2 }, "resultados": [ ... ] }`. A contagem `pendente` alimenta o sino do gerente.

## POST /api/aprovacoes/{id}/aprovar/
Corpo: `{ motivo? }`. 200: pedido `aprovado`. Publica `aprovacoes.pedido_decidido`, e o app da origem aplica o efeito na mesma transação (despesa → `a_pagar`; caixa → `fechado` com a diferença; cliente → desbloqueado; km corrigido; desconto aplicado; cancelamento feito).

## POST /api/aprovacoes/{id}/recusar/
Corpo: `{ motivo }` (obrigatório, `APR-07`). 200: `recusado`. A origem volta ao estado anterior (despesa → `recusada`; caixa → `aberto`; desconto → 0) e quem pediu é avisado com o motivo.

## POST /api/aprovacoes/{id}/cancelar/
Quem pediu desiste. 200: `cancelado`; a origem volta ao estado anterior.

Erros comuns: 409 `transicao_pedido` em pedido já decidido; 403 `APR-09`; 404 fora do escopo de filial. Todo pedido, aprovação e recusa entra na auditoria (`APR-10`).
