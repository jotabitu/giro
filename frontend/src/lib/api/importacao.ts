// Importação por planilha na API real (docs/api/importacao.md). Só o administrador (e o suporte com "ver e editar").
import { chamar, http } from "./http";
import type { Importacao, LinhaDaImportacao, ModeloEscolhido, NovaImportacao, PreparoDaImportacao, StatusDaLinha, TipoDeImportacao } from "./tipos-importacao";

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

  /** "Corrigir aqui": só os campos corrigidos; a linha volta revalidada. Em veículos, `categoria_id` põe a linha numa categoria só dela, e `null` a faz seguir o modelo de novo (IMP-08). */
  corrigir(id: number, numero: number, dados: Record<string, string>, categoria?: { categoria_id: number | null }): Promise<LinhaDaImportacao> {
    return http.patch(`/api/importacoes/${id}/linhas/${numero}/`, { dados, ...categoria });
  },

  /** IMP-08: a categoria de cada modelo; volta a importação com o bloco `categorias` atualizado. */
  escolherCategorias(id: number, modelos: ModeloEscolhido[]): Promise<Importacao> {
    return http.post(`/api/importacoes/${id}/categorias/`, { modelos });
  },

  /** IMP-08: antes de enviar veículos, a filial (a única ativa ou a escolhida) e se dá para importar. */
  preparo(filial_id?: number): Promise<PreparoDaImportacao> {
    return http.get("/api/importacoes/preparo/", { filial_id });
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
