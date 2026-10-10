// Tipos de locações, a partir do cliente gerado do OpenAPI (src/lib/api/schema.d.ts, `npm run api:gerar`).
// O gerador deixa alguns campos como `string` ou `unknown`; aqui eles ganham os valores fechados do contrato (docs/api/locacoes.md).
import type { components } from "./schema";
import type { TomApi } from "./tipos-frota";

type S = components["schemas"];

export type StatusLocacao = "rascunho" | "aguardando_retirada" | "ativa" | "devolucao_atrasada" | "encerrada" | "cancelada";
export type Periodicidade = "diaria" | "semanal" | "mensal";
export type AbaLocacoes = "abertas" | "precisam_acao" | "devolvem_hoje" | "encerradas" | "canceladas" | "rascunhos";
export type StatusParcela = "aberta" | "vence_hoje" | "atrasada" | "paga" | "renegociada" | "cancelada" | "estornada";
export type CodigoAcaoLocacao = "cobrar" | "receber_devolucao" | "abrir";

export type LocacaoResumo = Omit<S["Locacao"], "status" | "periodicidade" | "situacao" | "pagamento" | "acao_principal"> & {
  status: StatusLocacao;
  periodicidade: Periodicidade;
  situacao: { codigo: string; rotulo: string; tom: TomApi };
  /** Ausente para o vistoriador. */
  pagamento?: { rotulo: string; tom: TomApi; em_aberto_centavos: number };
  acao_principal: { codigo: CodigoAcaoLocacao; rotulo: string };
};

export type ParcelaDaLocacao = Omit<S["ParcelaLocacao"], "tipo" | "status"> & { tipo: "parcela" | "caucao" | "acerto"; status: StatusParcela };

export type CancelamentoDaLocacao = Omit<S["CancelamentoLocacao"], "status"> & { status: "pendente" | "aprovado" };

export type LocacaoCompleta = Omit<S["LocacaoDetalhe"], keyof LocacaoResumo | "parcelas" | "acoes" | "cancelamento" | "periodicidade"> &
  LocacaoResumo & {
    parcelas?: ParcelaDaLocacao[];
    cancelamento: CancelamentoDaLocacao | null;
    acoes: Omit<S["AcoesLocacao"], "cancelar"> & { cancelar: "direto" | "pedir" | false };
  };

export type ListaLocacoes = Omit<S["ListaDeLocacoes"], "resultados"> & { resultados: LocacaoResumo[] };
export type FiltroLocacoes = {
  aba?: AbaLocacoes;
  periodicidade?: Periodicidade;
  veiculo?: number;
  cliente?: number;
  busca?: string;
  ordem?: "fim_previsto" | "-inicio";
  cursor?: string;
};

export type HistoricoDaLocacao = S["HistoricoLocacao"];
export type SimulacaoDaRenovacao = S["SimulacaoRenovacao"];
export type SimulacaoDoCancelamento = S["SimulacaoCancelamento"];
export type ParcelaPrevista = S["ParcelaPrevista"];
export type AvisoLocacao = S["CodigoMensagemLocacao"];
export type PedidoDeCancelamento = S["CancelamentoPedido"]["pedido_aprovacao"];
export type FormaDevolucaoCancelamento = "pix" | "estorno_cartao";
export type TrocaPedida = S["TrocaPedida"];
export type TrocaCancelada = S["TrocaCanceladaResposta"];
export type TrocaDaLocacao = S["TrocaPendente"];

export type FormaPagamento = "pix" | "pix_automatico" | "cartao" | "boleto" | "dinheiro";
export type ParcelamentoMensal = "a_vista" | "quatro_semanais";
export type ExtraDeLocacao = S["Extra"];
export type PlanoEspecial = Omit<S["PlanoEspecial"], "periodicidade" | "regra"> & { periodicidade: Periodicidade; regra: "preco_fixo" | "desconto_a_partir" };
export type SimulacaoDaLocacao = S["SimulacaoLocacao"];
/** Corpo de simular, criar e atualizar (`PATCH` do rascunho): o mesmo formulário. */
export type EntradaDaLocacao = Omit<S["LocacaoEntrada"], "periodicidade" | "forma_pagamento" | "parcelamento_mensal"> & {
  periodicidade: Periodicidade;
  forma_pagamento: FormaPagamento;
  parcelamento_mensal?: ParcelamentoMensal | null;
};
