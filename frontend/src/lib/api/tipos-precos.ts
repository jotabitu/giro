// Tipos das Tabelas de preço, a partir do cliente gerado do OpenAPI (docs/api/veiculos.md "Categorias e preços", docs/api/locacoes.md "Planos especiais").
import type { components } from "./schema";

type S = components["schemas"];

export type CategoriaDePreco = S["Categoria"];
export type PrecoDaCategoria = S["PrecoComData"];
export type CorpoDoPreco = S["PrecoEntrada"];
/** O mesmo corpo com a data a partir da qual o preço vale (`vigente_desde` ≥ hoje, LOC-15). */
export type CorpoDoPrecoComData = CorpoDoPreco & { vigente_desde?: string };
export type PrecoGravado = S["PrecoCriado"];
export type PrecoDoHistorico = S["PrecoHistorico"];
export type MudancaDePreco = S["MudancaDePreco"];
export type CorpoDaCategoria = Omit<S["CategoriaEntrada"], "preco"> & { preco?: CorpoDoPreco };
export type TipoDaCategoria = S["TipoVeiculoEnum"];

export type ExtraDePreco = S["Extra"];
export type CorpoDoExtra = S["ExtraEntrada"];
export type CobrancaDoExtra = S["CobrancaEnum"];

export type PlanoEspecialDePreco = S["PlanoEspecial"];
export type CorpoDoPlanoEspecial = S["PlanoEspecialEntrada"];
export type PeriodicidadeDoPlano = S["PeriodicidadeEnum"];
export type RegraDoPlano = S["RegraEnum"];
