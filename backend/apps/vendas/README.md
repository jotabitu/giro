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

## Fase 1c da T-502 (ADR 0042, itens 8, 13 e 14)

Em módulos próprios, para não cruzar com a fase 1b (`services.py`, `contratos`, `financeiro`):

- `envio.py`: o PDF da proposta (`contratos.pdf.gerar`, armazenamento privado, sem versão), o e-mail com o PDF anexo depois do commit (tarefa `vendas_enviar_proposta`, em `tasks.py`; o envio mais novo vence), o texto pronto do envio (`VEN-19`) e o link público da proposta (S-15, como o recibo da devolução: hash do token, 7 dias, um vivo por venda, token no fragmento, consulta por POST). Ligado por `GIRO_PROPOSTA_PUBLICA`, desligado até a revisão da Segurança.
- `metas.py`: `MetaVenda` por vendedor, filial e mês (`VEN-09`); a meta da filial é a soma.
- `resumo.py`: funil, conversão, vendido e ticket médio, em negociação, meta e propostas para retornar (`VEN-08`, `VEN-09`, `VEN-12`, `VEN-16`). O ticket médio do início (`relatorios`, T-487) e o resumo leem as vendas concluídas por `selectors.vendidas_entre`.
- `api/fase_1c.py`: as rotas `vendas/resumo/`, `vendas/metas/`, `vendas/{id}/proposta/link/` e `publico/propostas/consultar/`.

`services.enviar_proposta` e `services.criar(acao="enviar")` só chamam `envio.agendar_envio`.
