# LigaDesliga

Interruptor de uma opção que vale na hora: ligar ou desligar um plano de preço do veículo, a locação com compra, uma regra do assistente. Trilho de 44 × 26 px, bolinha de 20 px. Ligado pinta em `solid` com a bolinha `on-solid`; desligado, o trilho é `line` e a bolinha `surface`. Foco com anel `focus`.

```html
<button type="button" class="wl-toggle" role="switch" aria-checked="true" aria-label="Oferecer plano semanal"></button>
```

- Sem texto visível: o `aria-label` é obrigatório e diz o que liga, com o nome do plano.
- Ligar e desligar plano (`VEI-12`) pede confirmação, na tela de preços e no cartão da ficha. O diálogo diz a consequência em uma frase (ver o guia em `frontend/src/design-system/components/LigaDesliga/README.md`).
- Desabilitado: `disabled`, opacidade 50%.
- Cor da empresa e cores de status não entram: ligado é `solid`. Para opções exclusivas use o `SegmentedControl`.
- Substitui o `.tg` copiado em várias telas (40 × 24 ou 44 × 26 px): o tamanho é o do `wl-toggle`.
