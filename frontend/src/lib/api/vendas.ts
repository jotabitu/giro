// Vendas na API real (docs/api/vendas.md). Só abre com o recurso `vendas_comissoes` (PLT-12); o vistoriador recebe 403.
// Fase 1a da T-502: lista, detalhe, simular, criar, editar, enviar (só o estado e a data), resposta, pedir aprovação e perder.
import { http } from "./http";
import type { EdicaoDaVenda, FiltroDeVendas, ListaDeVendas, NovaVenda, PropostaDaVenda, SimulacaoDaVenda, VendaDetalhe, VendaEnviada } from "./tipos-vendas";

export const vendasApi = {
  listar(f: FiltroDeVendas = {}): Promise<ListaDeVendas> {
    return http.get("/api/vendas/", {
      origem: f.origem,
      transferencia_pendente: f.transferencia_pendente ? "true" : undefined,
      aba: f.aba,
      status: f.status,
      mes: f.mes,
      veiculo: f.veiculo === undefined ? undefined : String(f.veiculo),
      cursor: f.cursor,
    });
  },

  obter(id: number): Promise<VendaDetalhe> {
    return http.get(`/api/vendas/${id}/`);
  },

  /** A tela chama a cada mudança; não grava (ADR 0005). Preço final, saldo, parcelas, comissão e `precisa_aprovacao` vêm daqui. */
  simular(corpo: PropostaDaVenda & ({ veiculo_id: number } | { venda_id: number })): Promise<SimulacaoDaVenda> {
    return http.post("/api/vendas/simular/", corpo);
  },

  criar(corpo: NovaVenda): Promise<VendaDetalhe> {
    return http.post("/api/vendas/", corpo);
  },

  editar(id: number, corpo: EdicaoDaVenda): Promise<VendaDetalhe> {
    return http.patch(`/api/vendas/${id}/`, corpo);
  },

  /** Interessado → proposta, ou reenvio. Na fase 1a, `email_enviado` é sempre `false` (o e-mail entra na 1c). */
  enviar(id: number): Promise<VendaEnviada> {
    return http.post(`/api/vendas/${id}/enviar/`, {});
  },

  /** Proposta → negociação. A nota vai só para a auditoria. */
  registrarResposta(id: number, nota: string): Promise<VendaDetalhe> {
    return http.post(`/api/vendas/${id}/resposta/`, nota ? { nota } : {});
  },

  pedirAprovacao(id: number, desconto_pct: string, motivo?: string): Promise<VendaDetalhe> {
    return http.post(`/api/vendas/${id}/pedir-aprovacao/`, motivo ? { desconto_pct, motivo } : { desconto_pct });
  },

  /** O motivo é obrigatório (VEN-13). */
  perder(id: number, motivo: string): Promise<VendaDetalhe> {
    return http.post(`/api/vendas/${id}/perder/`, { motivo });
  },
};
