# T-313 · line-height do número do KpiTile · design-system → frontend, orquestrador

**O que foi feito:** `.wl-kpi__value` passou de `line-height: 1.05` para `1` em `frontend/src/design-system/componentes.css` (linha 196), a pedido da T-312. No tamanho máximo (44 px) o número ocupa 44 px, como a referência (`docs/design-system/components/bundle.css`, `line-height: 44px`), e continua proporcional quando o `clamp` encolhe a fonte. O `docs/design-system/` já tinha o valor da referência (44 px); nada a acertar lá.
**Onde:** `frontend/src/design-system/componentes.css`.
**Conferido:** numa página de teste com `wl-theme.css` e `componentes.css`, quatro tiles (86, R$ 4.380, R$ 128.450, R$ 1.284.500,00) em 260 px: altura do KpiTile de 136,2 px para 134 px; linha de 46,2 px para 44 px; sem estouro horizontal. `npx vitest run src/design-system`: 60 testes passam. Os ajustes de celular da ficha do veículo e do cliente (`leading-8`) não são afetados.
**O que ficou de fora:** não abri Dashboard, Frota nem a ficha no navegador (sem backend no worktree); a conferência foi no KpiTile isolado. O frontend confirma a ficha do veículo a 134 px contra `Veiculo-Desktop`.
**Próximo passo para quem recebe:** frontend (T-312): depois do merge, conferir os 134 px na ficha e tirar a diferença do handoff.
