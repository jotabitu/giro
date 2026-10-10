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

## Implementado (T-091)

- `fim.py`: as contas do fim da locação, sem banco.
  - `calcular_atraso` (`LOC-10`, `LOC-11`, `FIL-03`): o prazo é o fim previsto mais a tolerância. Ele passa para a abertura seguinte quando a filial está fechada no fim previsto ou fecha antes de a tolerância acabar. A devolução fora do horário vale como feita na abertura seguinte. Cada 24 h (ou fração) desde o fim cobra 1 diária, sem as horas de feriado. Filial sem horário conta como aberta o dia todo.
  - `depois_da_retirada` e `antes_da_retirada` (`LOC-12`, `LOC-13`): o período em curso, os dias restantes, a multa (20%, no mínimo 1 diária), o crédito das semanas (mensal) ou das diárias não usadas e o saldo (`devolver` ou `cobrar`).
- `services.py`:
  - `calcular_atraso(locacao, momento)`, que soma o atraso guardado numa renovação, e `marcar_devolucoes_atrasadas` (`AUT-02`). Esta leva para `devolucao_atrasada` no dia seguinte ao fim previsto, quando a devolução feita agora já teria atraso;
  - `montar_renovacao` e `renovar` (`LOC-08`): o mesmo LOC, as parcelas novas com o preço de hoje, o aditivo pelo `contrato.gerar_aditivo` e nenhuma comissão. A `devolucao_atrasada` volta a `ativa`, com o atraso corrido guardado (`atraso_anterior_*`);
  - `calcular_encerramento` e `cancelar` (`LOC-12`, `APR-02`). O gerente, o administrador e quem tem `cancelar_contrato` cancelam direto; o vendedor abre o pedido. Antes da retirada, a locação fica `cancelada` e o pago vira `Reembolso`; o veículo reservado volta a `disponivel`, a comissão é estornada e o contrato sem assinatura é cancelado. Depois da retirada, o encerramento antecipado fica aprovado e as parcelas que vencem depois do dia são canceladas;
  - `aplicar_decisao_cancelamento`, a volta do `APR-02`;
  - `encerrar(locacao, devolvida_em=...)`, para a devolução da T-016: `encerrada`, ou `cancelada` no encerramento antecipado. Publica `locacoes.locacao_encerrada`. O veículo fica com `vistorias` (`DEV-04`).
- `Locacao` ganhou `cancelamento_status`, `pedido_cancelamento_id`, `cancelamento_data`, `cancelamento_forma`, `credito_encerramento_centavos`, `atraso_anterior_dias` e `atraso_anterior_centavos` (migração `0002`).
- Rotas: `POST .../renovar/simular/`, `.../renovar/`, `.../cancelamento/simular/` e `.../cancelar/`. O sinal `cancelamento_pendente`, a aba "Precisam de ação", o rótulo "Multa R$ 84,80" e o bloco `cancelamento` do detalhe.
- `tasks.py`: `aut_02_marcar_devolucao_atrasada`, de hora em hora no Beat.

## Implementado (T-092)

- `TrocaVeiculo` (migração `0004`): `pendente` → `concluida` (`REGRA_TRANSICAO = "transicao_troca"`), uma pendente por locação. As vistorias e a diferença de caução ficam só pelos ids (`vistoria_devolucao_id`, `vistoria_saida_id`, `conta_caucao_id`), porque `vistorias` fica acima (ADR 0011).
- `services.py` (`LOC-09`):
  - `pedir_troca`: só em `ativa` e sem cancelamento em curso (409). 422 `CLI-02`, `FIL-05` e `LOC-03` para o veículo novo. Reserva o novo e, com a caução da nova categoria maior, cria a conta `caucao` da diferença, com vencimento hoje. Caução menor não gera conta: o acerto final desconta da caução total paga;
  - `preco_da_troca`: o preço de hoje da nova categoria (como na renovação); o plano de preço fixo continua se valer para ela;
  - `caucao_da_troca_paga`, `troca_pendente` e `vincular_vistorias_da_troca`, para `vistorias`;
  - `concluir_troca`: fecha o trecho e abre o novo, passa a locação ao veículo novo (`alugado`) com o preço, a diária e a caução da nova categoria, e refaz as parcelas em aberto que vencem depois do dia da troca (`financeiro.ajustar_valor`): só a parte do período muda, com o mesmo desconto.
- A rota `POST /api/locacoes/{id}/trocar-veiculo/` fica em `vistorias`, porque abre as duas vistorias. `acoes.trocar_veiculo` fica `false` com uma troca pendente ou um cancelamento em curso.

## Implementado (T-123, decisões da troca)

- `TrocaVeiculo` (migração `0005`): o preço da nova categoria no dia do pedido (`valor_periodo_centavos`, `diaria_centavos`, `caucao_centavos`, `preco_do_dia`; a migração preenche as trocas antigas pelo dia de `criado_em`), a diferença do período guardada na conclusão (`periodo_inicio`, `periodo_fim`, `dias_do_periodo`, `dias_restantes`, `periodo_antigo_centavos`, `periodo_novo_centavos`, `ja_refeito_centavos`, `diferenca_centavos`) e o cancelamento (`cancelada_em`, `cancelada_por`, `motivo_cancelamento`).
- `pedir_troca` grava o preço do dia (`preco_da_troca(locacao, veiculo, dia)`); `concluir_troca` usa o guardado (`preco_guardado`), não a tabela do dia.
- `_parcela_refeita`: a parcela inteira pelo preço novo do período `k` dela, com todos os descontos (`calculo.preco_com_descontos`), mais os extras por período; no mensal em 4 semanais, a quarta parte do mês; na diária, cada diária da parcela da renovação.
- `_diferenca_do_periodo`: `fim.periodo_em_curso` (o mesmo período e dias restantes do `LOC-12`) e `proporcional`; no mensal em 4 semanais, desconta o que as parcelas refeitas do período já subiram (`ja_refeito_centavos`).
- `cancelar_troca(troca, motivo, usuario)`: troca `cancelada`, veículo novo `disponivel` e a conta aberta da diferença de caução `cancelada` (`financeiro.services.cancelar_conta`); a paga fica. As vistorias são de `vistorias.services.cancelar_troca`.
- `cancelar` (direto e pedido) responde 409 `troca_pendente` com a troca pendente, antes do perfil. `acoes.cancelar` vem `false`, `acoes.cancelar_troca` vem `true` com a saída do novo ainda não concluída, e o detalhe ganha o bloco `troca` (sem `preco` e `caucao` para o vistoriador).
- `selectors.trocas_concluidas(locacao)`, para o item `diferenca_troca` do acerto. O status das vistorias da troca e o `devolucao_id` do detalhe vêm de `vistorias` pelo registro de leituras (ADR 0015).

## Fica para as próximas tarefas

- T-016: a vistoria de saída chama `registrar_vistoria_saida(locacao, km=..., concluida_em=...)` depois de `clientes.selectors.impedimentos_para_retirada`. A devolução usa `calcular_atraso`, `multa_encerramento_centavos` e `credito_encerramento_centavos` no acerto e, no fim, chama `encerrar`.

Testes: `tests/aceitacao/test_t015_locacoes.py` e `test_t091_locacao_fim.py`. A carteira de outubro no banco fica em `tests/aceitacao/carteira.py`.
