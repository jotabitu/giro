# Sidebar

Menu lateral de 280px em painel `surface` com `radius-xl`, que leva a marca do cliente no topo e agrupa os módulos por área.

- **Slot de marca** (`wl-brand-row`): o consumidor fornece o logotipo do cliente (imagem quadrada em `wl-logo-slot`, 40px, `radius-sm`) e o nome fantasia. Sem logo, o slot mostra as iniciais sobre `solid`.
- **Seletor de filial** (`wl-switcher`): nome e cidade da filial ativa; abre a lista de filiais. Esconda quando o cliente tiver uma filial só.
- **Itens** (`wl-nav-item`): ícone de 20px + rótulo; o ativo leva `aria-current="page"` e fica em `solid`. Um `wl-count` à direita mostra pendências reais (contratos a vencer, OS abertas); sem pendências, sem contador.
- **Grupos** (`wl-nav-label`): rótulo `overline` em maiúsculas — Operação, Financeiro.

Mostre só os módulos que o plano do cliente e o perfil do usuário liberam. No celular a sidebar vira gaveta sobre o canvas.
