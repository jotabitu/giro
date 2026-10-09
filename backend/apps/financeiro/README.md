# app `financeiro`

**Schema:** empresa
**Escopo:** Contas a receber (parcelas), despesas, caixa do dia, movimentos, conciliação bancária, comissões, DRE.
**Regras:** FIN (ver `docs/regras-de-negocio.md`)
**Telas:** Receber, Caixa, Despesas, Comissoes, Conciliacao, Financeiro (ver `docs/telas/README.md`)

## Estrutura esperada

```
financeiro/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/financeiro.md` (escrito pelo arquiteto antes da implementação).

## Implementado (mínimo, com a T-015)

- `models.py`: `ContaReceber` e `Comissao`, como máquinas de estados com origem genérica (ADR 0011). A conta guarda `aberta`, `paga`, `cancelada` e `renegociada`. `vence_hoje` e `atrasada` saem do selector (`FIN-01`). A conta tem também `observacao` ("Devolver na entrega", na caução).
- `services.py`:
  - `criar_contas`, `ajustar_valor` (só a conta em aberto) e `cancelar_abertas`;
  - `marcar_paga`, a porta da baixa até a T-017. Ela grava o pagamento e publica `financeiro.parcela_paga(parcela_id, cliente_id, origem_tipo, origem_id, tipo)`;
  - `lancar_comissao` e `confirmar_comissao` (`FIN-09`): a confirmada é paga no dia 5 do mês seguinte (`mes_pagamento`).
- `selectors.py`: `contas_da_origem`, `status_exibido`, `representacao_conta`, `primeiro_pagamento_em` (1ª parcela e caução), `anotar_resumo_da_origem` (em atraso, parcela atrasada mais antiga, pago e abertas, numa query) e `comissoes_confirmadas_centavos` (`FIN-10`).

## Com a T-091

- `Reembolso` (`a_fazer` → `feito`, com o comprovante): o dinheiro que volta ao cliente. `devolver_ao_cliente` aceita Pix ou estorno no cartão; dinheiro espera o caixa da T-017. Ele também avisa os gerentes da filial no sino. `marcar_reembolso_feito` ainda não tem rota: a rota `.../reembolsos/{id}/feito/` entra com a T-017.
- `estornar_comissao` (`FIN-09`: locação cancelada antes da retirada) e `cancelar_abertas(..., vencendo_depois_de=dia)` (encerramento antecipado).
- Selectors `pago_da_origem_centavos`, `abertas_vencendo_depois` e `reembolsos_da_origem`.

A T-017 acrescenta o caixa, os movimentos (`movimento_caixa` na conta), as cobranças externas, o estorno, a API e os blocos de `clientes` (`financeiro`, `historico`, filtro `em_aberto` e contadores).
