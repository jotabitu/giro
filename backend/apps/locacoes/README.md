# app `locacoes`

**Schema:** empresa
**Escopo:** Planos especiais, locações, reservas, contratos e modelos de contrato, renovação, cancelamento.
**Regras:** LOC (ver `docs/regras-de-negocio.md`)
**Telas:** Locacao, Locacoes, Locacao-Detalhe, Contratos-Modelos (ver `docs/telas/README.md`)

## Estrutura esperada

```
locacoes/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/locacoes.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-015)

- `models.py`:
  - `PlanoEspecial` (ativável): `preco_fixo` ou `desconto` a partir de um período, com o `CHECK` do campo da regra;
  - `Locacao`, uma máquina de estados (`REGRA_TRANSICAO = "transicao_locacao"`), com código `LOC`, a restrição `uma_locacao_aberta_por_veiculo` (`LOC-03`) e o `CHECK` do fim depois do início. `valor_periodo_centavos` é o preço do período (tabela ou plano de preço fixo) congelado na confirmação, sem descontos (`LOC-15`). O pedido `APR-01` fica em `desconto_status`, `desconto_pedido_pct` e `pedido_desconto_id` (sem FK, ADR 0019). O rascunho guarda os extras em `extras_rascunho` e o último uso em `usado_em`;
  - `ExtraLocacao`, com o valor congelado, e `TrechoLocacao`, um aberto por locação.
- `calculo.py`: as contas sem banco (`LOC-01` a `LOC-05`, `LOC-14`). São os períodos pelo fim previsto (fração conta como período), o preço por período com o plano especial, o desconto do vendedor, os extras por período ou únicos e as parcelas. A diária sai toda na retirada, a semanal a cada 7 dias, a mensal a cada mês ou em 4 semanais (`dividir_em_parcelas`).
- `services.py`:
  - `montar`: preço de hoje, impedimentos (`CLI-05`, `cliente_inativo`, `CLI-02`, `FIL-05`, `LOC-03`) e avisos (`CLI-03`, CNH vencida, `IMP-04`);
  - `criar_rascunho`, `editar_rascunho` e `cancelar_rascunhos_sem_uso` (24 h);
  - `confirmar`, numa transação só. Ele congela os preços, cria as contas a receber (parcelas e caução) e a comissão `pendente`, e reserva o veículo quando o início é futuro. Desconto acima do limite de um vendedor abre o `APR-01`. A corrida pelo mesmo veículo para na restrição do banco e responde 409 `LOC-03`;
  - `aplicar_decisao_desconto`, a volta do `APR-01`;
  - `verificar_ativacao`, `registrar_vistoria_saida`, `registrar_contrato_assinado` e `registrar_pagamento`. Com as três condições, a locação fica `ativa`, o veículo `alugado` e a comissão `confirmada`;
  - os planos especiais: `criar_plano`, `editar_plano` e `desativar_plano`.
- `selectors.py`: `simular`, a lista (abas, filtros, contagens e indicadores), `linha` (sinais, situação, pagamento e ação), `detalhe`, `sem_valores` (para o vistoriador) e `historico`.
- `leituras.py` registra o que os outros apps leem (ADR 0015):
  - em `veiculos.Veiculo`: `locacao_atual`;
  - em `clientes.Cliente`: `locacao_atual`, `ultima_locacao`, o filtro `com_locacao` e o contador `locacao_aberta`;
  - em `filiais.Filial`: `indicadores.locacoes_ativas` e o contador `locacoes`;
  - em `veiculos.Categoria`: o contador `locacoes_em_andamento`.
- `eventos.py`: os assinantes de `financeiro.parcela_paga`, `contratos.contrato_assinado` (o aditivo não conta) e `aprovacoes.pedido_decidido` (`APR-01`).
- `tasks.py`: `locacoes_cancelar_rascunhos_sem_uso`, de hora em hora.
- `contrato.py` (T-090): os valores dos marcadores da locação, `gerar`, `reenviar` e `gerar_aditivo` (para a renovação da T-091), e o registro da prévia com dados reais. As rotas `POST /api/locacoes/{id}/contrato/`, `GET .../contrato/pdf/` e `POST .../contrato/reenviar/`.

## Fica para as próximas tarefas

- T-091:
  - a renovação (`LOC-08`), que chama `contrato.gerar_aditivo(locacao)`;
  - o atraso, com `calcular_atraso` e a `aut_02` (`LOC-10`, `LOC-11`);
  - o cancelamento e o encerramento antecipado (`LOC-12`, `LOC-13`, `APR-02`), com o reembolso e o estorno da comissão;
  - o sinal `cancelamento_pendente` e o bloco `cancelamento`.
- T-092: a troca de veículo (`LOC-09`).
- T-016: a vistoria de saída chama `registrar_vistoria_saida(locacao, km=..., concluida_em=...)` depois de `clientes.selectors.impedimentos_para_retirada`.

Testes: `tests/aceitacao/test_t015_locacoes.py`. A carteira de outubro no banco fica em `tests/aceitacao/carteira.py`.
