// Decisão dos pedidos de aprovação (docs/api/aprovacoes.md). Quem pode decidir e o efeito na origem são da API.
import { http } from "./http";
import type { PedidoDeAprovacao } from "./tipos-financeiro";

export const aprovacoesApi = {
  aprovar(id: number, motivo?: string): Promise<PedidoDeAprovacao> {
    return http.post(`/api/aprovacoes/${id}/aprovar/`, motivo ? { motivo } : {});
  },

  /** O motivo é obrigatório (APR-07). */
  recusar(id: number, motivo: string): Promise<PedidoDeAprovacao> {
    return http.post(`/api/aprovacoes/${id}/recusar/`, { motivo });
  },
};
