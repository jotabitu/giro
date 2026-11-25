# BarraDeAcoes

Barra flutuante de ações no pé de toda tela de página inteira que cria ou edita: cartão `surface` com `shadow-pop` e raio `lg`, fixo ao rolar, "Cancelar" quieto (`wl-btn--quiet`) e o botão principal sólido (`wl-btn--solid`) à direita.

- Posição: no desktop, a 16px da borda de baixo; no celular, a 88px, acima da barra de navegação. Fica no fim do conteúdo (não é `fixed`), então o fim da página nunca some atrás dela.
- Os botões que ficavam no fim do formulário ou no cabeçalho passam para a barra. Não duplique.
- `aEsquerda` (opcional): ação secundária ou aviso ("Salvar como reserva", "Salvar e cadastrar outro"). No celular ocupa a linha de cima.
- Estado ocupado troca o texto por "Salvando…" e desabilita o botão principal.
- Não use em diálogos e painéis laterais (têm os botões no rodapé), no assistente de implantação, em fluxos com ações próprias por estado (vistoria, devolução, venda já criada) nem em tela só de leitura.
- Só tokens: `surface`, `shadow-pop`, `ink-muted`. A cor da marca vem do botão sólido, sem cor própria.

As telas de referência em `docs/telas/` mostram os botões de salvar dentro do formulário; a barra é a forma de implementação (T-514) e vale no lugar deles. Código em `frontend/src/design-system/components/BarraDeAcoes/`, preview em `/design-system/barra-de-acoes`.
