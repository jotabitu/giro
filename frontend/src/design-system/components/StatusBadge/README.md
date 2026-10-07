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

## Em React

Código em `frontend/src/design-system/components/StatusBadge/StatusBadge.tsx`; preview em `/design-system/status-badge`.

```tsx
import { Contador, StatusBadge } from "@/design-system";

<StatusBadge tom="sucesso">Disponível</StatusBadge>
<StatusBadge tom="atencao" ponto>Em vistoria</StatusBadge>
```

Tons: `neutro`, `sucesso`, `info`, `alerta`, `critico`, `alta`, `atencao`, `solido`, `marca` e `superficie`, mapeados para as classes da tabela acima. `compacto` é o `wl-badge--sm`. O tom `marca` usa a cor da empresa e só serve para resumo de alertas, nunca para significado de status.
