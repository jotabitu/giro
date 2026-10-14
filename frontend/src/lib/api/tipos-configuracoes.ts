// Tipos de Configurações, a partir do cliente gerado do OpenAPI (docs/api/configuracoes.md).
import type { components } from "./schema";

type S = components["schemas"];

export type ChaveDoCartao = S["CartaoDeConfiguracoesChaveEnum"];
export type CartaoDeConfiguracoes = S["CartaoDeConfiguracoes"];
export type ImplantacaoDeConfiguracoes = S["ImplantacaoDeConfiguracoes"];
export type Configuracoes = S["Configuracoes"];
