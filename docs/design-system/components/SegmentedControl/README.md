# SegmentedControl

Troca de visão entre duas a quatro opções curtas, como período (Hoje, 7 dias, 30 dias) ou tipo de veículo.

O consumidor fornece as opções e qual está ativa (`aria-pressed="true"`, que pinta em `solid`). O trilho é `surface-sunken`; use dentro de painéis brancos, no cabeçalho à direita do título. Para mais de quatro opções, use um menu suspenso.

Também escolhe um valor de um formulário com poucas opções exclusivas, com o nome do grupo num rótulo acima (`wl-field__label`) e `aria-label` igual no grupo: periodicidade da locação com compra (Diárias, Semanais, Quinzenais, Mensais) e como definir a parcela (Calcular pelos juros, Digitar a parcela). Uma opção só liga ou desliga com o `LigaDesliga`, não com o segmentado.
