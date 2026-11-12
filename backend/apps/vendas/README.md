# app `vendas`

**Schema:** empresa
**Escopo:** Propostas, funil, simulação de pagamento, troca, venda, recibo.
**Regras:** VEN (ver `docs/regras-de-negocio.md`)
**Telas:** Vendas, Venda, Vendedor (ver `docs/telas/README.md`)

## Estrutura esperada

```
vendas/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/vendas.md` (escrito pelo arquiteto antes da implementação).

## O que já existe (T-420, ADR 0037)

- `Venda` inteira (modelo de dados, item 17), com `origem` (`balcao`, `quitacao_locacao`).
- `eventos.locacao_quitada` assina `locacoes.locacao_quitada` e chama
  `services.criar_venda_da_quitacao` (`VEN-11`): venda `vendida` de R$ 0,00, veículo `alugado` →
  `vendido`, aviso aos gerentes depois do commit.
- `services.registrar_transferencia` e `POST /api/locacoes/{id}/transferencia/`.
- `GET /api/vendas/` e `GET /api/vendas/{id}/` (recurso `vendas_comissoes`).
- `leituras.py`: bloco `compra_venda` para `locacoes.Locacao` e `vendas` para a ficha do veículo;
  `selectors.transferencias_pendentes(filiais)` para o painel.
- Funil, conversão, meta e comissão (T-418 e seguintes) filtram `origem = "balcao"`.
