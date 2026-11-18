# Escolha

Opções que se excluem, em cartões com título e uma linha de apoio: a forma de pagamento da venda ("À vista", "Entrada + parcelas"). De duas a quatro opções; para mais, `SelectField`. Para um filtro curto, `SegmentedControl`.

```tsx
<Escolha
  rotulo="Forma de pagamento"
  valor={forma}
  aoMudar={setForma}
  opcoes={[
    { valor: "a_vista", titulo: "À vista", apoio: "Pix ou TED" },
    { valor: "entrada_parcelas", titulo: "Entrada + parcelas", apoio: "boleto ou Pix mensal" },
  ]}
/>
```

- Controlado. `role="radiogroup"` com `aria-label`; cada cartão é `role="radio"` com `aria-checked`. Setas movem a escolha e o foco.
- A escolhida ganha o anel de `ink` (2 px). Cor da empresa não entra.
- A opção que a regra não permite não aparece (na venda, "Financiamento" fica fora até a fase 3, `VEN-18`); não use `desabilitado` para esconder opção.
- Guia visual: `docs/design-system/components/Escolha/README.md`.
