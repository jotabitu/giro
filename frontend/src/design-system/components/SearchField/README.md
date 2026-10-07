# SearchField

Busca global em pílula `surface` de 56px, no canto superior direito, que encontra veículo pela placa, cliente pelo nome ou CPF e contrato pelo código.

O consumidor fornece o placeholder (diga o que dá para buscar) e a ação do atalho `⌘K` (Ctrl+K no Windows), que fica no chip `brand`. Ao lado dela ficam o botão de notificações e a ação principal da tela em `wl-btn--solid` com a mesma altura de 56px.

## Em React

Código em `frontend/src/design-system/components/SearchField/SearchField.tsx`; preview em `/design-system/search-field`.

```tsx
import { SearchField } from "@/design-system";

<SearchField placeholder="Buscar placa, cliente ou contrato" />
```

Ctrl+K (⌘K no Mac) foca o campo; desligue com `atalho={false}`. `cheio` ocupa a largura do contêiner (padrão de 360px, e largura total em telas estreitas). Aceita `value`, `onChange` e os demais atributos de `<input>`. Componente de cliente.
