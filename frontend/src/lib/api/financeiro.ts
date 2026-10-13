// Financeiro na API real (docs/api/financeiro.md). A API decide valor do dia, multa, juros e status; aqui só se monta a chamada.
import { http } from "./http";
import type {
  Caixa,
  CaixaDeHoje,
  CobrancaDaConta,
  ContaReceber,
  ContaReceberDetalhe,
  FiltroReceber,
  FormaDeRecebimento,
  LancamentoAvulso,
  ListaContasReceber,
  MovimentoDoCaixa,
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
};
