# Design system em código

Porta de `docs/design-system/` para React. Dono: agente **design-system** (T-004). Importe sempre de `@/design-system`.

- `tokens.ts`: gerado por `frontend/scripts/gerar-tokens.mjs` a partir de `docs/design-system/tokens.json` (fonte única). Não edite à mão: mude o JSON e rode `node scripts/gerar-tokens.mjs`. Token novo entra no `tokens.json` e no README de `docs/design-system/`.
- `marca.ts`: white label. `cssDaMarca(hex)` gera `--brand`, `--on-brand` (contraste mínimo 4,5:1) e `--brand-soft` nos dois temas; o layout injeta o `<style id="marca-da-empresa">` e `aplicarMarca(hex)` troca em execução. Só aceita `#rrggbb`; outra coisa cai na cor padrão.
- `componentes.css`: estilos `wl-*` dos componentes, só com variáveis de token (teste garante que não há cor fixa). Porta de `docs/design-system/components/bundle.css`.
- `components/<Nome>/`: AlertCard, Button (e IconButton), Cover, DataTable, FleetBar, KpiTile, SearchField, SegmentedControl, Sidebar, StatusBadge (e Contador), TextField, VehicleCard, mais o apoio Panel. Cada pasta tem o `.tsx` e um README de uso.
- `Icone.tsx`: ícone Lucide de 20px (traço 1,75) para usar dentro dos componentes.
- Preview: `/design-system` (índice) e `/design-system/<componente>`, com troca de tema e da cor da empresa em execução. Referência visual original: `docs/design-system/components/<Nome>/preview.html`.

Regras: marca só como preenchimento (nunca texto ou borda sobre `surface`); status usam `success`, `info`, `warning`, `critical`; a marca Giro vem sempre de SVG em `docs/marca/kit/`, nunca texto digitado, e nunca verde-limão sobre branco. Fontes Geist e Geist Mono vêm do pacote `geist` (sem rede no build).
