# LigaDesliga

Interruptor de uma opção que vale na hora: ligar ou desligar um plano de preço do veículo ("Oferecer plano semanal"), a locação com compra, uma regra do assistente. Trilho de 44 × 26 px com a bolinha de 20 px. Ligado pinta em `solid` com a bolinha `on-solid`; desligado, o trilho é `line` e a bolinha `surface`. Foco com anel `focus`.

```tsx
import { Dialogo, LigaDesliga, Button } from "@/design-system";

<LigaDesliga ligado={plano.ligado} rotulo="Oferecer plano semanal" aoMudar={() => setPedido(plano)} />
```

- **Controlado e sem estado próprio.** `aoMudar` recebe o valor pedido. O interruptor só muda quando `ligado` muda; em ação com confirmação, abra um `Dialogo` no `aoMudar` e só passe `ligado` ao novo valor depois que a API responder 200.
- **Ligar e desligar plano (`VEI-12`) pede confirmação**, na tela de preços e no cartão da ficha. O diálogo diz a consequência em uma frase: ao desligar, "Este plano deixa de aparecer na Nova locação. As locações já confirmadas continuam com o preço delas."; ao desligar o último, soma "Sem nenhum plano ligado, a moto fica indisponível (sem preço)." (`VEI-15`). Ao ligar, a API pode recusar no campo (valor, forma aceita, caução): mostre o erro da API e deixe o interruptor desligado.
- **Nome acessível obrigatório** (`rotulo`): o interruptor não tem texto visível. Diga o que liga, com o nome do plano.
- Marca da empresa não entra aqui: ligado é `solid`, como os botões sólidos e o controle segmentado. Cor de status não se usa para ligado e desligado.
- Para escolher entre opções exclusivas ("Calcular pelos juros" ou "Digitar a parcela"), use o `SegmentedControl`, não dois interruptores.
- Desligado e `desabilitado` ficam distintos: o `desabilitado` tem opacidade 50% e não aceita clique (ex.: o suporte Giro, que só vê os preços, `VEI-12`).

HTML puro, sem JavaScript: `<button type="button" class="wl-toggle" role="switch" aria-checked="true" aria-label="Oferecer plano semanal"></button>`.
