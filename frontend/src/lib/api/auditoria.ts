// Auditoria da empresa e exportação na API real (docs/api/auditoria.md). Só o administrador chama.
import { chamar, http } from "./http";
import type { DetalheDoEvento, ExportacaoRecente, FiltroAuditoria, ListaEventos, PedidoDeExportacao, PessoaDaAuditoria, PeriodoDaAuditoria } from "./tipos-auditoria";

export const auditoriaApi = {
  eventos(f: FiltroAuditoria = {}): Promise<ListaEventos> {
    return http.get("/api/auditoria/eventos/", { categoria: f.categoria, ator: f.ator, ator_tipo: f.ator_tipo, periodo: f.periodo, cursor: f.cursor });
  },

  evento(id: number): Promise<DetalheDoEvento> {
    return http.get(`/api/auditoria/eventos/${id}/`);
  },

  async pessoas(periodo?: PeriodoDaAuditoria): Promise<PessoaDaAuditoria[]> {
    return (await http.get<{ resultados: PessoaDaAuditoria[] }>("/api/auditoria/pessoas/", { periodo })).resultados;
  },

  async exportacoes(): Promise<ExportacaoRecente[]> {
    return (await http.get<{ resultados: ExportacaoRecente[] }>("/api/exportacoes/")).resultados;
  },

  exportar(corpo: PedidoDeExportacao): Promise<{ id: number; status: string }> {
    return http.post("/api/exportacoes/", corpo);
  },

  /**
   * O "baixar" exige login (Bearer, que só vive em memória), então um link simples não serve: a tela busca o arquivo
   * com o token, seguindo o 302 para a URL assinada do storage, e entrega o conteúdo ao navegador.
   */
  baixar(id: number): Promise<Blob> {
    return chamar<Blob>("GET", `/api/exportacoes/${id}/baixar/`, { blob: true });
  },
};
