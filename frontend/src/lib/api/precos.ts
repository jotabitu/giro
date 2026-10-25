// Tabelas de preço na API real (docs/api/veiculos.md "Categorias e preços" e "Extras", docs/api/locacoes.md "Planos especiais").
// Só o administrador muda; os outros perfis leem pelas rotas de escolha (`veiculos.categorias`, `locacoes.extras`).
import { http } from "./http";
import type {
  CategoriaDePreco,
  CorpoDaCategoria,
  CorpoDoExtra,
  CorpoDoPlanoEspecial,
  CorpoDoPrecoComData,
  ExtraDePreco,
  MudancaDePreco,
  PlanoEspecialDePreco,
  PrecoDoHistorico,
  PrecoGravado,
} from "./tipos-precos";

export const precosApi = {
  /** `filial` traz as categorias da empresa mais as dessa filial; sem ela, todas. `ativo: false` mostra as desativadas. */
  async categorias(f: { filial?: number; ativo?: boolean } = {}): Promise<CategoriaDePreco[]> {
    return (await http.get<{ resultados: CategoriaDePreco[] }>("/api/categorias/", { filial: f.filial, ativo: f.ativo === undefined ? undefined : String(f.ativo) })).resultados;
  },

  criarCategoria(corpo: CorpoDaCategoria): Promise<CategoriaDePreco> {
    return http.post("/api/categorias/", corpo);
  },

  alterarCategoria(id: number, corpo: Partial<Omit<CorpoDaCategoria, "preco">>): Promise<CategoriaDePreco> {
    return http.patch(`/api/categorias/${id}/`, corpo);
  },

  desativarCategoria(id: number): Promise<CategoriaDePreco> {
    return http.post(`/api/categorias/${id}/desativar/`, {});
  },

  reativarCategoria(id: number): Promise<CategoriaDePreco> {
    return http.post(`/api/categorias/${id}/reativar/`, {});
  },

  /** Histórico de uma categoria (LOC-15), do mais novo ao mais velho. */
  async historicoDaCategoria(id: number): Promise<PrecoDoHistorico[]> {
    return (await http.get<{ resultados: PrecoDoHistorico[] }>(`/api/categorias/${id}/precos/`)).resultados;
  },

  /** Preço novo a partir de `vigente_desde` (padrão: hoje). 409 `preco_ja_definido` se a data já tem preço. */
  definirPreco(id: number, corpo: CorpoDoPrecoComData): Promise<PrecoGravado> {
    return http.post(`/api/categorias/${id}/precos/`, corpo);
  },

  /** Troca um preço agendado para o futuro; 409 `preco_ja_vigente` se a data já chegou. */
  trocarPrecoAgendado(id: number, vigenteDesde: string, corpo: CorpoDoPrecoComData): Promise<PrecoGravado> {
    return http.put(`/api/categorias/${id}/precos/${vigenteDesde}/`, corpo);
  },

  /** Todas as mudanças de preço da empresa ("Histórico de preços"). */
  async historico(): Promise<MudancaDePreco[]> {
    return (await http.get<{ resultados: MudancaDePreco[] }>("/api/precos/historico/")).resultados;
  },

  async extras(f: { ativo?: boolean } = {}): Promise<ExtraDePreco[]> {
    return (await http.get<{ resultados: ExtraDePreco[] }>("/api/extras/", { ativo: f.ativo === undefined ? undefined : String(f.ativo) })).resultados;
  },

  criarExtra(corpo: CorpoDoExtra): Promise<ExtraDePreco> {
    return http.post("/api/extras/", corpo);
  },

  alterarExtra(id: number, corpo: Partial<CorpoDoExtra>): Promise<ExtraDePreco> {
    return http.patch(`/api/extras/${id}/`, corpo);
  },

  desativarExtra(id: number): Promise<ExtraDePreco> {
    return http.post(`/api/extras/${id}/desativar/`, {});
  },

  /** `ativo: "todos"` traz também os desativados. */
  async planosEspeciais(f: { ativo?: boolean | "todos" } = {}): Promise<PlanoEspecialDePreco[]> {
    return (await http.get<{ resultados: PlanoEspecialDePreco[] }>("/api/planos-especiais/", { ativo: f.ativo === undefined ? undefined : String(f.ativo) })).resultados;
  },

  criarPlanoEspecial(corpo: CorpoDoPlanoEspecial): Promise<PlanoEspecialDePreco> {
    return http.post("/api/planos-especiais/", corpo);
  },

  alterarPlanoEspecial(id: number, corpo: Partial<CorpoDoPlanoEspecial>): Promise<PlanoEspecialDePreco> {
    return http.patch(`/api/planos-especiais/${id}/`, corpo);
  },

  desativarPlanoEspecial(id: number): Promise<PlanoEspecialDePreco> {
    return http.post(`/api/planos-especiais/${id}/desativar/`, {});
  },
};
