# Panel

Painel `surface` com `radius-xl` e padding `space-6`: todo conteúdo da tela fica em painéis sobre o `canvas`. Não é um dos 12 componentes de `docs/design-system/components/`, mas o bundle já define `wl-panel` e DataTable, KpiTile e outros dependem dele.

```tsx
<Panel titulo="Devoluções da semana" subtitulo="5 contratos" acao={<IconButton aria-label="Filtros" icone={<Icone de={SlidersHorizontal} />} quieto compacto />}>
  ...
</Panel>
```

Sem sombra e sem borda: a escada `canvas`, `surface`, `surface-sunken` marca a hierarquia.
