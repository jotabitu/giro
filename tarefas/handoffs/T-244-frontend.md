# T-244 · Despesas: ajustes da tela · frontend → qa, design-system

**O que achei na tela real** (gerente e financeiro, 1440px e 390px, antes de mexer):
1. **O "+ Avulso" do pedido não existe no código** (nem na `main`, nem na pilha de integração, nem nas telas de referência). O que aparecia no desktop era o botão redondo "+" ("Nova despesa", `aria-label`), que é só do celular: o link tinha `md:hidden`, mas `.wl-icon-btn` define `display` sem camada e vence o utilitário do Tailwind. Esse é o botão que sai do desktop; no celular ele fica, como na referência `Despesas-Mobile`. Se o dono se referia a outro botão, a captura ajuda.
2. **A busca saía do bloco:** `.wl-search` tem 360px por padrão e o bloco da busca tem 220px (como a referência); a busca ia de x=808 a x=1168 e o painel da lista termina em x=1052, invadindo o espaço da coluna "Nova despesa".
3. **Exportar** já estava no canto direito do cabeçalho (`ml-auto`, só desktop, só quem tem `pode.despesas_exportar`); nada a mudar.

**O que foi feito:** `frontend/src/components/financeiro/ListaDespesas.tsx`
- O "+" ficou dentro de um `div ml-auto md:hidden`; quem some no desktop é o wrapper.
- O bloco da busca recebe `[&_.wl-search]:!w-full`: a busca ocupa os 220px do bloco, dentro do painel (medido: x 808 a 1028).

**Conferência:** subi o Next deste worktree (porta 3100, API da 8000) e medi no navegador: desktop sem o "+" e busca de 220px dentro do painel; celular com o "+" visível. Teste `t_244_cabecalho_e_busca_como_a_referencia` em `Despesas.test.tsx`. `tsc`, `eslint` e os 27 testes de Despesas passam.

**O que ficou de fora:** nada do pedido. Fica a causa de fundo, para o design-system: classes do `componentes.css` (`.wl-icon-btn`, `.wl-search`) vencem utilitários do Tailwind porque estão fora de camada; outras telas podem ter o mesmo sintoma com `hidden`/`md:hidden`/largura em componentes `wl-`. Não mexi no CSS.
