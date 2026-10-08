// Lista dos componentes do preview (sem JSX: serve a páginas de servidor e de cliente).
export const CATALOGO = [
  { slug: "alert-card", nome: "AlertCard", resumo: "Resumo do que pede ação hoje" },
  { slug: "button", nome: "Button", resumo: "Sólido, cor da empresa, padrão, quieto e botão de ícone" },
  { slug: "codigo-verificacao", nome: "CodigoVerificacao", resumo: "Código de 6 dígitos das 2 etapas, com colar, teclado e erro" },
  { slug: "cover", nome: "Cover", resumo: "Capa com as cores dos tokens" },
  { slug: "data-table", nome: "DataTable", resumo: "Lista de contratos com placa, cliente e situação" },
  { slug: "dialogo", nome: "Dialogo", resumo: "Janela modal para confirmar ou preencher algo curto" },
  { slug: "fleet-bar", nome: "FleetBar", resumo: "Distribuição da frota por status" },
  { slug: "gaveta", nome: "Gaveta", resumo: "Painel que desliza da borda: menu, filtros e detalhe no celular" },
  { slug: "kpi-tile", nome: "KpiTile", resumo: "Indicadores do painel; o primeiro em destaque" },
  { slug: "linha-de-lista", nome: "LinhaDeLista", resumo: "Linha com título, apoio e ação, para listas dentro de painéis" },
  { slug: "progress-bar", nome: "ProgressBar", resumo: "Andamento em porcentagem, como os primeiros passos" },
  { slug: "search-field", nome: "SearchField", resumo: "Busca global com atalho Ctrl K" },
  { slug: "segmented-control", nome: "SegmentedControl", resumo: "Período e filtros de visão" },
  { slug: "seletor-de-filial", nome: "SeletorDeFilial", resumo: "Troca de filial no topo do menu, com Todas as filiais para o administrador" },
  { slug: "sidebar", nome: "Sidebar", resumo: "Logo da empresa, seletor de filial e menu por módulo" },
  { slug: "status-badge", nome: "StatusBadge", resumo: "Status do veículo, prioridade e contadores" },
  { slug: "text-field", nome: "TextField", resumo: "Campo com rótulo, dica e erro" },
  { slug: "vehicle-card", nome: "VehicleCard", resumo: "Veículo em destaque com contrato em andamento" },
] as const;

export type SlugExemplo = (typeof CATALOGO)[number]["slug"];
