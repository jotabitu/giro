# DataTable

Tabela de listagem dentro de um painel: cabeçalho em pílula `surface-sunken`, linhas separadas por `line`, sem zebra e sem bordas verticais.

- O consumidor fornece colunas e linhas; a primeira coluna identifica o registro (placa ou código em `wl-mono`).
- Células com duas informações usam `wl-cell-main` (nome do veículo) e `wl-cell-sub` (cliente, cidade) em `ink-muted`.
- Status vai na última coluna como `wl-badge--sm`; datas curtas em `wl-mono` (`06 out`).
- Filtros e ordenação ficam no cabeçalho do painel, em botões de ícone `--sunken`.
- Linha inteira clicável abre o detalhe; ações destrutivas nunca ficam na linha.
- Em telas estreitas a tabela vira lista de cards com os mesmos campos.

## Em React

Código em `frontend/src/design-system/components/DataTable/DataTable.tsx`; preview em `/design-system/data-table`.

```tsx
import { CelulaDupla, DataTable, Panel } from "@/design-system";

<Panel titulo="Devoluções da semana">
  <DataTable
    chaveDaLinha={(l) => l.placa}
    aoAbrir={(l) => router.push(`/locacoes/${l.codigo}`)}
    linhas={linhas}
    colunas={[
      { chave: "placa", titulo: "Placa", mono: true },
      { chave: "veiculo", titulo: "Veículo e cliente", celula: (l) => <CelulaDupla principal={l.veiculo} secundaria={l.cliente} /> },
    ]}
  />
</Panel>
```

Colunas com `chave`, `titulo`, `celula` (opcional) e `mono`. `aoAbrir` torna a linha clicável e acessível por teclado (Enter e espaço). Em telas estreitas (até 720px) a tabela vira lista de cards, com o título da coluna acima de cada valor. Componente de cliente.
