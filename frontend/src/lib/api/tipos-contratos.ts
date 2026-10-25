// Tipos dos Modelos de contrato, a partir do cliente gerado do OpenAPI (docs/api/contratos.md, "Modelos").
import type { components } from "./schema";

type S = components["schemas"];

export type ModeloDeContratoDaLista = S["ModeloResumo"];
export type ModeloDeContrato = S["ModeloDetalhe"];
export type VersaoDoModeloDeContrato = S["VersaoDoModelo"];
export type MarcadorDeContrato = S["Marcador"];
export type ModeloProntoDeContrato = S["ModeloPronto"];
export type CorpoDoNovoModelo = S["ModeloEntrada"];
export type CorpoDaEdicaoDoModelo = S["PatchedModeloEdicao"];
