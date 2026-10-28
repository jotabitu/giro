// Tipos do controle do suporte, a partir do cliente gerado do OpenAPI (docs/api/contas.md, "Controle do administrador").
import type { components } from "./schema";

type S = components["schemas"];

export type SituacaoDoSuporte = "todos" | "ativos" | "encerrados";
export type AcessoDoSuporte = S["AcessoDaLista"];
export type ControleDoSuporte = S["SuporteDaEmpresa"];
export type BloqueioDoSuporte = S["Bloqueio"];
