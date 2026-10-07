# KpiTile

Bloco de indicador com rótulo, número grande (`metric`) e uma linha de contexto, em grade de quatro dentro de um painel.

- O consumidor fornece rótulo curto, valor já formatado em pt-BR (`R$ 4.380`, `71%`) e uma linha de contexto que explique o número (comparação, meta ou o que fazer).
- O primeiro bloco, o número mais importante da tela, usa `wl-kpi--solid`; os demais ficam em `surface-sunken`. Nunca dois sólidos lado a lado.
- Variação usa seta e texto (`↗ 6 esta semana`), não cor sozinha.
- Em telas estreitas a grade passa para duas colunas.
