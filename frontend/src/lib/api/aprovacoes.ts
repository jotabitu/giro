// Decisão dos pedidos de aprovação (docs/api/aprovacoes.md). Quem pode decidir e o efeito na origem são da API.
import { http } from "./http";
import type { FiltroPedidos, ListaPedidos, PedidoDeAprovacao } from "./tipos-financeiro";

export const aprovacoesApi = {
  /** Os pedidos que a pessoa decide na filial do `X-Filial` (ou, com `minhas`, os que ela fez). */
  listar(f: FiltroPedidos = {}): Promise<ListaPedidos> {
    return http.get("/api/aprovacoes/", { status: f.status, tipo: f.tipo, minhas: f.minhas ? "true" : undefined });
  },

  aprovar(id: number, motivo?: string): Promise<PedidoDeAprovacao> {
    return http.post(`/api/aprovacoes/${id}/aprovar/`, motivo ? { motivo } : {});
  },

  /** O motivo é obrigatório (APR-07). */
  recusar(id: number, motivo: string): Promise<PedidoDeAprovacao> {
    return http.post(`/api/aprovacoes/${id}/recusar/`, { motivo });
  },

  /** Quem pediu desiste do próprio pedido. */
  cancelar(id: number): Promise<PedidoDeAprovacao> {
    return http.post(`/api/aprovacoes/${id}/cancelar/`, {});
  },
};
