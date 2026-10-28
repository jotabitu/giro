// Recebimentos da empresa (docs/api/plataforma.md, "Recebimentos da empresa"), a partir do cliente gerado.
import type { components } from "./schema";

type S = components["schemas"];

export type SugestaoDeRecebimentos = S["SugestaoDosRecebimentos"];
export type Recebimentos = S["Recebimentos"];
export type SituacaoDosRecebimentos = S["RecebimentosSituacaoEnum"];
export type CorpoDosRecebimentos = S["ConectarRecebimentos"];
export type TipoDeEmpresa = S["TipoEmpresaEnum"];
