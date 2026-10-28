// Recebimentos da empresa (docs/api/plataforma.md, "Recebimentos da empresa"), a partir do cliente gerado.
import type { components } from "./schema";

type S = components["schemas"];

/**
 * Campos pré-preenchidos do formulário (só em `desconectado`). O OpenAPI gerado aponta `sugestao` para o schema `Sugestao` de outra rota
 * (colisão de nome no drf-spectacular); aqui vale o contrato escrito em plataforma.md até o backend corrigir.
 */
export type SugestaoDeRecebimentos = {
  nome: string;
  documento: string;
  email: string;
  celular: string;
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
};

export type Recebimentos = Omit<S["Recebimentos"], "sugestao"> & { sugestao: SugestaoDeRecebimentos | null };
export type SituacaoDosRecebimentos = S["RecebimentosSituacaoEnum"];
export type CorpoDosRecebimentos = S["ConectarRecebimentos"];
export type TipoDeEmpresa = S["TipoEmpresaEnum"];
