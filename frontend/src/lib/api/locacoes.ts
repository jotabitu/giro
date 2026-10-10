// Locações na API real (docs/api/locacoes.md). A API decide valores e status; aqui só se monta a chamada.
import { chamarComStatus, http } from "./http";
import type {
  EntradaDaLocacao,
  ExtraDeLocacao,
  FiltroLocacoes,
  FormaDevolucaoCancelamento,
  HistoricoDaLocacao,
  ListaLocacoes,
  LocacaoCompleta,
  PedidoDeCancelamento,
  PlanoEspecial,
  SimulacaoDaLocacao,
  SimulacaoDaRenovacao,
  SimulacaoDoCancelamento,
  TrocaCancelada,
  TrocaPedida,
} from "./tipos-locacoes";

type CorpoDeRenovacao = { periodos?: number | null; fim_previsto?: string | null };

export const locacoesApi = {
  extras(): Promise<{ resultados: ExtraDeLocacao[] }> {
    return http.get("/api/extras/", { ativo: true });
  },

  planosEspeciais(): Promise<{ resultados: PlanoEspecial[] }> {
    return http.get("/api/planos-especiais/", { ativo: true });
  },

  simular(e: EntradaDaLocacao): Promise<SimulacaoDaLocacao> {
    return http.post("/api/locacoes/simular/", e);
  },

  criar(e: EntradaDaLocacao): Promise<LocacaoCompleta> {
    return http.post("/api/locacoes/", e);
  },

  atualizar(id: number, e: EntradaDaLocacao): Promise<LocacaoCompleta> {
    return http.patch(`/api/locacoes/${id}/`, e);
  },

  confirmar(id: number, corpo: { primeiro_vencimento?: string | null } = {}): Promise<LocacaoCompleta> {
    return http.post(`/api/locacoes/${id}/confirmar/`, corpo);
  },

  listar(f: FiltroLocacoes = {}): Promise<ListaLocacoes> {
    return http.get("/api/locacoes/", { aba: f.aba, periodicidade: f.periodicidade, veiculo: f.veiculo, cliente: f.cliente, busca: f.busca, ordem: f.ordem, cursor: f.cursor });
  },

  obter(id: number): Promise<LocacaoCompleta> {
    return http.get(`/api/locacoes/${id}/`);
  },

  historico(id: number): Promise<HistoricoDaLocacao> {
    return http.get(`/api/locacoes/${id}/historico/`);
  },

  simularRenovacao(id: number, corpo: CorpoDeRenovacao): Promise<SimulacaoDaRenovacao> {
    return http.post(`/api/locacoes/${id}/renovar/simular/`, corpo);
  },

  renovar(id: number, corpo: CorpoDeRenovacao): Promise<LocacaoCompleta> {
    return http.post(`/api/locacoes/${id}/renovar/`, corpo);
  },

  simularCancelamento(id: number, corpo: { data?: string | null } = {}): Promise<SimulacaoDoCancelamento> {
    return http.post(`/api/locacoes/${id}/cancelamento/simular/`, corpo);
  },

  /** 200 com a locação cancelada, ou 202 quando o cancelamento vira pedido de aprovação (APR-02). */
  async cancelar(
    id: number,
    corpo: { motivo: string; data?: string | null; forma_devolucao: FormaDevolucaoCancelamento },
  ): Promise<{ status: 200; locacao: LocacaoCompleta } | { status: 202; pedido: PedidoDeCancelamento }> {
    const r = await chamarComStatus<LocacaoCompleta | { pedido_aprovacao: PedidoDeCancelamento }>("POST", `/api/locacoes/${id}/cancelar/`, { corpo });
    if (r.status === 202) return { status: 202, pedido: (r.dados as { pedido_aprovacao: PedidoDeCancelamento }).pedido_aprovacao };
    return { status: 200, locacao: r.dados as LocacaoCompleta };
  },

  trocarVeiculo(id: number, corpo: { veiculo_novo_id: number; motivo: string }): Promise<TrocaPedida> {
    return http.post(`/api/locacoes/${id}/trocar-veiculo/`, corpo);
  },

  /** LOC-09: cancela a troca pendente; as vistorias da troca são descartadas e o veículo novo volta a ficar disponível. */
  cancelarTroca(id: number, corpo: { motivo: string }): Promise<TrocaCancelada> {
    return http.post(`/api/locacoes/${id}/trocar-veiculo/cancelar/`, corpo);
  },

  async reenviarContrato(id: number): Promise<void> {
    await http.post(`/api/locacoes/${id}/contrato/reenviar/`);
  },

  pdfDoContrato(id: number): Promise<{ url: string; url_expira_em: string }> {
    return http.get(`/api/locacoes/${id}/contrato/pdf/`);
  },
};
