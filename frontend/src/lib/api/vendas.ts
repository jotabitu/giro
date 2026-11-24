// Vendas na API real (docs/api/vendas.md). Só abre com o recurso `vendas_comissoes` (PLT-12); o vistoriador recebe 403.
// Fase 1a da T-502: lista, detalhe, simular, criar, editar, enviar (só o estado e a data), resposta, pedir aprovação e perder.
// Fase 1b: assinatura (contrato e entrada), link e reenvio do contrato, PDF e transferência no Detran.
import { http } from "./http";
import type { LinkDoContrato } from "./tipos-locacoes";
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

  /** "Preparar assinatura" (VEN-15): o contrato de compra e venda e a conta da entrada, na mesma transação. */
  prepararAssinatura(id: number): Promise<VendaDetalhe> {
    return http.post(`/api/vendas/${id}/assinatura/`, {});
  },

  /** "Cancelar assinatura" (VEN-19): contrato e cobrança da entrada cancelados; a proposta volta a se editar. */
  cancelarAssinatura(id: number): Promise<VendaDetalhe> {
    return http.delete(`/api/vendas/${id}/assinatura/`);
  },

  /** Token novo a cada chamada (T-411, S-15); o anterior deixa de valer. */
  copiarLinkDoContrato(id: number): Promise<LinkDoContrato> {
    return http.post(`/api/vendas/${id}/contrato/link/`, {});
  },

  async reenviarContrato(id: number): Promise<void> {
    await http.post(`/api/vendas/${id}/contrato/reenviar/`, {});
  },

  /** URL de 15 minutos do PDF (o assinado, se houver). */
  pdfDoContrato(id: number): Promise<{ url: string; url_expira_em: string }> {
    return http.get(`/api/vendas/${id}/contrato/pdf/`);
  },

  /** VEN-17: administrador e gerente da filial, na venda `vendida`. */
  registrarTransferencia(id: number, feita_em: string): Promise<VendaDetalhe> {
    return http.post(`/api/vendas/${id}/transferencia/`, { feita_em });
  },
};
