# ProgressBar

Barra de andamento de 8px: trilho em `surface-sunken` e preenchimento em `solid`. Serve para os primeiros passos da implantação e para qualquer progresso com porcentagem que a API devolve.

- `valor` de 0 a 100; fora disso é limitado. O componente não calcula o percentual.
- `rotulo` é obrigatório: vira o `aria-label` do `role="progressbar"`. Escreva o texto do percentual ao lado ou em `sr-only` ("40% concluído").
- Não usa a cor da marca: cor de marca não carrega significado.

## Em React

Código em `frontend/src/design-system/components/ProgressBar/ProgressBar.tsx`; preview em `/design-system/progress-bar`.

```tsx
import { ProgressBar } from "@/design-system";

<ProgressBar valor={40} rotulo="Primeiros passos" />
```

O progresso do cartão `VehicleCard` continua com o `wl-progress` próprio (valor e barra na mesma linha).
