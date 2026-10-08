// Tipos do contrato docs/api/painel.md. TEMPORÁRIO: sai quando o cliente gerado do OpenAPI (T-011) existir.
import type { VarianteInicio } from "./tipos";

/** Todo número de KPI vem tipado: dinheiro em centavos, percentual como texto com 2 casas. */
export type ValorTipado = { tipo: "numero"; valor: number } | { tipo: "centavos"; valor: number } | { tipo: "pct"; valor: string };

export type Situacao = { rotulo: string; tom: "sucesso" | "info" | "alerta" | "perigo" | "neutro" };

/** `valor: null` = módulo que ainda não existe (USR-08): o cartão não aparece. */
export type Kpi = {
  chave: string;
  rotulo: string;
  valor: ValorTipado | null;
  contexto: string | null;
  destaque?: boolean;
  tendencia?: "sobe" | "desce";
};

export type Contadores = { atualizado_em: string; contadores: Record<string, number | null> };

export type DestinoPendencia = { chave: string; filtro?: string; id?: number };

export type PendenciaInicio = { texto: string; gravidade: "critica" | "atencao" | "info"; destino: DestinoPendencia };

export type InicioGeral = {
  variante: "geral";
  atencao: { quantidade: number; texto: string };
  kpis: Kpi[];
  frota: {
    ocupacao_pct: string;
    meta_ocupacao_pct: string;
    nota: string;
    segmentos: { status: string; rotulo: string; quantidade: number }[];
  };
  devolucoes_semana: {
    subtitulo: string;
    linhas: { locacao_id: number; codigo: string; placa: string; veiculo: string; cliente: string; data: string; situacao: Situacao }[];
  };
  pendencias: { titulo: string; itens: PendenciaInicio[] };
  caixa_hoje: {
    filial: string;
    data: string;
    status: string;
    recebido_centavos: number;
    a_receber_hoje_centavos: number;
    despesas_centavos: number;
    saldo_dia_centavos: number;
  } | null;
};

export type PassoImplantacao = {
  chave: string;
  rotulo: string;
  detalhe: string;
  concluido: boolean;
  acao?: { rotulo: string; destino: string };
};

export type InicioImplantacao = {
  variante: "implantacao";
  teste: { fim: string; dias_restantes: number; texto: string } | null;
  primeiros_passos: { concluidos: number; total: number; pct: string; itens: PassoImplantacao[] };
  convites: { nome: string; contato: string; perfil: string; status: string }[];
  indicadores: { frota_cadastrada: number; alugados_agora: number; clientes: number; a_receber_centavos: number };
};

export type InicioGerente = {
  variante: "gerente";
  aprovacoes: {
    total: number;
    mais_antigo: string | null;
    itens: { id: number; tipo: string; titulo: string; detalhe: string; acoes: ("recusar" | "aprovar")[] }[];
  };
  kpis: Kpi[];
  equipe_hoje: { usuario_id: number; nome: string; perfil: string; resumo: string; online: boolean }[];
  frota_filial: { total: number; segmentos: { rotulo: string; quantidade: number }[] };
};

export type InicioVendedor = {
  variante: "vendedor";
  kpis: Kpi[];
  parcelas_atrasadas: { conta_id: number; cliente: string; locacao: string; vencimento: string; valor_centavos: number; dias: number; acao: string }[];
  precisam_acao: { locacao_id: number; codigo: string; cliente: string; situacao: Situacao }[];
  meta: null;
  funil: null;
  comissao_prevista: null;
  propostas: null;
};

export type ItemAgenda = {
  id: string;
  tipo: "saida" | "devolucao";
  horario: string;
  veiculo: { id: number; placa: string; modelo: string };
  cliente: { nome: string };
  locacao: { id: number; codigo: string };
  situacao: { codigo: string; rotulo: string; tom: Situacao["tom"] };
  vistoria_id: number | null;
  acao: { codigo: "iniciar" | "continuar" | "abrir"; rotulo: string };
};

/** Corpo de GET /api/vistorias/agenda/ (docs/api/vistorias.md). */
export type Agenda = {
  resumo: string;
  proxima: { item_id: string; em_minutos: number } | null;
  avarias_abertas: number;
  resultados: ItemAgenda[];
};

export type InicioVistoriador = { variante: "vistoriador"; agenda: Agenda; avarias_abertas: number };

export type InicioFinanceiro = {
  variante: "financeiro";
  kpis: Kpi[];
  caixas_do_dia: { filial: string; status: string; aberto_por: string | null; esperado_gaveta_centavos: number }[];
  para_hoje: { texto: string; tipo: "reembolso" | "despesa"; destino: DestinoPendencia }[];
  fluxo_previsto: null;
  conciliacao: null;
};

export type Periodo = "hoje" | "7d" | "30d";

export type Inicio = { saudacao: string; atualizado_em: string } & (
  | InicioGeral
  | InicioImplantacao
  | InicioGerente
  | InicioVendedor
  | InicioVistoriador
  | InicioFinanceiro
);

export type InicioDe<V extends VarianteInicio> = Extract<Inicio, { variante: V }>;
