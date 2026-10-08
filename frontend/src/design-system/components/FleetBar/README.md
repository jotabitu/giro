# FleetBar

Barra segmentada que mostra quantos veículos há em cada status, com largura proporcional à contagem e número e rótulo embaixo de cada segmento.

- O consumidor fornece os status na ordem do ciclo (Disponível, Alugado, Reservado, Manutenção, À venda) e a contagem de cada um; a largura de cada coluna é `flex: <contagem>`, com mínimo de 64px para o rótulo caber. Quando os cinco segmentos não cabem na linha (lateral a 390px, dentro de um painel), os segmentos quebram para a linha de baixo em vez de estourar a largura da tela.
- Um único segmento em `brand` marca o status que a tela quer destacar (normalmente Alugado, que gera receita); um em `solid` pode marcar o fim do ciclo. Os demais ficam em `line`.
- O cabeçalho traz o total e um indicador de contexto (ocupação). Clicar num segmento filtra a lista abaixo.

## Em React

Código em `frontend/src/design-system/components/FleetBar/FleetBar.tsx`; preview em `/design-system/fleet-bar`.

```tsx
import { FleetBar } from "@/design-system";

<FleetBar
  nota="86 veículos · ocupação de 71%"
  segmentos={[{ chave: "alugado", rotulo: "Alugado", contagem: 42, destaque: "marca" }]}
  selecionado={filtro}
  aoSelecionar={setFiltro}
/>
```

Com `aoSelecionar`, cada segmento vira botão (`aria-pressed`) e filtra a lista abaixo. A API devolve as contagens; o componente só aplica a largura proporcional.
