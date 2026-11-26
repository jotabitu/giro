# Etapas

Linha do tempo vertical de um processo que anda por passos: a assinatura e a entrada da venda (contrato enviado, cliente assina, entrada paga, venda concluída). Mostra o que já foi, o que se espera agora e o que vem depois, com texto em todos os passos.

- `ol.wl-steps` com um `li` por passo. O estado fica no `li`: `data-state="done"` (marcador cheio em `solid`), `aria-current="step"` (anel de `ink`, o passo em que o processo está parado) e sem atributo (anel de `line`, pendente).
- Dentro do `li`: `wl-steps__title` (500), `wl-steps__text` (14 px, `ink-muted`, a data, quem fez ou o que falta) e, se houver ação, `wl-steps__acts` com botões `wl-btn--sm`. A ação fica no passo a que pertence ("Copiar link para assinar" no passo da assinatura).
- Mais de um passo pode estar atual quando eles andam em paralelo, como a assinatura e a entrada da venda (`VEN-15`: em qualquer ordem).
- O estado nunca depende só do marcador: o texto diz "Assinado em 07 out" ou "Aguardando pagamento". Aviso de erro ou de bloqueio vai num `Aviso` abaixo da lista, não dentro do passo.
- Quem decide o estado de cada passo é a API; a tela só põe o atributo.
