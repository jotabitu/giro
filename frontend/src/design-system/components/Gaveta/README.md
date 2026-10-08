# Gaveta

Painel modal que desliza da borda da tela. É o mesmo mecanismo do `Dialogo` (elemento nativo `<dialog>`: foco preso, Escape, fundo inerte, foco devolvido), só que ancorado na borda.

```tsx
import { Gaveta, Sidebar, SeletorDeFilial } from "@/design-system";

<Gaveta aberto={menuAberto} aoFechar={() => setMenuAberto(false)} lado="esquerda" titulo="Menu">
  <Sidebar marca={...} seletorDeFilial={<SeletorDeFilial ... />} grupos={...} />
</Gaveta>
```

| `lado` | Uso | Forma |
| --- | --- | --- |
| `esquerda` | menu no celular (a Sidebar vira gaveta) | até 340px ou 88% da largura, altura toda, cantos arredondados do lado de dentro |
| `baixo` | filtros e escolhas no celular | largura toda, até 90% da altura, cantos de cima arredondados |
| `direita` | detalhe lateral no desktop | como a esquerda, espelhada |

- **Props:** `aberto`, `aoFechar`, `titulo` (obrigatório: nome da gaveta, vira o `aria-labelledby`), `descricao?`, `acoes?` (rodapé, por exemplo "Limpar" e "Ver 42 veículos"), `lado`, `fecharAoClicarFora`.
- **Menu do celular:** dentro de uma gaveta à esquerda, a `Sidebar` perde o fundo e o padding e ocupa a largura da gaveta. Feche a gaveta ao navegar (`aoFechar` no clique do item ou no `usePathname`).
- **Foco inicial:** `data-autofocus` no elemento desejado; sem ele, no painel. O botão Fechar fica no cabeçalho, com `aria-label="Fechar"`.
- O conteúdo só é montado com a gaveta aberta. Controlado, como o `Dialogo`: feche em `aoFechar`.
- Rolagem da página travada enquanto aberta; rolagem interna na gaveta. Animação de 220ms, desligada em `prefers-reduced-motion`.
- O `SeletorDeFilial` dentro da gaveta fecha a própria lista com Escape sem fechar a gaveta.
