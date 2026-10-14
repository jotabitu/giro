// Tipos de Administração › Auditoria e Exportar dados, a partir do cliente gerado (docs/api/auditoria.md).
import type { components } from "./schema";

type S = components["schemas"];

export type CategoriaDeAuditoria = S["CategoriaAuditoriaEnum"];
export type TipoDeAtor = S["TipoAtorEnum"];
export type EventoDeAuditoria = S["Evento"];
export type DetalheDoEvento = S["EventoDetalhe"];
export type PessoaDaAuditoria = S["PessoaDaAuditoria"];
export type PeriodoDaAuditoria = "7d" | "30d" | "90d";
export type FiltroAuditoria = {
  categoria?: CategoriaDeAuditoria;
  ator?: number;
  ator_tipo?: "sistema" | "suporte";
  periodo?: PeriodoDaAuditoria;
  cursor?: string;
};
export type ListaEventos = S["ListaDeEventos"];

export type StatusDaExportacao = S["StatusExportacaoEnum"];
export type ExportacaoRecente = S["Exportacao"];
export type PeriodoDaExportacao = S["Periodo"];
/** No MVP só existe a auditoria em CSV (docs/api/auditoria.md, "O que existe no MVP"). */
export type PedidoDeExportacao = { itens: ["auditoria"]; formato: "csv"; periodo: PeriodoDaExportacao | null };
