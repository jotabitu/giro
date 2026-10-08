# T-054 · Componentes e telas apontados na T-048 e na T-053 · design-system → orquestrador, frontend, qa

**O que foi feito:**
- **FleetBar a 390 px:** `.wl-pipe__row` passa a quebrar linha (`flex-wrap`), então os 5 segmentos (mínimo de 64 px cada) descem para a linha de baixo em vez de estourar a lateral. Em tela larga nada muda.
- **Botão compacto:** `.wl-btn--sm` fica com 44 px de altura até 720 px de largura (36 px acima). Vale para `Button compacto` e para `Link` com `wl-btn wl-btn--quiet wl-btn--sm`; os consumidores não precisam mudar nada.
- **`ProgressBar`** (`valor` 0 a 100, `rotulo` obrigatório, `role="progressbar"`) e **`LinhaDeLista` / `ListaDeLinhas`** (título, apoio e ação, mínimo de 56 px), cada um com README e preview (`/design-system/progress-bar`, `/design-system/linha-de-lista`). O catálogo passou de 16 para 18 componentes.
- **Telas de referência (T-053, `FIN-15`):** contadores do menu nas 32 telas desktop (inclui `Main` e `Financeiro`, que tinha 11) e no `Menu-Mobile`: Contas a receber 2, Despesas 1; Conciliação e Manutenções sem número. CNPJ 12.345.678/0001-95 nas 10 telas da divergência (14 arquivos, contando as versões celular, mais a chave Pix do `Onboarding-Recebimentos`).

**Onde:** `frontend/src/design-system/` (`componentes.css`, `components/ProgressBar`, `components/LinhaDeLista`, `components/index.ts`, `componentes.test.tsx`), `frontend/src/app/design-system/{catalogo.ts,exemplos.tsx}`, `docs/telas/html/*.dc.html`.
**Testes:** `componentes.test.tsx` (bloco T-054): botão 44 px no celular, `flex-wrap` da barra de frota, limite de `ProgressBar`, `LinhaDeLista`. `eslint`, `tsc`, 108 testes e `next build` verdes. Não conferi o `FleetBar` a 390 px no navegador (sem Playwright no projeto); a conta fecha: 5 × 64 + gaps = 344 px, mais que os cerca de 270 px da lateral, então quebra.
**Fora do pedido, mesma causa:** o CNPJ da `Filial` e do `Filial-Mobile` (Messejana) era 12.345.678/0002-90, com dígito errado; troquei para 12.345.678/0002-76 (cálculo conferido; é o mesmo valor que o backlog dá para a filial 0002).
**O que ficou de fora:**
- Os números de outubro do `Receber` e "Entra hoje" do `Financeiro` (aguardam a carteira de outubro no seed, qa).
- Não mexi no quadro (`tarefas/*.md`), como pedido.
- Os consumidores da T-048 (`LinhaDoPainel` em `components/inicio/comuns.tsx` e o `div` de progresso em `InicioImplantacao`) seguem como estão.
**Próximo passo para quem recebe:** frontend pode trocar `LinhaDoPainel`/`ListaDoPainel` por `LinhaDeLista`/`ListaDeLinhas` (a prop `fim` vira `acao`) e o `div` de progresso por `<ProgressBar valor={p.pct} rotulo="Primeiros passos" />`. Orquestrador abre o PR e atualiza o quadro.
