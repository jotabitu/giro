// Movimentações (docs/api/movimentacoes.md): quadro, nova movimentação, paradas, chegada, locais de apoio e as listas de quem leva e quem recebe.
import { http } from "./http";
import type {
  ChegadaNoDestino,
  FiltroDeMovimentacoes,
  FotoDaChegada,
  LocalDeApoio,
  Movimentacao,
  NovaMovimentacao,
  NovoLocalDeApoio,
  PessoaParaEscolher,
  PosicaoDaFotoDaChegada,
  QuadroDeMovimentacoes,
  SaidaDaParada,
} from "./tipos-movimentacoes";

export const movimentacoesApi = {
  /** `GET /api/movimentacoes/quadro/`: quem leva recebe só as dele; a filial padrão é a do seletor do topo. */
  quadro(f: Pick<FiltroDeMovimentacoes, "filial"> = {}): Promise<QuadroDeMovimentacoes> {
    return http.get("/api/movimentacoes/quadro/", { filial: f.filial });
  },

  obter(id: number): Promise<Movimentacao> {
    return http.get(`/api/movimentacoes/${id}/`);
  },

  criar(c: NovaMovimentacao): Promise<Movimentacao> {
    return http.post("/api/movimentacoes/", c);
  },

  /** "Sair agora" de uma agendada: `agendada` → `em_transito`. */
  iniciar(id: number): Promise<Movimentacao> {
    return http.post(`/api/movimentacoes/${id}/iniciar/`, {});
  },

  cancelar(id: number, motivo: string): Promise<Movimentacao> {
    return http.post(`/api/movimentacoes/${id}/cancelar/`, { motivo });
  },

  /** "Cheguei" na parada da `proxima_etapa`: `em_transito` → `no_local`. */
  chegarNaParada(id: number, paradaId: number): Promise<Movimentacao> {
    return http.post(`/api/movimentacoes/${id}/paradas/${paradaId}/chegada/`, {});
  },

  /** Saída da parada com o valor pago e a nota (`MOV-04`): `no_local` → `em_transito`. */
  sairDaParada(id: number, paradaId: number, s: SaidaDaParada): Promise<Movimentacao> {
    const corpo = new FormData();
    corpo.set("valor_pago_centavos", String(s.valor_pago_centavos));
    if (s.nota) corpo.set("nota", s.nota);
    return http.post(`/api/movimentacoes/${id}/paradas/${paradaId}/saida/`, corpo);
  },

  /** Vistoria rápida (`MOV-05`): uma foto por vez; nova foto da mesma posição substitui a anterior. */
  enviarFotoDaChegada(id: number, posicao: PosicaoDaFotoDaChegada, arquivo: File): Promise<FotoDaChegada> {
    const corpo = new FormData();
    corpo.set("posicao", posicao);
    corpo.set("arquivo", arquivo);
    return http.post(`/api/movimentacoes/${id}/chegada/fotos/`, corpo);
  },

  registrarChegada(id: number, c: ChegadaNoDestino): Promise<Movimentacao> {
    return http.post(`/api/movimentacoes/${id}/chegada/`, c);
  },

  locais(f: { busca?: string } = {}): Promise<{ resultados: LocalDeApoio[] }> {
    return http.get("/api/movimentacoes/locais/", { busca: f.busca });
  },

  criarLocal(c: NovoLocalDeApoio): Promise<LocalDeApoio> {
    return http.post("/api/movimentacoes/locais/", c);
  },

  /** `GET /api/movimentacoes/pessoas/?filial=`: quem pode levar, na filial de saída (a do veículo). */
  pessoas(filialId: number): Promise<{ resultados: PessoaParaEscolher[] }> {
    return http.get("/api/movimentacoes/pessoas/", { filial: filialId });
  },

  /** `GET /api/movimentacoes/{id}/recebedores/`: quem pode receber na chegada da transferência (a filial é a de destino). */
  recebedores(id: number): Promise<{ resultados: PessoaParaEscolher[] }> {
    return http.get(`/api/movimentacoes/${id}/recebedores/`);
  },
};
