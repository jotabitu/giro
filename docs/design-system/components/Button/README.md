# Button

Pílula de 48px para ações; a sólida (`solid`) é a ação principal da tela e aparece uma vez por área.

- **Sólido** (`wl-btn wl-btn--solid`): a ação que a tela existe para fazer — "Nova locação", "Salvar contrato".
- **Cor do cliente** (`wl-btn--brand`): destaque secundário dentro de um card escuro ou para chamar atenção a alertas. No máximo um por tela; o texto é `on-brand`.
- **Padrão** (`wl-btn`, fundo `surface`): ações sobre o canvas, ao lado da busca.
- **Quieto** (`wl-btn--quiet`, fundo `surface-sunken`): ações dentro de um painel branco, como "Cancelar" e "Detalhes".
- **Compacto** (`wl-btn--sm`, 36px): dentro de tabelas e cards.
- **Botão de ícone** (`wl-icon-btn`): círculo de 48px (ou 40px com `--sm`); sempre com `aria-label`. `wl-notify` adiciona o ponto `critical` de notificação.

O consumidor fornece o rótulo (verbo no infinitivo ou substantivo de ação, sem ponto final, primeira letra maiúscula) e, se quiser, um ícone de 20px antes do texto. Desabilitado usa o atributo `disabled`; nunca esconda a ação principal.
