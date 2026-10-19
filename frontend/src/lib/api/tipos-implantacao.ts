// Andamento do assistente de implantação (docs/api/plataforma.md, "GET /api/implantacao/", T-201).
// ATENÇÃO: a rota ainda não está em docs/api/openapi.yaml (backend T-202 pendente), então estes tipos seguem o contrato escrito.
// Quando a rota entrar no OpenAPI, trocar por tipos gerados de schema.d.ts (T-335, handoff).

export type ChaveDoPasso = "marca" | "filial" | "ramo" | "precos" | "contrato" | "recebimentos" | "importar" | "equipe";

export type PassoDoAssistente = { passo: ChaveDoPasso; numero: number; rotulo: string; feito: boolean; feito_em: string | null };

export type AndamentoDoAssistente = {
  concluida: boolean;
  total: number;
  feitos: number;
  /** Primeiro passo ainda não feito, na ordem; `null` quando todos estão feitos. */
  proximo: ChaveDoPasso | null;
  passos: PassoDoAssistente[];
};
