// Tipos da importação por planilha, a partir do cliente gerado (docs/api/importacao.md).
import type { components } from "./schema";

type S = components["schemas"];

export type TipoDeImportacao = S["TipoImportacaoEnum"];
export type StatusDaImportacao = S["StatusImportacaoEnum"];
export type StatusDaLinha = S["StatusLinhaImportacaoEnum"];
export type Importacao = S["Importacao"];
export type LinhaDaImportacao = S["Linha"];
export type ErroDaLinha = S["ErroDaLinha"];
export type NovaImportacao = { tipo: TipoDeImportacao; arquivo: File; filial_id?: number };
