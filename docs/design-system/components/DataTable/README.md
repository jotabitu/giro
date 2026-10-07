# DataTable

Tabela de listagem dentro de um painel: cabeçalho em pílula `surface-sunken`, linhas separadas por `line`, sem zebra e sem bordas verticais.

- O consumidor fornece colunas e linhas; a primeira coluna identifica o registro (placa ou código em `wl-mono`).
- Células com duas informações usam `wl-cell-main` (nome do veículo) e `wl-cell-sub` (cliente, cidade) em `ink-muted`.
- Status vai na última coluna como `wl-badge--sm`; datas curtas em `wl-mono` (`06 out`).
- Filtros e ordenação ficam no cabeçalho do painel, em botões de ícone `--sunken`.
- Linha inteira clicável abre o detalhe; ações destrutivas nunca ficam na linha.
- Em telas estreitas a tabela vira lista de cards com os mesmos campos.
