# BarraDeAcoes

Barra flutuante de ações no pé de toda tela de página inteira que cria ou edita: cartão `surface` com `shadow-pop` e raio `lg`, fixo ao rolar, "Cancelar" quieto (`wl-btn--quiet`) e o botão principal sólido (`wl-btn--solid`) à direita.

- **Bloco fixo e barra (T-519):** a tela mantém o bloco de botões de sempre (no painel lateral, no cabeçalho ou no fim do formulário, como na tela de referência) e a barra **repete só Cancelar e o botão principal**, sem `aEsquerda`. Com `blocos` (retorno de `useBlocoVisivel()`), a barra fica escondida enquanto o bloco aparece e surge, com transição suave, quando ele sai da tela ao rolar. Os dois conjuntos enviam o mesmo form e têm o mesmo estado ocupado e desligado. Não é "mover" os botões: o bloco continua na tela, e a barra só cobre a rolagem.
- Sem `blocos`, a barra aparece sempre. Serve à tela que não tem bloco fixo de botões.
- Escondida, a barra continua ocupando o lugar (o layout não pula) e fica `inert` e `aria-hidden`.
- Bloco com `display: none` (por exemplo, o do cabeçalho no celular) conta como fora da tela: a barra fica à mostra. Se o bloco existe em dois lugares, basta um aparecer para a barra ficar escondida.
- No celular, com o aside embaixo do formulário, vale a mesma regra.
- Posição: no desktop, a 16px da borda de baixo; no celular, a 88px, acima da barra de navegação. Fica no fim do conteúdo (não é `fixed`), então o fim da página nunca some atrás dela.
- `aEsquerda` (opcional): ação secundária ou aviso, para a barra sem bloco fixo. No celular ocupa a linha de cima. Na tela com bloco fixo, a ação secundária fica no bloco, não na barra.
- Estado ocupado troca o texto por "Salvando…" e desabilita o botão principal.
- Não use em diálogos e painéis laterais (têm os botões no rodapé), no assistente de implantação, em fluxos com ações próprias por estado (vistoria, devolução, venda já criada) nem em tela só de leitura.
- Só tokens: `surface`, `shadow-pop`, `ink-muted`. A cor da marca vem do botão sólido, sem cor própria.

As telas de referência em `docs/telas/` mostram os botões de salvar dentro do formulário: eles continuam lá (T-519). A barra é a forma de implementação (T-514) para a página longa. Código em `frontend/src/design-system/components/BarraDeAcoes/`, preview em `/design-system/barra-de-acoes`.
