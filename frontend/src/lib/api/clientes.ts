// Clientes na API real (docs/api/clientes.md).
import { http } from "./http";
import type {
  AnaliseCadastro,
  ClienteCompleto,
  ClienteResumo,
  FiltroClientes,
  DetalheDaLocacaoAtual,
  ListaClientes,
  LocacaoDoCliente,
  LocacoesDoCliente,
  NovoCliente,
  TipoDocumentoCliente,
} from "./tipos-clientes";
import type { LocacaoCompleta, ListaLocacoes } from "./tipos-locacoes";

const EM_ANDAMENTO = new Set(["aguardando_retirada", "ativa", "devolucao_atrasada"]);

function daLinha(l: ListaLocacoes["resultados"][number]): LocacaoDoCliente {
  return {
    id: l.id,
    codigo: l.codigo,
    status: l.status as LocacaoDoCliente["status"],
    veiculo: { id: l.veiculo.id, modelo: l.veiculo.modelo, placa: l.veiculo.placa, tipo: l.veiculo.tipo },
    periodicidade: l.periodicidade,
    inicio: l.inicio ?? "",
    fim_previsto: l.fim_previsto ?? "",
    situacao: l.situacao,
    pago_centavos: l.pagamento?.pago_centavos ?? 0,
  };
}

function doDetalhe(l: LocacaoCompleta): DetalheDaLocacaoAtual {
  const parcelas = (l.parcelas ?? []).filter((p) => p.tipo === "parcela");
  const caucao = (l.parcelas ?? []).find((p) => p.tipo === "caucao");
  return {
    valor_periodo_centavos: l.precos?.valor_periodo_centavos ?? 0,
    caucao_centavos: l.precos?.caucao_centavos ?? 0,
    caucao_em_garantia: caucao?.status === "paga",
    parcelas_pagas: parcelas.filter((p) => p.status === "paga").length,
    parcelas_total: parcelas.length,
  };
}

export const clientesApi = {
  listar(f: FiltroClientes = {}): Promise<ListaClientes> {
    return http.get<ListaClientes>("/api/clientes/", { situacao: f.situacao, busca: f.busca, ordem: f.ordem, cursor: f.cursor });
  },

  obter(id: number): Promise<ClienteResumo | ClienteCompleto> {
    return http.get<ClienteCompleto>(`/api/clientes/${id}/`);
  },

  analisar(corpo: Partial<NovoCliente>): Promise<AnaliseCadastro> {
    return http.post<AnaliseCadastro>("/api/clientes/analisar/", corpo);
  },

  criar(c: NovoCliente): Promise<ClienteCompleto> {
    return http.post<ClienteCompleto>("/api/clientes/", c);
  },

  /** `GET /api/locacoes/?cliente=`: o pago e o tipo do veículo vêm na linha. Só a locação em andamento abre o detalhe, para o preço, as parcelas e a caução. */
  async locacoes(id: number): Promise<LocacoesDoCliente> {
    const lista = await http.get<ListaLocacoes>("/api/locacoes/", { cliente: id, ordem: "-inicio", tamanho: 100 });
    const resultados = lista.resultados.map(daLinha);
    const atual = resultados.find((l) => EM_ANDAMENTO.has(l.status));
    if (atual) atual.detalhe = doDetalhe(await http.get<LocacaoCompleta>(`/api/locacoes/${atual.id}/`));
    return {
      total: resultados.length,
      com_atraso: lista.resultados.filter((l) => l.sinais.pagamento_atrasado || l.status === "devolucao_atrasada").length,
      resultados,
    };
  },

  enviarDocumento(id: number, tipo: TipoDocumentoCliente, arquivo: File): Promise<ClienteCompleto> {
    const corpo = new FormData();
    corpo.set("tipo", tipo);
    corpo.set("arquivo", arquivo);
    return http.post<ClienteCompleto>(`/api/clientes/${id}/documentos/`, corpo);
  },
};
