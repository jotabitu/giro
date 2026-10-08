# LinhaDeLista

Linha de lista com título, apoio e ação à direita, para painéis do início ("Ver detalhes", "Cobrar", "Aprovar"). Padrão das telas `Gerente`, `Financeiro` e `Pos-Dashboard`.

- Altura mínima de 56px; divisor `line` entre linhas, sem divisor depois da última.
- `titulo` em peso 500; `apoio` em `ink-muted`, 14px. Ambos quebram linha em tela estreita; a ação não encolhe.
- `acao` recebe um `Button compacto` (ou `Link` com `wl-btn wl-btn--quiet wl-btn--sm`). No celular o compacto tem 44px de alvo de toque.
- Use `ListaDeLinhas` em volta, com `rotulo`.

## Em React

Código em `frontend/src/design-system/components/LinhaDeLista/LinhaDeLista.tsx`; preview em `/design-system/linha-de-lista`.

```tsx
import { Button, LinhaDeLista, ListaDeLinhas } from "@/design-system";

<ListaDeLinhas rotulo="Parcelas em atraso">
  <LinhaDeLista titulo="Carlos Souza" apoio="Parcela 2 de 5 · venceu em 30 set" acao={<Button variante="quieto" compacto>Cobrar</Button>} />
</ListaDeLinhas>
```
