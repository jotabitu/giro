# Aprovações

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

Tudo que precisa de aprovação usa o mesmo mecanismo: o pedido fica `pendente`, aparece no topo do início do gerente (`Gerente`) e só tem efeito quando aprovado. Recusado, a origem volta ao estado anterior e quem pediu é avisado com o motivo.

| Código | O que | Limite | Quem pede | Quem aprova | Efeito ao aprovar |
| --- | --- | --- | --- | --- | --- |
| `APR-01` | Desconto em locação ou venda | acima de 5% | vendedor | gerente (ou permissão extra) | libera o preço com desconto; venda segue o funil |
| `APR-02` | Cancelamento de locação | sempre | vendedor | gerente | cancela e calcula multa e acerto |
| `APR-03` | Despesa ou orçamento de OS | acima de R$ 500 | qualquer perfil que lança despesa | gerente | despesa vai para `a_pagar`; OS pode executar |
| `APR-04` | Diferença no fechamento do caixa | qualquer valor | quem fecha o caixa | gerente | caixa fechado com a diferença registrada |
| `APR-05` | Desbloqueio manual de cliente | pedido pelo vendedor (gerente e administrador desbloqueiam direto, `CLI-05`) | vendedor | gerente | cliente volta a `ativo` (ou `incompleto`, se faltar cadastro) |
| `APR-06` | Correção de km para baixo | sempre | vistoriador | gerente | km corrigido com motivo |

**Regras**

- `APR-07` Aprovação pelo celular com 1 toque (aprovar / recusar / detalhes). Recusar exige motivo.
- `APR-08` Pedido sem resposta em 4 horas úteis avisa o administrador. **Fase 2** (`AUT-09`): no MVP, nenhuma tela fala do aviso.
- `APR-09` Quem pediu não pode aprovar o próprio pedido, mesmo tendo a permissão, com uma exceção: o **administrador** pode decidir (aprovar ou recusar, `APR-07`) o próprio pedido. Gerente, vendedor, vistoriador e financeiro continuam proibidos, também com a permissão extra (`USR-03`); o pedido deles fica para outra pessoa que aprova. O pedido do administrador continua nascendo `pendente` (ele não pula a aprovação) e pode ser decidido por ele ou por outra pessoa que aprova; quem decide primeiro fecha o pedido. O evento de auditoria da decisão marca "aprovou o próprio pedido" (ou "recusou o próprio pedido") (`APR-10`).
- `APR-10` Todo pedido, aprovação e recusa entra na auditoria.
- `APR-11` Aprovar uma correção de km (`APR-06`) depois que outra leitura já mudou o km do veículo é recusado com 409 `km_mudou`, e o pedido continua `pendente`. O gerente recusa o pedido e a correção é pedida de novo a partir do km atual. A leitura mais nova nunca é apagada (`VEI-01`).
- `APR-12` **Números da tela `Aprovações`.** Contam os pedidos das filiais da pessoa (a filial escolhida no seletor, `USR-07`), sem os pedidos que ela mesma fez (`APR-09`; os do administrador entram nos números dele, porque ele pode decidi-los), no mês corrente pelo dia da decisão, em `America/Sao_Paulo`. Pedido `cancelado` não entra em nenhum número.
  - **Aprovadas no mês:** quantos pedidos foram aprovados no mês. **Tempo médio:** média de (aprovado em − pedido em) dos aprovados no mês, em horas e minutos corridos, arredondada para o minuto ("1 h 30 min"; abaixo de 1 hora, "40 min"); sem aprovados, sem número.
  - **Recusadas no mês:** quantos pedidos foram recusados no mês.
  - **Descontos aprovados:** soma, em reais, do desconto dos pedidos de desconto (`APR-01`) aprovados no mês (preço de tabela − preço com desconto) e quantos são.
  - **Esperando você:** os pedidos `pendente` que a pessoa pode decidir, de qualquer mês, e há quanto tempo espera o mais antigo.
  - **Abas:** Pendentes (os mesmos de "Esperando você"), Aprovadas e Recusadas (as do mês) e Meus pedidos (os que a pessoa fez, para cancelar o `pendente`).
