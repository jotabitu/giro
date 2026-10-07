// Tipos do contrato docs/api/clientes.md. TEMPORÁRIO: sai quando o cliente gerado do OpenAPI existir.
import type { TomApi } from "./tipos-frota";

export type StatusCliente = "ativo" | "incompleto" | "bloqueado" | "inativo";
export type TipoCliente = "pf" | "pj";
export type TipoDocumentoCliente = "cnh_frente" | "cnh_verso" | "selfie_documento" | "comprovante_residencia";

export type AcaoPrincipal = {
  codigo: "cobrar" | "completar_cadastro" | "ver_proposta" | "ver_locacao" | "nova_locacao";
  rotulo: string;
  alvo: { tipo: "conta" | "cliente" | "venda" | "locacao"; id: number } | null;
};

export type ClienteResumo = {
  id: number;
  tipo: TipoCliente;
  nome: string;
  documento_mascarado: string;
  celular: string;
  status: StatusCliente;
  situacao: { codigo: string; rotulo: string; tom: TomApi };
  cliente_desde: string;
  locacao_atual: { id: number; codigo: string; veiculo: string; detalhe: string; alerta: string | null; valor_a_devolver_centavos?: number } | null;
  ultima_locacao: { codigo: string; encerrada_em: string } | null;
  financeiro: { total_pago_centavos: number; em_aberto_centavos: number; a_devolver_centavos: number } | null;
  venda_aberta: { id: number; codigo: string; veiculo: string } | null;
  acao_principal: AcaoPrincipal | null;
};

export type ListaClientes = {
  contagens: { todos: number; com_locacao: number | null; em_aberto: number | null; bloqueados: number; incompletos: number };
  indicadores: { novos_no_mes_anterior: number; com_locacao_pct: string | null; em_aberto_total_centavos: number | null };
  resultados: ClienteResumo[];
  proximo: string | null;
  anterior: string | null;
};

export type SituacaoCliente = "com_locacao" | "em_aberto" | "bloqueados" | "incompletos" | "inativos";
export type FiltroClientes = { situacao?: SituacaoCliente; busca?: string; ordem?: "-criado_em" | "nome" | "-total_pago"; cursor?: string };

export type EnderecoCliente = { cep?: string; logradouro?: string; numero?: string; complemento?: string | null; bairro?: string; cidade?: string; uf?: string };

/** Corpo de POST /api/clientes/ (e de /clientes/analisar/). Só tipo, nome, documento e celular são obrigatórios. */
export type NovoCliente = {
  tipo: TipoCliente;
  nome: string;
  documento: string;
  celular: string;
  nascimento?: string;
  email?: string;
  profissao?: string;
  cnh?: { numero?: string; categoria?: string; validade?: string; primeira_habilitacao?: string };
  responsavel?: { nome?: string; cpf?: string; celular?: string };
  endereco?: EnderecoCliente;
  referencia?: { nome?: string; parentesco?: string; telefone?: string };
  consentimento?: boolean;
};

export type ItemAnalise = { codigo: string; situacao: "ok" | "pendente" | "problema"; rotulo: string };
export type AnaliseCadastro = { itens: ItemAnalise[] };

export type ClienteCompleto = ClienteResumo & {
  documento: string;
  pendencias: string[];
  analise: AnaliseCadastro;
};
