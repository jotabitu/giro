# Etapas

Linha do tempo vertical de um processo que anda por passos: a assinatura e a entrada da venda (contrato enviado, cliente assina, entrada paga, venda concluída).

```tsx
<Etapas
  rotulo="Assinatura e entrada"
  etapas={[
    { titulo: "Contrato enviado", texto: "07 out, 10:20 · diego.martins@exemplo.com.br", estado: "feita" },
    { titulo: "Assinatura do cliente", texto: "Aguardando assinatura. O cliente assina pelo celular.", estado: "atual" },
    { titulo: "Venda concluída", estado: "pendente" },
  ]}
/>
```

- `feita` (marcador cheio em `solid`), `atual` (anel de `ink`, `aria-current="step"`) e `pendente` (anel de `line`). Dois passos podem ser `atual` quando andam em paralelo (assinatura e entrada, `VEN-15`).
- Todo passo diz o estado em texto. Erro ou bloqueio vai num `Aviso` abaixo da lista.
- Quem decide o estado de cada passo é a API; a tela só repassa.
- Guia visual: `docs/design-system/components/Etapas/README.md`.
