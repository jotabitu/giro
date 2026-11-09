# Manutenção e despesas

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

Toda manutenção é uma ordem de serviço ligada a um veículo, e todo custo dela vira uma despesa. Telas: `Manutencao` (quadro de OS), `Veiculo` (histórico), `Despesas`.

| Estado da OS | Significa | Veículo fica |
| --- | --- | --- |
| `agendada` | preventiva prevista por km ou data | no estado atual |
| `aguardando` | aberta, esperando aprovação do orçamento ou vaga na oficina | `em_manutencao` se já parado |
| `na_oficina` | veículo entregue à oficina | `em_manutencao` |
| `concluida` | serviço pronto e veículo liberado | `disponivel`, ou `indisponivel` com CRLV ou seguro vencido (`MAN-05`) |
| `cancelada` | não será feita | volta ao estado anterior |

**Regras**

- `MAN-01` OS tem: veículo, serviço, oficina (cadastro de oficinas parceiras), previsão de volta, orçamento e custo final. OS sem previsão não pode ir para `na_oficina`.
- `MAN-02` Orçamento acima de R$ 500 precisa de aprovação do gerente antes de executar (`APR-03`). Ex.: OS-118, pneus R$ 1.200,00.
- `MAN-03` Preventivas automáticas por regra da empresa: troca de óleo a cada 1.000 km, revisão a cada 5.000 km, pneus conferidos em toda devolução. Quando faltam 500 km, cria OS `agendada`; se o veículo está alugado, a OS é marcada para a devolução.
- `MAN-04` OS que passa da previsão vira atrasada (destaque vermelho) e avisa o gerente.
- `MAN-05` Ao concluir: lança a despesa com o custo final (ligada ao veículo), atualiza km e data da última manutenção, recalcula a próxima preventiva e libera o veículo. Se o CRLV ou o seguro do veículo venceu durante a OS (`VEI-03`), ele vai para `indisponivel`, com o motivo do documento (ex.: "Seguro vencido"), e não para `disponivel`. Renovar o documento não libera sozinho: o gerente desbloqueia depois de renovar, como no `disponivel` que venceu.
- `MAN-06` Indicadores: veículos fora de operação, gasto do mês, tempo médio na oficina (meta 2 dias), preventivas nos próximos 500 km.
