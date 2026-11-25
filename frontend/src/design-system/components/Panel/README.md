# Panel

Painel `surface` com `radius-xl` e padding `space-6`: todo conteúdo da tela fica em painéis sobre o `canvas`. Não é um dos 12 componentes de `docs/design-system/components/`, mas o bundle já define `wl-panel` e DataTable, KpiTile e outros dependem dele.

```tsx
<Panel titulo="Devoluções da semana" subtitulo="5 contratos" acao={<IconButton aria-label="Filtros" icone={<Icone de={SlidersHorizontal} />} quieto compacto />}>
  ...
</Panel>
```

Sem sombra e sem borda: a escada `canvas`, `surface`, `surface-sunken` marca a hierarquia.

`className` (opcional) é só para o layout da página: altura e alinhamento no grid. Um exemplo é o "Devoluções da semana" do Início, que vai até o fim do "Caixa de hoje" (`xl:absolute xl:inset-0 xl:flex xl:flex-col`). Não use para mudar o visual do painel (cor, borda, sombra, raio, padding), que fica no `wl-panel`.
