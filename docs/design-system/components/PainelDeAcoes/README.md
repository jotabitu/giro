# PainelDeAcoes

Painel "Ações" no **topo da coluna lateral** das fichas (veículo e cliente, desktop). No cabeçalho da ficha ficam só "Editar" e a ação principal (`wl-acoes-topo`); as demais ações viram linhas do painel: ícone num quadrado `surface-sunken`, nome e uma explicação curta em `ink-muted`.

```tsx
<PainelDeAcoes>
  <LinhaDeAcao rotulo="Transferir" detalhe="Mudar de filial, com vistoria rápida" icone={<Icone de={ArrowLeftRight} />} href="/veiculos/movimentacoes/nova?transferir=1" />
  <LinhaDeAcao rotulo="Movimentar" detalhe="Veículo alugado não se movimenta." icone={<Icone de={Truck} />} disabled />
  <SeparadorDeAcoes />
  <LinhaDeAcao perigo rotulo="Dar baixa" detalhe="Tirar da frota de vez" icone={<Icone de={ArrowDownToLine} />} onClick={abrir} />
</PainelDeAcoes>
```

- Com `href` a linha é link (`externo` abre em outra aba); sem `href`, botão. `disabled` vira botão desligado.
- **Perigo por último**, depois de `SeparadorDeAcoes`, com `perigo` (`critical-ink` e `critical-soft`).
- **Acessibilidade:** o nome acessível é o `rotulo` (`aria-labelledby`) e o `detalhe` é a descrição (`aria-describedby`). Não use `aria-label`: ele esconderia o texto. Numa ação desligada o `detalhe` é o motivo e fica **visível**; só o ícone e o nome esmaecem, o motivo mantém o contraste de `ink-muted`.
- Só tokens: `space-*`, `radius-md` e `radius-sm`, `surface-sunken`, `ink`, `ink-muted`, `line`, `focus`, `critical-ink`, `critical-soft`.
- Não use em celular (a ficha usa o menu "Mais ações") nem para a ação principal da tela.

Código em `frontend/src/design-system/components/PainelDeAcoes/`, preview em `/design-system/painel-de-acoes`.
