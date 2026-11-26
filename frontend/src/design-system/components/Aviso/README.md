# Aviso

Nota curta dentro de um painel, perto do que ela explica: o aviso de tabela de preços não preenchida (`VEI-15`), os juros acima de 1% ao mês (`VEI-16`), o valor de venda abaixo do pago. Substitui o bloco `.note` copiado em cada tela.

```tsx
<Aviso>Locadora não é financeira: juros acima de 1% ao mês (12% ao ano) pedem confirmação. Valide o contrato com seu advogado.</Aviso>
<Aviso tom="info">Mudar um preço vale para as próximas locações.</Aviso>
<Aviso tom="critico">A parcela não cobre o valor de venda.</Aviso>
```

| Tom | Classe | Tokens | Quando |
| --- | --- | --- | --- |
| `atencao` (padrão) | `wl-note` | `warning-soft` sobre `warning-ink` | pede atenção, não impede (aviso da tabela, juros, venda abaixo do pago) |
| `info` | `wl-note wl-note--info` | `info-soft` sobre `info-ink` | explica, sem pedir ação |
| `critico` | `wl-note wl-note--critical` | `critical-soft` sobre `critical-ink` | impede seguir, como o erro de campo que a API devolve |

- O significado está no texto; o tom só reforça (nunca a cor sozinha). Texto curto, em português, com a mensagem que a API ou a regra manda, sem reescrever.
- 13 px, `radius-md`, sem ícone e sem botão. Se a nota pedir uma ação, ponha o botão ao lado, fora do aviso.
- `critico` usa `role="alert"`; os outros, `role="note"`.
- Cor da empresa não entra: use sempre tons de status.
