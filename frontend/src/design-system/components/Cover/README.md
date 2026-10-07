# Cover

Capa do design system.

## Em React

Código em `frontend/src/design-system/components/Cover/Cover.tsx`; preview em `/design-system/cover`.

```tsx
import { Cover } from "@/design-system";

<Cover />
```

Capa do design system: faixa de painéis desiguais com `brand`, `solid`, `surface` e `warning` sobre o `canvas`. Serve de abertura da página de preview e de material de apresentação; não entra nas telas do produto. As cores vêm de variáveis CSS, então a capa troca com o tema e com a marca da empresa. Props: `titulo` e `descricao`.
