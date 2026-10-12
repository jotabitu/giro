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

## Com a T-017 (contas a receber, caixa do dia, baixa e despesas)

- **Models** (migração `0004`): `Caixa` (um por filial por dia, `FIN-07`), `MovimentoCaixa` (imutável: `save` de um já gravado e `delete` levantam `MovimentoImutavel`; a correção é um estorno com `estorno_de`), `CobrancaExterna` (Pix e boleto, uma `aguardando` por conta), `PendenciaPagamento` (S-14) e `Despesa`. Na conta: `movimento_caixa`, `estorno_de` e `estornada_em`; no reembolso, `movimento_caixa`. Fora do app: `comum.WebhookRecebido` (`evento_id` único) e `plataforma.ContaPagamento` (a subconta; a chave cifrada entra com a T-029).
- **Uma baixa só** (`services._baixar`): grava forma, hora, multa e juros e publica `financeiro.parcela_paga`. Portas: `receber` (caixa, `FIN-04`, sem pagamento parcial, `FIN-01`), `processar_webhook` (`AUT-05`, consulta o parceiro e compara o valor; o diferente vira pendência) e `pagar_com_caucao`/`marcar_paga` (acerto e seed).
- **FIN-03**: `selectors.devido_ate` é a única conta; `valor_hoje` e `JurosDaPagina` (lê a configuração e a cláusula uma vez por origem na lista).
- **Contas**: `lancar_avulsa`, `cancelar`, `renegociar` (`Renegociacao` de origem `cliente`), `estornar` (nasce uma conta aberta igual; o movimento do caixa é estornado), `gerar_cobranca` (422 `recebimentos_desligados` sem subconta aprovada; `no_caixa` liga a cobrança ao caixa), `cobrar` (WhatsApp, uma vez por conta por dia) e `regua_de_cobranca` (`AUT-03`: WhatsApp em D-1, D0, D+3 e D+7; `financeiro.parcela_atrasou` em 1, 3, 7 e de 15 dias em diante).
- **Caixa**: `abrir_caixa`, `sangria` (não passa da gaveta), `estornar_movimento`, `fechar_caixa` (diferença exige motivo e abre o pedido `APR-04`), `decidir_diferenca_do_caixa` (assinante em `eventos.py`) e `fechar_caixas_sem_conferencia` (`AUT-08`).
- **Despesas**: `lancar_despesa` (acima de R$ 500 abre o pedido `APR-03`; paga no caixa só até R$ 500), `decidir_despesa` e `pagar_despesa` (dinheiro sai do caixa).
- **Devolução ao cliente**: `devolver_ao_cliente` em dinheiro sai pelo caixa aberto da filial e o reembolso nasce `feito` (422 `FIN-07` sem caixa, CA-016-18).
- **Tarefas** (`tasks.py`): `aut_03_regua_de_cobranca` (09:00), `aut_05_processar_webhook` e `aut_08_fechamento_automatico_do_caixa` (23:59).
- **Leituras para os outros apps** (`leituras.py`, ADR 0015): blocos `financeiro` e `historico`, filtro `em_aberto`, contadores `contas_atrasadas_15_dias` e `em_aberto_centavos` e o total `em_aberto_centavos` de `clientes`; contador `caixas` de `filiais` (`FIL-06`); `custo_manutencao_ano_centavos` de `veiculos`. `locacoes` fornece à conta a placa e a forma prevista (bloco `locacao`) e ao veículo o `rendeu_no_ano_centavos`.
- **API** (`api/`): contas a receber, caixas, despesas, reembolsos e pendências em `/api/financeiro/`; o webhook do parceiro em `/api/webhooks/pagamentos/asaas/`, no host da plataforma.
- Testes: `tests/aceitacao/test_t017_financeiro.py` (CA-017-01 a 23) e o CA-016-18 em `test_t016_vistorias.py`.
