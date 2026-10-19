// Tipos de Configurações, a partir do cliente gerado do OpenAPI (docs/api/configuracoes.md).
import type { components } from "./schema";

type S = components["schemas"];

// O enum do OpenAPI ainda não traz `ramo` (o cartão existe na API desde a T-262); sai daqui quando o backend regenerar o enum.
export type ChaveDoCartao = S["CartaoDeConfiguracoesChaveEnum"] | "ramo";
export type CartaoDeConfiguracoes = Omit<S["CartaoDeConfiguracoes"], "chave"> & { chave: ChaveDoCartao };
export type ImplantacaoDeConfiguracoes = S["ImplantacaoDeConfiguracoes"];
export type Configuracoes = Omit<S["Configuracoes"], "cartoes"> & { cartoes: CartaoDeConfiguracoes[] };

// O ramo da empresa (docs/api/empresas.md, "Ramo da empresa").
export type Ramo = S["Ramo"];
export type AtividadeDoRamo = S["AtividadeEnum"];
export type TrabalhaCom = S["TrabalhaComEnum"];
export type CorpoDoRamo = S["MudarRamo"];
