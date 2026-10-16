// Tipos de Administração › Usuários, a partir do cliente gerado do OpenAPI (docs/api/contas.md, "Usuários").
import type { components } from "./schema";

type S = components["schemas"];

export type StatusDoUsuario = "ativo" | "convite_pendente" | "desativado";
export type PermissaoExtra = S["PermissaoExtraEnum"];
export type PlanoDeUsuarios = S["PlanoDeUsuarios"];
export type ContagensDeUsuarios = S["ContagensDeUsuarios"];
export type UsuarioDaLista = Omit<S["UsuarioItem"], "status"> & { status: StatusDoUsuario };
export type UsuarioDetalhado = Omit<S["UsuarioDetalhe"], "status"> & { status: StatusDoUsuario };
export type ListaUsuarios = Omit<S["ListaDeUsuarios"], "resultados"> & { resultados: UsuarioDaLista[] };
export type PermissaoDoUsuario = S["PermissaoExtraDoUsuario"];
export type SituacaoDeUsuarios = "ativos" | "convites" | "desativados";
export type FiltroUsuarios = { situacao?: SituacaoDeUsuarios; perfil?: S["PerfilEnum"]; filial?: number; busca?: string; cursor?: string };
export type ConviteNovo = S["Convidar"];
export type AlteracaoDeUsuario = S["PatchedAlterarUsuario"];
export type LinkDoConvite = S["LinkDoConvite"];
export type SessaoDoUsuario = S["Sessao"];
