// Filiais na API real (docs/api/filiais.md): só o seletor do topo do menu.
import { chamar, http } from "./http";
import type { CepEncontrado, CorpoDaFilial, FeriadoDaFilial, FeriadoNovo, FilialDetalhada, ListaFiliais, MinhasFiliais, SugestaoDeFeriado } from "./tipos";

export const filiaisApi = {
  /** As filiais ativas da pessoa e se ela pode escolher "Todas as filiais" (USR-07). */
  minhas(): Promise<MinhasFiliais> {
    return chamar<MinhasFiliais>("GET", "/api/filiais/minhas/", { semFilial: true });
  },

  /** Administrador: todas as filiais da empresa, com plano e indicadores (docs/api/filiais.md). */
  listar(f: { ativo?: boolean; busca?: string; cursor?: string } = {}): Promise<ListaFiliais> {
    return http.get("/api/filiais/", { ativo: f.ativo === undefined ? undefined : String(f.ativo), busca: f.busca, cursor: f.cursor });
  },

  obter(id: number): Promise<FilialDetalhada> {
    return http.get(`/api/filiais/${id}/`);
  },

  criar(corpo: CorpoDaFilial): Promise<FilialDetalhada> {
    return http.post("/api/filiais/", corpo);
  },

  /** `endereco`, `contato` e `horario` são trocados inteiros quando enviados. */
  alterar(id: number, corpo: Partial<Omit<CorpoDaFilial, "matriz">>): Promise<FilialDetalhada> {
    return http.patch(`/api/filiais/${id}/`, corpo);
  },

  tornarMatriz(id: number): Promise<FilialDetalhada> {
    return http.post(`/api/filiais/${id}/tornar-matriz/`, {});
  },

  desativar(id: number, motivo: string): Promise<FilialDetalhada> {
    return http.post(`/api/filiais/${id}/desativar/`, { motivo });
  },

  reativar(id: number, motivo: string): Promise<FilialDetalhada> {
    return http.post(`/api/filiais/${id}/reativar/`, { motivo });
  },

  async feriados(id: number, ano: number): Promise<FeriadoDaFilial[]> {
    return (await http.get<{ resultados: FeriadoDaFilial[] }>(`/api/filiais/${id}/feriados/`, { ano })).resultados;
  },

  async sugestoesDeFeriados(id: number, ano: number): Promise<SugestaoDeFeriado[]> {
    return (await http.get<{ resultados: SugestaoDeFeriado[] }>(`/api/filiais/${id}/feriados/sugestoes/`, { ano })).resultados;
  },

  async confirmarFeriados(id: number, feriados: FeriadoNovo[]): Promise<FeriadoDaFilial[]> {
    return (await http.post<{ resultados: FeriadoDaFilial[] }>(`/api/filiais/${id}/feriados/`, { feriados })).resultados;
  },

  removerFeriado(id: number, feriadoId: number): Promise<void> {
    return http.post(`/api/filiais/${id}/feriados/${feriadoId}/remover/`, {});
  },

  /** Preenche rua, bairro e cidade pelo CEP; 404 `cep_nao_encontrado` deixa o endereço à mão. */
  cep(cep: string): Promise<CepEncontrado> {
    return http.get(`/api/enderecos/cep/${cep}/`);
  },
};
