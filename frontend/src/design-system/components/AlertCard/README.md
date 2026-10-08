# AlertCard

Card em `solid` que resume, em uma frase e até quatro itens, o que precisa de ação hoje; é o único card escuro da tela.

- O consumidor fornece o título com o número total ("7 contratos precisam de ação hoje"), os itens com sua gravidade (`is-critical`, `is-warning` ou padrão, que usa `brand`) e uma ação em `wl-btn--brand`.
- Cada item é uma frase completa com número; a cor do ponto só reforça.
- O horário da última atualização fica à direita do cabeçalho em mono (`on-solid-muted`).
- No tema escuro o card fica claro (o `solid` inverte), mantendo o contraste com o canvas.

## Em React

Código em `frontend/src/design-system/components/AlertCard/AlertCard.tsx`; preview em `/design-system/alert-card`.

```tsx
import { AlertCard, Button } from "@/design-system";

<AlertCard
  atualizadoHa="há 6 min"
  titulo="7 contratos precisam de ação hoje"
  itens={[{ texto: "3 devoluções estão atrasadas", gravidade: "critica" }, { texto: "2 parcelas vencem até amanhã" }]}
  acao={<Button variante="marca">Ver pendências</Button>}
/>
```

Props: `cabecalho`, `atualizadoHa`, `titulo`, `itens` (até quatro; `gravidade`: `critica` ou `atencao`, o padrão usa a marca) e `acao`.
