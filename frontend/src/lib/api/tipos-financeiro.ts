// Tipos do financeiro (contas a receber e caixa do dia), a partir do cliente gerado do OpenAPI (schema.d.ts, `npm run api:gerar`).
// O gerador deixa `forma` e `tipo` como `string`; aqui eles ganham os valores fechados do contrato (docs/api/financeiro.md).
import type { components } from "./schema";

type S = components["schemas"];

export type TipoDeConta = "parcela" | "caucao" | "multa" | "avaria" | "acerto" | "outro";
export type StatusDaConta = S["StatusContaReceberEnum"];
export type FaixaDeAtraso = S["FaixaAtrasoEnum"];
export type FormaPrevista = "pix" | "pix_automatico" | "cartao" | "boleto" | "dinheiro";
export type FormaDaBaixa = "dinheiro" | "cartao_debito" | "cartao_credito" | "pix" | "boleto" | "caucao";
export type StatusDoCaixa = S["StatusCaixaEnum"];
export type FormaDoMovimento = "dinheiro" | "pix" | "cartao" | "cartao_debito" | "cartao_credito" | "boleto";

export type CobrancaDaConta = Omit<S["Cobranca"], "tipo" | "status"> & { tipo: "pix" | "boleto"; status: string };

export type ContaReceber = Omit<S["Conta"], "tipo" | "forma_prevista" | "forma" | "cobranca_aberta"> & {
  tipo: TipoDeConta;
  forma_prevista: FormaPrevista | null;
  forma: FormaDaBaixa | null;
  cobranca_aberta: CobrancaDaConta | null;
};
export type ContaReceberDetalhe = ContaReceber & { historico: HistoricoDaConta[] };
export type HistoricoDaConta = S["HistoricoDaConta"];
export type ValorHoje = S["ValorHoje"];
export type IndicadoresReceber = S["IndicadoresReceber"];
export type ContagensReceber = S["ContagensReceber"];
export type ListaContasReceber = Omit<S["ListaDeContas"], "resultados"> & { resultados: ContaReceber[] };

export type PeriodoReceber = "hoje" | "semana" | "mes";
export type SituacaoReceber = "atrasadas" | "vencem_hoje" | "a_vencer" | "pagas" | "canceladas";
export type FiltroReceber = {
  periodo?: PeriodoReceber;
  situacao?: SituacaoReceber;
  faixa?: FaixaDeAtraso;
  cliente?: number;
  busca?: string;
  ordem?: "vencimento" | "-valor";
};

export type FormaDeRecebimento = S["ReceberFormaEnum"];
export type LancamentoAvulso = Omit<S["Lancamento"], "tipo"> & { tipo: "multa" | "avaria" | "outro" };

export type MovimentoDoCaixa = Omit<S["Movimento"], "forma"> & { forma: FormaDoMovimento };
export type ResumoDoCaixa = S["ResumoCaixa"];
export type FechamentoDoCaixa = S["Fechamento"];
export type Caixa = Omit<S["Caixa"], "aberto_por"> & { aberto_por: S["Ref"] };
/** `GET /caixas/hoje/`: o caixa de hoje da filial, ou a resposta de que ainda não foi aberto. */
export type CaixaDeHoje = Caixa | { caixa: null; pode_abrir: boolean };

export function caixaAberto(r: CaixaDeHoje): r is Caixa {
  return !("caixa" in r);
}

export type CategoriaDaDespesa = S["CategoriaDespesaEnum"];
export type StatusDaDespesa = S["DespesaStatusEnum"];
export type FormaDaDespesa = S["FormaDespesaEnum"];
export type Despesa = S["Despesa"];
export type IndicadoresDespesas = S["IndicadoresDespesas"];
export type ContagensDespesas = S["ContagensDespesas"];
export type ListaDespesas = S["ListaDeDespesas"];
export type FiltroDespesas = { mes?: string; status?: StatusDaDespesa; categoria?: CategoriaDaDespesa; veiculo?: number; busca?: string; cursor?: string };
/** Pedido da exportação das despesas (`FIN-16`, `AUD-07`): o mês e a filial da tela; `filial_id` nulo vale todas. */
export type PedidoDeExportacaoDeDespesas = { mes: string; filial_id: number | null };
export type ExportacaoCriada = S["ExportacaoCriada"];
/** Corpo do `POST /despesas/` (multipart). O gerador deixou `nota` como texto; aqui é o arquivo. */
export type NovaDespesa = Omit<S["DespesaEntrada"], "nota" | "veiculo_id" | "pago_no_caixa"> & { veiculo_id?: number | null; nota?: File | null; pago_no_caixa?: boolean };
export type PagamentoDeDespesa = Omit<S["PagarDespesa"], "comprovante"> & { comprovante?: File | null };
export type PedidoDeAprovacao = S["Pedido"];
export type StatusDoPedido = S["PedidoStatusEnum"];
export type TipoDoPedido = S["PedidoTipoEnum"];
export type IndicadoresAprovacoes = S["IndicadoresDePedidos"];
export type ContagensAprovacoes = S["ContagensDePedidos"];
export type ResumoDoPedido = S["ResumoDoPedido"];
export type FiltroPedidos = { status?: StatusDoPedido; tipo?: TipoDoPedido; minhas?: boolean };
export type ListaPedidos = S["ListaDePedidos"];

/** Corpo de `POST /api/financeiro/contas-receber/renegociar/` (docs/api/financeiro.md). */
export type CorpoDaRenegociacao = { contas: number[]; novas: { vencimento: string; valor_centavos: number }[]; motivo: string };

/** Reembolsos ao cliente (`DEV-02`, docs/api/financeiro.md). Os textos, os indicadores e as ações vêm prontos da API. */
export type Reembolso = S["Reembolso"];
export type StatusDoReembolso = S["ReembolsoStatusEnum"];
export type ListaReembolsos = S["ListaDeReembolsos"];
export type FiltroReembolsos = { status?: StatusDoReembolso | "todos"; periodo?: "hoje" | "semana" | "mes"; busca?: string; cursor?: string };

/** Pendências do pagamento (`AUT-05`, `PLT-12`). */
export type PendenciaPagamento = S["PendenciaPagamento"];
export type StatusDaPendencia = S["PendenciaPagamentoStatusEnum"];
export type AcaoDaPendencia = S["AcaoEnum"];
export type ListaPendencias = S["ListaDePendenciasPagamento"];
export type FiltroPendencias = { status?: StatusDaPendencia | "todas"; periodo?: "mes"; busca?: string; cursor?: string };
