# Sidebar

Menu lateral de 280px em painel `surface` com `radius-xl`, que leva a marca do cliente no topo e agrupa os módulos por área.

- **Slot de marca** (`wl-brand-row`): o consumidor fornece o logotipo do cliente (imagem quadrada em `wl-logo-slot`, 40px, `radius-sm`) e o nome fantasia. Sem logo, o slot mostra as iniciais sobre `solid`.
- **Seletor de filial** (`wl-switcher`): nome e cidade da filial ativa; abre a lista de filiais. Esconda quando o cliente tiver uma filial só.
- **Itens** (`wl-nav-item`): ícone de 20px + rótulo; o ativo leva `aria-current="page"` e fica em `solid`. Um `wl-count` à direita mostra pendências reais (contratos a vencer, OS abertas); sem pendências, sem contador.
- **Grupos** (`wl-nav-label`): rótulo `overline` em maiúsculas — Operação, Financeiro.

Mostre só os módulos que o plano do cliente e o perfil do usuário liberam. No celular a sidebar vira gaveta sobre o canvas.

## Em React

Código em `frontend/src/design-system/components/Sidebar/Sidebar.tsx`; preview em `/design-system/sidebar`.

```tsx
import { Icone, Sidebar } from "@/design-system";
import { LayoutGrid } from "lucide-react";
import Link from "next/link";

<Sidebar
  componenteLink={Link}
  marca={{ nome: empresa.nome, logoSrc: empresa.logoUrl }}
  filial={{ nome: "Filial Centro", cidade: "Fortaleza, CE" }}
  grupos={[{ itens: [{ rotulo: "Visão geral", href: "/inicio", icone: <Icone de={LayoutGrid} />, ativo: true }] }]}
/>
```

Sem `logoSrc`, o slot mostra as iniciais do nome (ou `iniciais`). O logo da empresa vem da API; a marca Giro não aparece aqui (ela só vive no painel da plataforma, sempre por SVG de `docs/marca/kit/`). `contador` só aparece quando maior que zero. Passe `componenteLink={Link}` para navegar sem recarregar.

## Seletor de filial e menu do celular

Passe `seletorDeFilial={<SeletorDeFilial ... />}` para trocar de filial pelo menu; ele tem prioridade sobre `filial`, que continua servindo só para mostrar a filial ativa. No celular, coloque a Sidebar dentro de uma `Gaveta` com `lado="esquerda"`.
