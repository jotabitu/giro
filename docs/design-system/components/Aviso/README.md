# Aviso

Nota curta dentro de um painel, perto do que ela explica: tabela de preços não preenchida (`VEI-15`), juros acima de 1% ao mês e venda abaixo do pago (`VEI-16`). Substitui o `.note` copiado em cada tela.

| Tom | Classe | Tokens | Quando |
| --- | --- | --- | --- |
| atenção (padrão) | `wl-note` | `warning-soft` sobre `warning-ink` | pede atenção, não impede |
| info | `wl-note wl-note--info` | `info-soft` sobre `info-ink` | explica, sem pedir ação |
| crítico | `wl-note wl-note--critical` | `critical-soft` sobre `critical-ink` | impede seguir; erro de campo da API |

O significado está no texto; o tom só reforça. 13 px, `radius-md`, sem ícone e sem botão (se pedir ação, o botão fica ao lado, fora do aviso). `role="alert"` no crítico, `role="note"` nos outros. Cor da empresa não entra.
