// Tipos de vendas, a partir do cliente gerado do OpenAPI (docs/api/vendas.md). Hoje só há a venda da quitação (VEN-11).
import type { components } from "./schema";

type S = components["schemas"];

export type Venda = S["Venda"];
export type ListaDeVendas = S["ListaDeVendas"];
export type OrigemDaVenda = S["OrigemVendaEnum"];
export type FiltroDeVendas = { origem?: OrigemDaVenda; transferencia_pendente?: boolean; cursor?: string };
