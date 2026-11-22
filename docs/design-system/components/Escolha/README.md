# Escolha

Opções que se excluem, em cartões com título e uma linha de apoio: a forma de pagamento da venda ("À vista", "Entrada + parcelas"). Duas a quatro opções; para mais, use `select`. Para um valor curto num filtro, o `SegmentedControl`.

- Grupo: `div.wl-choice` com `role="radiogroup"` e `aria-label`. Cada opção é um `button.wl-choice__item` com `role="radio"` e `aria-checked`; a escolhida ganha o anel de `ink` (2 px). Cor da empresa não entra.
- Título em 500 e apoio em `<small>` (`ink-muted`, 13 px). Os cartões se distribuem em colunas de pelo menos 140 px, então em 390 px ficam em uma ou duas colunas.
- A opção que a regra não permite não aparece. Na venda, "Financiamento" fica fora até a fase 3 (`VEN-18`); não use `disabled` para esconder opção.
- Teclado: setas movem a escolha dentro do grupo, como todo `radiogroup`; foco com o anel de `focus`.
