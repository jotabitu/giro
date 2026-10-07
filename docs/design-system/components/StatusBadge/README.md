# StatusBadge

Pílula de uma ou duas palavras que diz o estado de um veículo, contrato, título ou prioridade; o significado está sempre no texto, a cor só reforça.

| Situação | Classe | Tokens |
| --- | --- | --- |
| Veículo Disponível, título Pago | `wl-badge--success` | `success-soft` + `success-ink` |
| Reservado, A vencer | `wl-badge--info` | `info-soft` + `info-ink` |
| Alugado | `wl-badge--solid` | `solid` + `on-solid` |
| Em manutenção, prioridade Média | `wl-badge--warning` | `warning-soft` + `warning-ink` |
| Em preparação, Vendido, prioridade Baixa | `wl-badge` | `surface-sunken` + `ink` |
| Atrasado, Inadimplente | `wl-badge--critical` | `critical-soft` + `critical-ink` |
| Prioridade Alta | `wl-badge--high` | `critical` + `on-critical` |
| Estado em andamento que pede olhar (Em vistoria) | `wl-badge--attention` com `wl-badge__dot` | `warning` + `on-warning` |
| Resumo de alertas no topo da tela | `wl-badge--brand` | `brand` + `on-brand` |

Use `wl-badge--sm` (26px) dentro de tabelas densas. `wl-count` é o contador neutro do menu e de abas. Não invente cores novas para status: um novo estado entra num dos grupos acima.
