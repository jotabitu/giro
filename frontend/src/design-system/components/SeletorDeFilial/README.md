# SeletorDeFilial

Troca de filial no topo do menu (`wl-switcher`): o botão mostra o nome e a cidade da filial ativa e abre a lista das filiais da pessoa (USR-07).

```tsx
import { SeletorDeFilial, Sidebar } from "@/design-system";

<Sidebar
  marca={...}
  seletorDeFilial={
    <SeletorDeFilial filiais={filiais} valor={filialAtiva} aoMudar={trocarFilial} permiteTodas={pode.administracao} />
  }
  grupos={...}
/>
```

- **Dados:** `filiais` com `id`, `nome` e `cidade`, só as da pessoa (a API já filtra). `valor` é o id ativo ou `"todas"` (exportado como `TODAS`).
- **Administrador:** `permiteTodas` põe "Todas as filiais" no topo da lista, com a contagem ("3 filiais"). A tela decide o que "todas" significa na consulta; o componente só devolve `"todas"`.
- **Uma filial só:** sem `permiteTodas`, o componente não renderiza nada (README da Sidebar: esconda quando a empresa tiver uma filial só).
- **Teclado:** Enter, espaço ou seta abrem; setas, Home e End movem (sem dar a volta); Enter ou espaço escolhe; Escape fecha e devolve o foco ao botão, sem fechar uma gaveta ou diálogo em volta; Tab fecha. Clique fora fecha.
- **Acessibilidade:** botão com `aria-haspopup="listbox"` e `aria-expanded`; lista `role="listbox"` com `aria-activedescendant`, cada filial `role="option"` com `aria-selected` e a marca de seleção por ícone, não só por cor. Itens de 48px de altura.
- A lista é um popup abaixo do botão (`wl-menu`, `shadow-pop`), do mesmo tamanho dele; funciona dentro da `Gaveta` do menu no celular.
- Trocar de filial é decisão da tela: guarde o id e recarregue os dados; o componente não faz requisição.
- A lógica (lista, esconder, navegação) fica em `logica.ts` e é testada sem navegador.
