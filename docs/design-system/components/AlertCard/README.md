# AlertCard

Card em `solid` que resume, em uma frase e até quatro itens, o que precisa de ação hoje; é o único card escuro da tela.

- O consumidor fornece o título com o número total ("7 contratos precisam de ação hoje"), os itens com sua gravidade (`is-critical`, `is-warning` ou padrão, que usa `brand`) e uma ação em `wl-btn--brand`.
- Cada item é uma frase completa com número; a cor do ponto só reforça.
- O horário da última atualização fica à direita do cabeçalho em mono (`on-solid-muted`).
- No tema escuro o card fica claro (o `solid` inverte), mantendo o contraste com o canvas.
