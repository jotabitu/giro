// Clientes na API real (docs/api/clientes.md).
import { http } from "./http";
import type {
  AnaliseCadastro,
  ClienteCompleto,
  ClienteResumo,
  FiltroClientes,
  HistoricoDoCliente,
  ListaClientes,
  LocacaoDoCliente,
  LocacoesDoCliente,
  NovoCliente,
  TipoDocumentoCliente,
} from "./tipos-clientes";
import type { LocacaoCompleta, ListaLocacoes } from "./tipos-locacoes";

const SEM_FIM = new Set(["encerrada", "cancelada"]);

function daLocacao(l: LocacaoCompleta): LocacaoDoCliente {
  const parcelas = (l.parcelas ?? []).filter((p) => p.tipo === "parcela");
  const caucao = (l.parcelas ?? []).find((p) => p.tipo === "caucao");
  return {
    id: l.id,
    codigo: l.codigo,
    status: l.status as LocacaoDoCliente["status"],
    // O contrato de locações não traz o tipo do veículo; a ficha só usa para o ícone.
    veiculo: { id: l.veiculo.id, modelo: l.veiculo.modelo, placa: l.veiculo.placa, tipo_veiculo: "moto" },
    periodicidade: l.periodicidade,
    inicio: l.inicio ?? "",
    fim_previsto: l.fim_previsto ?? "",
    situacao: l.situacao,
    pago_centavos: l.total_pago_centavos ?? 0,
    pago_detalhe: "",
    valor_periodo_centavos: l.precos?.valor_periodo_centavos ?? 0,
    caucao_centavos: l.precos?.caucao_centavos ?? 0,
    caucao_em_garantia: !SEM_FIM.has(l.status) && caucao?.status === "paga",
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

  /** `GET /api/locacoes/?cliente=` mais o detalhe de cada uma, de onde saem o pago, a caução e as parcelas. */
  async locacoes(id: number): Promise<LocacoesDoCliente> {
    const lista = await http.get<ListaLocacoes>("/api/locacoes/", { cliente: id, ordem: "-inicio", tamanho: 100 });
    const detalhes = await Promise.all(lista.resultados.map((l) => http.get<LocacaoCompleta>(`/api/locacoes/${l.id}/`)));
    return {
      total: lista.resultados.length,
      com_atraso: lista.resultados.filter((l) => l.sinais.pagamento_atrasado || l.status === "devolucao_atrasada").length,
      resultados: detalhes.map(daLocacao),
    };
  },

  /** Não existe rota de linha do tempo do cliente (a auditoria é só leitura da plataforma): a seção vem vazia. */
  async historico(id: number): Promise<HistoricoDoCliente> {
    void id;
    return { resultados: [] };
  },

  enviarDocumento(id: number, tipo: TipoDocumentoCliente, arquivo: File): Promise<ClienteCompleto> {
    const corpo = new FormData();
    corpo.set("tipo", tipo);
    corpo.set("arquivo", arquivo);
    return http.post<ClienteCompleto>(`/api/clientes/${id}/documentos/`, corpo);
  },
};
