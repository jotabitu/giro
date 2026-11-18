# Valores

Lista de rótulo à esquerda e valor à direita, com linha fina entre as linhas: o "Resumo" da venda (preço de tabela, desconto, preço final, entrada, saldo, comissão).

```tsx
<Valores linhas={[
  { rotulo: "Preço de tabela", valor: "R$ 22.900,00" },
  { rotulo: "Desconto 8%", valor: "− R$ 1.832,00" },
]} />
```

- Todo valor vem pronto da API ("12 × R$ 1.339,00"); a tela não soma nem arredonda.
- Para fatos em colunas dentro de um bloco, use o `wl-facts` da ficha.
- Guia visual: `docs/design-system/components/Valores/README.md`.
