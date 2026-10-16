# T-279 · Classes wl- fora de camada vencem o Tailwind · design-system → frontend, orquestrador

**O que foi feito:** as classes `wl-` entram no CSS dentro de `@layer components`, antes dos utilitários do Tailwind. `md:hidden`, `hidden`, `md:inline-flex`, `size-11`, `bg-*` e `text-*` passam a valer por cima da classe `wl-`. Causa: `componentes.css` era importado pelo `layout.tsx`, fora do Tailwind, e uma classe solta de mesma especificidade vence o utilitário que vem antes na ordem (o `wl-icon-btn` com `display: inline-grid` ganhava do `md:hidden`).

**Onde:**
- `frontend/src/design-system/componentes.css`: todo o conteúdo dentro de `@layer components { ... }` (sem reindentar, para o diff ficar pequeno).
- `frontend/src/app/globals.css`: `@import "../design-system/componentes.css"` no topo, e as classes `wl-` do app (`.wl-marcar`, `.wl-search .wl-kbd`) também em `@layer components`.
- `frontend/postcss.config.mjs`: `postcss-import` antes do Tailwind (o Tailwind 3 só aceita `@layer` num arquivo com `@tailwind components`, então o arquivo precisa ser juntado ao `globals.css`).
- `frontend/src/app/layout.tsx`: saiu o import de `componentes.css`.
- `frontend/src/design-system/README.md`: a regra (classe `wl-` nova entra na camada, nunca solta).

**Dependência:** `postcss-import` 15.1.0 já está no `package-lock.json` (dependência do próprio Tailwind 3). Usei sem declará-la no `package.json`; se o time preferir, declarar como devDependency é uma linha.

**Conferência no navegador (admin Mariana, 23 rotas a 1440 e 390 px, script que acusa `md:hidden` visível no desktop e `hidden md:*` visível no celular):**
- Antes (app da `main`): 1440 px, 11 telas com o sintoma (o "Voltar" redondo em Aprovações, Filiais, Nova filial, Usuários, Auditoria, Configurações, Exportar, Assinatura e Cadastrar veículo; o "+" de Nova despesa; o "Nova filial" e o "Filtrar" em ícone); 390 px, 5 telas com o botão de texto de desktop aparecendo no celular (Importar planilha, Nova filial, "6 de 10 no plano", Exportar da Auditoria, Voltar da importação).
- Depois: 0 telas com o sintoma, nos dois tamanhos. Despesas a 1440 sem o "+" nem o voltar; Auditoria a 390 com voltar e filtro em ícone e sem o "Exportar" de texto.
- Testes: `vitest` completo (55 arquivos, 500 testes) e `eslint` limpos. O build compila o CSS; o `tsc` do meu worktree acusa erros de tipo do cliente da API (não gerado aqui) e de `@playwright/test` ausente, sem relação com a mudança (nenhum `.ts` foi alterado além do import do layout).

**O que ficou de fora:**
- Telas de perfis que não são administradora (vendedora, vistoriador, financeiro, gerente) e rotas de plataforma e públicas: o sintoma é por classe, não por perfil, e a varredura estática de `className` (65 pares `wl-` + utilitário) não achou caso fora dos padrões `md:hidden`, `hidden md:inline-flex`, `size-11`, `bg-*`/`text-*`, `p-0`, `min-w-*`, `rounded-full`, `text-[13px]`, todos intencionais do autor e agora efetivos (por exemplo, o `size-11` passa a dar alvo de toque de 44 px aos ícones pequenos).
- O CI do frontend não foi rodado (limite do Actions).
- A seção T-279 do backlog vive só na branch `t-272`, então não a movi; a linha está em `feito.md`.

**Próximo passo para quem recebe:** o Frontend, ao criar classe `wl-` nova ou CSS próprio, usa `@layer components`. Quem abrir o PR confere o CSS gerado: `.hidden` e `md:hidden` ficam depois de `.wl-btn` e `.wl-icon-btn`.
