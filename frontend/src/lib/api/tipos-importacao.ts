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
/** IMP-08 (T-440): "Categoria de cada modelo" e as categorias que a filial da importação oferece. */
export type CategoriasDaImportacao = S["CategoriasDaImportacao"];
export type ModeloDaImportacao = S["ModeloDaImportacao"];
export type ModeloEscolhido = S["ModeloEscolhido"];
/** Antes do envio de veículos: a filial (a única ativa ou a escolhida) e se dá para importar. */
export type PreparoDaImportacao = S["Preparo"];
