// Vistorias, devolução e acerto na API real (docs/api/vistorias.md).
import { http } from "./http";
import type {
  AgendaDoDia,
  AvariaAberta,
  DevolucaoCompleta,
  DiaDaAgenda,
  EdicaoDaVistoria,
  FormaDevolucaoAcerto,
  FotoDaVistoria,
  NovaAvaria,
  NovoItemDoAcerto,
  PosicaoFoto,
  Vistoria,
} from "./tipos-vistorias";

export const vistoriasApi = {
  /** 201 com o rascunho, ou 200 com o que já existe. */
  iniciarSaida(locacaoId: number): Promise<Vistoria> {
    return http.post(`/api/locacoes/${locacaoId}/vistorias/`, { tipo: "saida" });
  },

  obter(id: number): Promise<Vistoria> {
    return http.get(`/api/vistorias/${id}/`);
  },

  editar(id: number, patch: EdicaoDaVistoria): Promise<Vistoria> {
    return http.patch(`/api/vistorias/${id}/`, patch);
  },

  enviarFoto(id: number, posicao: PosicaoFoto, arquivo: File): Promise<FotoDaVistoria> {
    const corpo = new FormData();
    corpo.set("posicao", posicao);
    corpo.set("arquivo", arquivo);
    return http.post(`/api/vistorias/${id}/fotos/`, corpo);
  },

  /** A API devolve a avaria criada; a tela trabalha com a vistoria inteira, então ela é lida de novo. */
  async registrarAvaria(id: number, a: NovaAvaria): Promise<Vistoria> {
    await http.post(`/api/vistorias/${id}/avarias/`, { vai_para_oficina: false, ...a });
    return vistoriasApi.obter(id);
  },

  async removerAvaria(id: number, avariaId: number): Promise<Vistoria> {
    await http.delete(`/api/vistorias/${id}/avarias/${avariaId}/`);
    return vistoriasApi.obter(id);
  },

  concluir(id: number): Promise<Vistoria> {
    return http.post(`/api/vistorias/${id}/concluir/`);
  },

  corrigir(id: number, corpo: { motivo: string }): Promise<Vistoria> {
    return http.post(`/api/vistorias/${id}/corrigir/`, corpo);
  },

  agenda(dia: DiaDaAgenda = "hoje"): Promise<AgendaDoDia> {
    return http.get("/api/vistorias/agenda/", { dia });
  },

  avarias(): Promise<{ resultados: AvariaAberta[] }> {
    return http.get("/api/vistorias/avarias/");
  },

  // ---- Devolução --------------------------------------------------------------------------------------------------

  /** 201 com a devolução e a chegada em rascunho, ou 200 com a que já existe. */
  abrirDevolucao(locacaoId: number): Promise<DevolucaoCompleta> {
    return http.post(`/api/locacoes/${locacaoId}/devolucao/`);
  },

  obterDevolucao(id: number): Promise<DevolucaoCompleta> {
    return http.get(`/api/devolucoes/${id}/`);
  },

  definirForma(id: number, forma: FormaDevolucaoAcerto): Promise<DevolucaoCompleta> {
    return http.patch(`/api/devolucoes/${id}/acerto/`, { forma_devolucao: forma });
  },

  adicionarItem(id: number, item: NovoItemDoAcerto): Promise<DevolucaoCompleta> {
    return http.post(`/api/devolucoes/${id}/acerto/itens/`, item);
  },

  editarItem(id: number, itemId: number, patch: { descricao?: string; valor_centavos?: number }): Promise<DevolucaoCompleta> {
    return http.patch(`/api/devolucoes/${id}/acerto/itens/${itemId}/`, patch);
  },

  async removerItem(id: number, itemId: number): Promise<DevolucaoCompleta> {
    await http.delete(`/api/devolucoes/${id}/acerto/itens/${itemId}/`);
    return vistoriasApi.obterDevolucao(id);
  },

  encerrar(id: number): Promise<DevolucaoCompleta> {
    return http.post(`/api/devolucoes/${id}/encerrar/`);
  },

  recibo(id: number): Promise<{ url: string; url_expira_em: string }> {
    return http.get(`/api/devolucoes/${id}/recibo/`);
  },

  async reenviarRecibo(id: number): Promise<void> {
    await http.post(`/api/devolucoes/${id}/recibo/reenviar/`);
  },
};
