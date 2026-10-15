// Veículos na API real (docs/api/veiculos.md).
import { http } from "./http";
import type { ListaLocacoes } from "./tipos-locacoes";
import type {
  CategoriaVeiculo,
  DocumentoVeiculo,
  FiltroVeiculos,
  ListaVeiculos,
  LocacoesDoVeiculo,
  ManutencoesDoVeiculo,
  NovoVeiculo,
  TipoVeiculo,
  Veiculo,
  VeiculoDetalhe,
} from "./tipos-frota";

const ROTULO_DOCUMENTO: Record<string, string> = { crlv: "CRLV", seguro: "Seguro", ipva: "IPVA", rastreador: "Rastreador" };

type DocumentoDaApi = { id: number; tipo: string; validade: string | null; situacao: DocumentoVeiculo["situacao"]; dias_para_vencer: number | null };

export const veiculosApi = {
  async categorias(filtro: { filial?: number; tipo_veiculo?: TipoVeiculo } = {}): Promise<CategoriaVeiculo[]> {
    const r = await http.get<{ resultados: (Omit<CategoriaVeiculo, "preco_vigente"> & { preco_vigente?: CategoriaVeiculo["preco_vigente"] | null })[] }>("/api/categorias/", {
      ativo: true,
      filial: filtro.filial,
      tipo_veiculo: filtro.tipo_veiculo,
    });
    // Categoria sem preço vigente (ou sem o preço, como para o vistoriador) não serve para cadastrar nem alugar.
    return r.resultados.filter((c): c is CategoriaVeiculo => c.preco_vigente != null);
  },

  /** O 201 já traz o veículo. Ler a ficha em seguida faria uma falha da leitura passar por falha do cadastro (T-240): quem abre a ficha é a página dela. */
  criar(v: NovoVeiculo): Promise<Veiculo> {
    return http.post<Veiculo>("/api/veiculos/", v);
  },

  registrarKm(id: number, km: number): Promise<Veiculo> {
    return http.post<Veiculo>(`/api/veiculos/${id}/km/`, { km });
  },

  listar(f: FiltroVeiculos = {}): Promise<ListaVeiculos> {
    return http.get<ListaVeiculos>("/api/veiculos/", { status: f.status && f.status !== "todos" ? f.status : undefined, tipo_veiculo: f.tipo_veiculo, busca: f.busca, cursor: f.cursor });
  },

  obter(id: number): Promise<VeiculoDetalhe> {
    return http.get<VeiculoDetalhe>(`/api/veiculos/${id}/`);
  },

  async documentos(id: number): Promise<DocumentoVeiculo[]> {
    const r = await http.get<{ resultados: DocumentoDaApi[] }>(`/api/veiculos/${id}/documentos/`);
    return r.resultados.map((d) => ({ ...d, rotulo: ROTULO_DOCUMENTO[d.tipo] ?? d.tipo }));
  },

  /** `GET /api/locacoes/?veiculo=`: o contrato não traz o total, então ele é o tamanho da lista (até 100). */
  async locacoes(id: number): Promise<LocacoesDoVeiculo> {
    const r = await http.get<ListaLocacoes>("/api/locacoes/", { veiculo: id, ordem: "-inicio", tamanho: 100 });
    const resultados = r.resultados.map((l) => ({
      id: l.id,
      codigo: l.codigo,
      cliente_nome: l.cliente.nome,
      inicio: l.inicio ?? "",
      fim: l.fim_previsto ?? "",
      situacao: { rotulo: l.situacao.rotulo, tom: l.situacao.tom },
    }));
    return { total: resultados.length, resultados: resultados.slice(0, 3) };
  },

  /** O app de manutenção é da fase 2 e não tem rota: a ficha mostra "Nenhuma manutenção registrada". */
  async manutencoes(id: number): Promise<ManutencoesDoVeiculo> {
    void id;
    return { resultados: [] };
  },
};
