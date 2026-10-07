# FleetBar

Barra segmentada que mostra quantos veículos há em cada status, com largura proporcional à contagem e número e rótulo embaixo de cada segmento.

- O consumidor fornece os status na ordem do ciclo (Disponível, Alugado, Reservado, Manutenção, À venda) e a contagem de cada um; a largura de cada coluna é `flex: <contagem>`, com mínimo de 64px para o rótulo caber.
- Um único segmento em `brand` marca o status que a tela quer destacar (normalmente Alugado, que gera receita); um em `solid` pode marcar o fim do ciclo. Os demais ficam em `line`.
- O cabeçalho traz o total e um indicador de contexto (ocupação). Clicar num segmento filtra a lista abaixo.
