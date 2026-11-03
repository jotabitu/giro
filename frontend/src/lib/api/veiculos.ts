// Veículos na API real (docs/api/veiculos.md).
import { http } from "./http";
import type { ListaLocacoes } from "./tipos-locacoes";
import type {
  CorrecaoDeIdentificacao,
  CrlvDoCadastro,
  LeituraCrlv,
  ModeloDoCatalogo,
  CategoriaVeiculo,
  DocumentoVeiculo,
  NovoDocumentoVeiculo,
  FiltroVeiculos,
  ListaVeiculos,
  LocacoesDoVeiculo,
  ManutencoesDoVeiculo,
  EdicaoVeiculo,
  NovoVeiculo,
  TipoVeiculo,
  Veiculo,
  VeiculoDetalhe,
} from "./tipos-frota";

const ROTULO_DOCUMENTO: Record<string, string> = { crlv: "CRLV", seguro: "Seguro", ipva: "IPVA", rastreador: "Rastreador" };

type DocumentoDaApi = { id: number; tipo: string; ativo?: boolean; arquivo?: DocumentoVeiculo["arquivo"]; validade: string | null; situacao: DocumentoVeiculo["situacao"]; dias_para_vencer: number | null };

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
  criar(v: NovoVeiculo, crlv?: CrlvDoCadastro): Promise<Veiculo> {
    if (!crlv) return http.post<Veiculo>("/api/veiculos/", v);
    const corpo = new FormData();
    for (const [campo, valor] of Object.entries(v)) if (valor !== undefined && valor !== null) corpo.set(campo, String(valor));
    corpo.set("crlv_arquivo", crlv.arquivo);
    corpo.set("crlv_validade", crlv.validade);
    if (crlv.exercicio != null) corpo.set("crlv_exercicio", String(crlv.exercicio));
    corpo.set("leitura", crlv.leitura);
    return http.post<Veiculo>("/api/veiculos/", corpo);
  },

  /** VEI-08: lê o PDF do CRLV-e e devolve o que achou; não grava nada. 400, 422, 429 e 503 trazem a mensagem da API. */
  lerCrlv(arquivo: File): Promise<LeituraCrlv> {
    const corpo = new FormData();
    corpo.set("arquivo", arquivo);
    return http.post<LeituraCrlv>("/api/veiculos/leitura-crlv/", corpo);
  },

  /** O catálogo de marcas e modelos (até 50), para o campo Modelo. */
  async modelos(filtro: { tipo?: TipoVeiculo; marca?: string; busca?: string } = {}): Promise<ModeloDoCatalogo[]> {
    const r = await http.get<{ resultados: ModeloDoCatalogo[] }>("/api/veiculos/modelos/", { tipo: filtro.tipo, marca: filtro.marca || undefined, busca: filtro.busca || undefined });
    return r.resultados;
  },

  /** PATCH (VEI-01): administrador e gerente; a resposta é a ficha completa. */
  atualizar(id: number, v: EdicaoVeiculo): Promise<VeiculoDetalhe> {
    return http.patch<VeiculoDetalhe>(`/api/veiculos/${id}/`, v);
  },

  /** Erro de digitação na placa ou no chassi (administrador). 409 `VEI-01` se colidir com outro veículo. */
  corrigirIdentificacao(id: number, c: CorrecaoDeIdentificacao): Promise<VeiculoDetalhe> {
    return http.post<VeiculoDetalhe>(`/api/veiculos/${id}/corrigir-identificacao/`, c);
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

  /** `GET .../documentos/historico/`: todos os documentos, inclusive os renovados (inativos). */
  async historicoDeDocumentos(id: number): Promise<DocumentoVeiculo[]> {
    const r = await http.get<{ resultados: DocumentoDaApi[] }>(`/api/veiculos/${id}/documentos/historico/`);
    return r.resultados.map((d) => ({ ...d, rotulo: ROTULO_DOCUMENTO[d.tipo] ?? d.tipo }));
  },

  /** `POST .../documentos/` (VEI-03): se já havia um ativo do mesmo tipo, a API o deixa inativo. Administrador e gerente. */
  async enviarDocumento(id: number, d: NovoDocumentoVeiculo): Promise<DocumentoVeiculo> {
    const corpo = new FormData();
    corpo.set("tipo", d.tipo);
    corpo.set("validade", d.validade);
    if (d.exercicio) corpo.set("exercicio", d.exercicio);
    if (d.arquivo) corpo.set("arquivo", d.arquivo);
    const r = await http.post<DocumentoDaApi>(`/api/veiculos/${id}/documentos/`, corpo);
    return { ...r, rotulo: ROTULO_DOCUMENTO[r.tipo] ?? r.tipo };
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
