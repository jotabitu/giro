# KpiTile

Bloco de indicador com rótulo, número grande (`metric`) e uma linha de contexto, em grade de quatro dentro de um painel.

- O consumidor fornece rótulo curto, valor já formatado em pt-BR (`R$ 4.380`, `71%`) e uma linha de contexto que explique o número (comparação, meta ou o que fazer).
- O primeiro bloco, o número mais importante da tela, usa `wl-kpi--solid`; os demais ficam em `surface-sunken`. Nunca dois sólidos lado a lado.
- Variação usa seta e texto (`↗ 6 esta semana`), não cor sozinha.
- Em telas estreitas a grade passa para duas colunas.

## Em React

Código em `frontend/src/design-system/components/KpiTile/KpiTile.tsx`; preview em `/design-system/kpi-tile`.

```tsx
import { KpiGrid, KpiTile, KpiVariacao } from "@/design-system";

<KpiGrid>
  <KpiTile destaque rotulo="Frota ativa" valor="86" contexto="52 motos · 34 carros" />
  <KpiTile rotulo="Alugados agora" valor="42" contexto={<><KpiVariacao>↗ 6</KpiVariacao> esta semana</>} />
</KpiGrid>
```

`valor` chega formatado da API; o componente não calcula. `KpiGrid` tem quatro colunas e passa a duas em telas estreitas.

## Valor longo no celular

O numero encolhe para caber no bloco, nunca e cortado: o componente passa o tamanho do texto ao CSS (`--chars`) e o tamanho da fonte vai de 44px ate o minimo de 16px conforme a largura do bloco (container query). Em 4 colunas no desktop o `R$ 1.284.350,00` fica menor que o `71
## Valor longo no celular

O número encolhe para caber no bloco e nunca é cortado: o componente passa o tamanho do texto ao CSS (`--chars`) e a fonte vai de 44px até o mínimo de 16px conforme a largura do bloco (container query). Em quatro colunas no desktop, `R$ 1.284.350,00` fica menor que `71%`; no celular, em duas colunas, encolhe mais. Abaixo do mínimo o texto quebra no espaço em vez de estourar. Mande o valor já formatado pela API, sem abreviar (nada de `1,2 mi`).
