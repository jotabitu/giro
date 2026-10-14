// Importação por planilha na API real (docs/api/importacao.md). Só o administrador (e o suporte com "ver e editar").
import { chamar, http } from "./http";
import type { Importacao, LinhaDaImportacao, NovaImportacao, StatusDaLinha, TipoDeImportacao } from "./tipos-importacao";

export const importacaoApi = {
  /** Importações dos últimos 30 dias. */
  async listar(): Promise<Importacao[]> {
    return (await http.get<{ resultados: Importacao[] }>("/api/importacoes/")).resultados;
  },

  obter(id: number): Promise<Importacao> {
    return http.get(`/api/importacoes/${id}/`);
  },

  /** 202: a importação nasce `validando`; a validação roda numa task e a tela acompanha. */
  enviar(corpo: NovaImportacao): Promise<Importacao> {
    const f = new FormData();
    f.append("tipo", corpo.tipo);
    f.append("arquivo", corpo.arquivo);
    if (corpo.filial_id !== undefined) f.append("filial_id", String(corpo.filial_id));
    return http.post("/api/importacoes/", f);
  },

  async linhas(id: number, status?: StatusDaLinha): Promise<LinhaDaImportacao[]> {
    return (await http.get<{ resultados: LinhaDaImportacao[] }>(`/api/importacoes/${id}/linhas/`, { status })).resultados;
  },

  /** "Corrigir aqui": só os campos corrigidos; a linha volta revalidada. */
  corrigir(id: number, numero: number, dados: Record<string, string>): Promise<LinhaDaImportacao> {
    return http.patch(`/api/importacoes/${id}/linhas/${numero}/`, { dados });
  },

  ignorar(id: number, numero: number): Promise<LinhaDaImportacao> {
    return http.post(`/api/importacoes/${id}/linhas/${numero}/ignorar/`, {});
  },

  importar(id: number): Promise<Importacao> {
    return http.post(`/api/importacoes/${id}/importar/`, {});
  },

  cancelar(id: number): Promise<Importacao> {
    return http.post(`/api/importacoes/${id}/cancelar/`, {});
  },

  /** A planilha modelo exige login: a tela busca o arquivo com o token e entrega ao navegador. */
  modelo(tipo: TipoDeImportacao): Promise<Blob> {
    return chamar<Blob>("GET", "/api/importacoes/modelo/", { query: { tipo }, blob: true });
  },
};
