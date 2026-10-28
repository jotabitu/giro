// Modelos de contrato na API real (docs/api/contratos.md, "Modelos"). Só o administrador mexe (IMP-04, S-09, LOC-15).
import { http } from "./http";
import type { CorpoDaEdicaoDoModelo, CorpoDoNovoModelo, MarcadorDeContrato, ModeloDeContrato, ModeloDeContratoDaLista, ModeloProntoDeContrato } from "./tipos-contratos";

export const modelosContratoApi = {
  async listar(): Promise<ModeloDeContratoDaLista[]> {
    return (await http.get<{ resultados: ModeloDeContratoDaLista[] }>("/api/contratos/modelos/")).resultados;
  },

  /** Com o texto, os marcadores usados e as versões. */
  obter(id: number): Promise<ModeloDeContrato> {
    return http.get(`/api/contratos/modelos/${id}/`);
  },

  /** Os campos automáticos da lista fechada (S-09), com rótulo e exemplo. */
  async marcadores(): Promise<MarcadorDeContrato[]> {
    return (await http.get<{ resultados: MarcadorDeContrato[] }>("/api/contratos/marcadores/")).resultados;
  },

  async prontos(): Promise<ModeloProntoDeContrato[]> {
    return (await http.get<{ resultados: ModeloProntoDeContrato[] }>("/api/contratos/modelos-prontos/")).resultados;
  },

  /** `{ nome, a_partir_de }` cria o rascunho com o texto pronto; `{ nome, finalidade, texto }` cria com o texto enviado. 400 `marcador_invalido`. */
  criar(corpo: CorpoDoNovoModelo): Promise<ModeloDeContrato> {
    return http.post("/api/contratos/modelos/", corpo);
  },

  /** Editar um modelo publicado cria o rascunho da versão seguinte; a publicada não muda. */
  alterar(id: number, corpo: CorpoDaEdicaoDoModelo): Promise<ModeloDeContrato> {
    return http.patch(`/api/contratos/modelos/${id}/`, corpo);
  },

  /** "Ver com dados reais": HTML renderizado e sanitizado pela API, sem gerar PDF. Sem `locacaoId`, usa os dados de exemplo. */
  async previa(id: number, locacaoId?: number): Promise<string> {
    return (await http.post<{ html: string }>(`/api/contratos/modelos/${id}/previa/`, locacaoId ? { locacao_id: locacaoId } : {})).html;
  },

  publicar(id: number): Promise<ModeloDeContrato> {
    return http.post(`/api/contratos/modelos/${id}/publicar/`, {});
  },

  /** 422 `IMP-04` se for o último modelo de locação publicado. */
  arquivar(id: number): Promise<ModeloDeContrato> {
    return http.post(`/api/contratos/modelos/${id}/arquivar/`, {});
  },
};
