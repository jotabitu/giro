# SegmentedControl

Troca de visão entre duas a quatro opções curtas, como período (Hoje, 7 dias, 30 dias) ou tipo de veículo.

O consumidor fornece as opções e qual está ativa (`aria-pressed="true"`, que pinta em `solid`). O trilho é `surface-sunken`; use dentro de painéis brancos, no cabeçalho à direita do título. Para mais de quatro opções, use um menu suspenso.

## Em React

Código em `frontend/src/design-system/components/SegmentedControl/SegmentedControl.tsx`; preview em `/design-system/segmented-control`.

```tsx
import { SegmentedControl } from "@/design-system";

<SegmentedControl rotulo="Período" valor={periodo} aoMudar={setPeriodo} opcoes={[{ valor: "hoje", rotulo: "Hoje" }, { valor: "7d", rotulo: "7 dias" }]} />
```

Controlado: o consumidor guarda o `valor`. `rotulo` nomeia o grupo para leitores de tela. Componente de cliente.
