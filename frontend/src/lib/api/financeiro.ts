// Financeiro na API real (docs/api/financeiro.md). A API decide valor do dia, multa, juros e status; aqui só se monta a chamada.
import { http } from "./http";
import type {
  Caixa,
  CaixaDeHoje,
  CobrancaDaConta,
  ContaReceber,
  ContaReceberDetalhe,
  Despesa,
  ExportacaoCriada,
  FiltroDespesas,
  FiltroReceber,
  FormaDeRecebimento,
  LancamentoAvulso,
  ListaContasReceber,
  ListaDespesas,
  MovimentoDoCaixa,
  NovaDespesa,
  PagamentoDeDespesa,
  PedidoDeExportacaoDeDespesas,
} from "./tipos-financeiro";

export const financeiroApi = {
  listarContas(f: FiltroReceber = {}): Promise<ListaContasReceber> {
    return http.get("/api/financeiro/contas-receber/", { periodo: f.periodo, situacao: f.situacao, faixa: f.faixa, cliente: f.cliente, busca: f.busca, ordem: f.ordem });
  },

  obterConta(id: number): Promise<ContaReceberDetalhe> {
    return http.get(`/api/financeiro/contas-receber/${id}/`);
  },

  lancar(corpo: LancamentoAvulso): Promise<ContaReceber> {
    return http.post("/api/financeiro/contas-receber/", corpo);
  },

  /** Baixa no caixa: o valor enviado tem que ser o `valor_hoje.total_centavos` que a própria API devolveu. */
  receber(id: number, corpo: { forma: FormaDeRecebimento; valor_centavos: number }): Promise<ContaReceber> {
    return http.post(`/api/financeiro/contas-receber/${id}/receber/`, corpo);
  },

  gerarCobranca(id: number, corpo: { tipo: "pix" | "boleto"; vence_em?: string | null; no_caixa?: boolean }): Promise<CobrancaDaConta> {
    return http.post(`/api/financeiro/contas-receber/${id}/cobranca/`, corpo);
  },

  cobrar(id: number): Promise<{ enviadas: number }> {
    return http.post(`/api/financeiro/contas-receber/${id}/cobrar/`, {});
  },

  cobrarEmLote(ids: number[]): Promise<{ enviadas: number }> {
    return http.post("/api/financeiro/contas-receber/cobrar-em-lote/", { ids });
  },

  cancelarConta(id: number, motivo: string): Promise<ContaReceber> {
    return http.post(`/api/financeiro/contas-receber/${id}/cancelar/`, { motivo });
  },

  estornarConta(id: number, motivo: string): Promise<ContaReceber> {
    return http.post(`/api/financeiro/contas-receber/${id}/estornar/`, { motivo });
  },

  caixaDeHoje(): Promise<CaixaDeHoje> {
    return http.get("/api/financeiro/caixas/hoje/");
  },

  abrirCaixa(troco_centavos: number): Promise<Caixa> {
    return http.post("/api/financeiro/caixas/", { troco_centavos });
  },

  movimentos(caixaId: number, tipo?: "entrada" | "saida" | "sangria"): Promise<{ resultados: MovimentoDoCaixa[] }> {
    return http.get(`/api/financeiro/caixas/${caixaId}/movimentos/`, { tipo });
  },

  sangria(caixaId: number, corpo: { valor_centavos: number; descricao: string }): Promise<MovimentoDoCaixa> {
    return http.post(`/api/financeiro/caixas/${caixaId}/sangria/`, corpo);
  },

  fecharCaixa(caixaId: number, corpo: { contado_centavos: number; motivo_diferenca?: string | null }): Promise<Caixa> {
    return http.post(`/api/financeiro/caixas/${caixaId}/fechar/`, corpo);
  },

  listarDespesas(f: FiltroDespesas = {}): Promise<ListaDespesas> {
    return http.get("/api/financeiro/despesas/", { mes: f.mes, status: f.status, categoria: f.categoria, veiculo: f.veiculo, busca: f.busca, cursor: f.cursor });
  },

  obterDespesa(id: number): Promise<Despesa> {
    return http.get(`/api/financeiro/despesas/${id}/`);
  },

  /** Multipart (nota em foto ou PDF). A API decide o estado: até R$ 500 `a_pagar`, acima `aguardando_aprovacao` (FIN-05, APR-03). */
  lancarDespesa(corpo: NovaDespesa): Promise<Despesa> {
    return http.post("/api/financeiro/despesas/", formulario(corpo));
  },

  /** Cria a exportação das despesas do mês e da filial da tela; o link chega por e-mail (`AUD-07`). A busca e a aba não vão no pedido. */
  exportarDespesas(pedido: PedidoDeExportacaoDeDespesas): Promise<ExportacaoCriada> {
    return http.post("/api/exportacoes/", { itens: ["despesas"], formato: "csv", mes: pedido.mes, filial_id: pedido.filial_id });
  },

  /** Anexa a nota depois (`MOV-04`): só na despesa sem nota; com nota, 409 `nota_existente`. */
  anexarNota(id: number, nota: File): Promise<Despesa> {
    return http.post(`/api/financeiro/despesas/${id}/nota/`, formulario({ nota }));
  },

  pagarDespesa(id: number, corpo: PagamentoDeDespesa): Promise<Despesa> {
    return http.post(`/api/financeiro/despesas/${id}/pagar/`, formulario(corpo));
  },
};

/** Campos ausentes ficam fora do multipart; arquivo vai como arquivo. */
function formulario(corpo: object): FormData {
  const f = new FormData();
  for (const [campo, valor] of Object.entries(corpo)) {
    if (valor === undefined || valor === null || valor === "") continue;
    f.append(campo, valor instanceof Blob ? valor : String(valor));
  }
  return f;
}
