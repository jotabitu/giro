# T-046 · Componentes pedidos pela T-020 · design-system → orquestrador, frontend (T-020, T-021)

**O que foi feito:** `SeletorDeFilial`, `Dialogo`, `Gaveta` e `KpiTile` com valor longo, em `frontend/src/design-system/components/`, exportados por `@/design-system`, cada um com README e preview em `/design-system/<slug>` (`seletor-de-filial`, `dialogo`, `gaveta`, `kpi-tile`).
**Como usar:**
```tsx
<SeletorDeFilial filiais={filiais} valor={filialId} aoMudar={setFilialId} />
<Dialogo aberto={aberto} aoFechar={() => setAberto(false)} titulo="Cancelar contrato LOC-2841"
  descricao="Não dá para desfazer." acoes={<>...</>}>...</Dialogo>
<Gaveta aberto={aberto} aoFechar={fechar} titulo="Filtros" lado="baixo" acoes={<>...</>}>...</Gaveta>
```
Todos controlados (`aberto`/`valor` vêm de quem usa). Detalhes de props nos READMEs.
**shadcn/ui:** não foi usado e nenhuma dependência nova entrou. `Dialogo` e `Gaveta` usam o `<dialog>` nativo com `showModal()` (foco preso, Escape, fundo inerte e devolução do foco pelo navegador), sobre os tokens do design system. Base comum em `components/Dialogo/modal.tsx`.
**KpiTile:** o valor encolhe de 44px até 16px conforme a largura do bloco (container query + `--chars`), nunca é cortado; abaixo do mínimo quebra no espaço. Sem abreviar o valor, a API manda formatado.
**Validação no celular (portal 390x844, não Edge headless):** sem rolagem horizontal; `R$ 1.284.350,00` fica em 16px dentro do bloco sem estourar (`scrollWidth` = `clientWidth`) na grade de 2 colunas; a `Gaveta` com `lado="baixo"` ancora embaixo na largura toda e o foco vai ao painel; fecha por `cancel` e pelo botão Fechar; a lista do `SeletorDeFilial` fica dentro da tela. O Escape sintético do portal não dispara o `cancel` nativo, então esse caminho foi testado por evento `cancel`.
**Testes:** `componentes.test.tsx` (ARIA do diálogo, lado da gaveta, conteúdo só quando aberto, `--chars`, container query) e `SeletorDeFilial.test.tsx` (12). Suíte: 69 passando; `eslint` e `tsc --noEmit` limpos.
**O que ficou de fora:** teste de interação no navegador (foco e Escape reais) fica para o QA/Playwright; o ambiente de testes é `node`.
**Próximo passo para quem recebe:** Frontend usa `SeletorDeFilial` na casca (T-020) e `Dialogo`/`Gaveta` nos filtros e confirmações da T-021. Neste worktree foi preciso `npm install` porque `react-hook-form`, `zod` e `@tanstack/react-query` vieram da T-020.
