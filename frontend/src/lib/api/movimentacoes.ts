// PROVISÓRIO (T-289): camada das Movimentações com os dados de exemplo do contrato (docs/api/movimentacoes.md, seed de 07 out),
// porque as rotas só existem depois da T-288 (backend). A tela chama estes métodos como chamaria a API; quem decide
// (ações, resumo, rota, mensagens) é "a API", aqui simulada. Quando a T-288 entregar: trocar o corpo de cada método por
// `http.get/post(...)` nas rotas do contrato, usar os tipos gerados e apagar a simulação. Nada aqui vale como regra de negócio.
import { ErroApi } from "./tipos";
import type {
  ChegadaNoDestino,
  ColunaDoQuadro,
  FiltroDeMovimentacoes,
  FotoDaChegada,
  LinhaDaMovimentacao,
  LocalDeApoio,
  Movimentacao,
  NovaMovimentacao,
  NovoLocalDeApoio,
  PosicaoDaFotoDaChegada,
  QuadroDeMovimentacoes,
  StatusDaMovimentacao,
} from "./tipos-movimentacoes";

const SEM_ACOES = { editar: false, iniciar: false, cancelar: false, chegar_parada: false, sair_parada: false, registrar_chegada: false };
const CENTRO = { id: 1, nome: "Filial Centro" };
const CAUCAIA = { id: 2, nome: "Filial Caucaia" };
const JOAO = { id: 4, nome: "João Silva" };
const LAVA: LocalDeApoio = { id: 3, nome: "Lava Rápido Aldeota", tipo: "lava_jato", ativo: true };
const OFICINA: LocalDeApoio = { id: 5, nome: "Moto Peças CE", tipo: "oficina", ativo: true };
const LOCAIS: LocalDeApoio[] = [LAVA, OFICINA, { id: 6, nome: "Despachante Silva", tipo: "despachante", ativo: true }];
const VEICULOS: Record<number, { placa: string; modelo: string }> = {
  501: { placa: "SAK1D39", modelo: "Honda CG 160 Fan" },
  503: { placa: "PMZ3E17", modelo: "Honda Pop 110i" },
};
/** Quem pode levar e quem pode receber: o contrato não tem rota para estas escolhas (anotado no handoff da T-289). */
const PESSOAS = [
  { id: 4, nome: "João Silva", filial_id: 1 },
  { id: 7, nome: "Bruna Alves", filial_id: 1 },
  { id: 9, nome: "Paulo Lima", filial_id: 2 },
];

const ROTULOS: Record<ColunaDoQuadro["status"], string> = { agendada: "Agendadas", em_transito: "Em trânsito", no_local: "No local de apoio", concluida: "Concluídas" };

function semente(): { lista: Movimentacao[]; resumos: Record<number, string> } {
  const mov1: Movimentacao = {
    id: 1,
    codigo: "MOV-0001",
    status: "concluida",
    veiculo: { id: 501, placa: "SAK1D39", modelo: "Honda CG 160 Fan", status: "disponivel" },
    filial_saida: CENTRO,
    destino: CENTRO,
    transferencia: false,
    rota: "Centro → Lava Rápido Aldeota → Centro",
    levado_por: JOAO,
    agendada_para: null,
    iniciada_em: "2026-10-07T10:20:00Z",
    concluida_em: "2026-10-07T11:30:00Z",
    duracao_minutos: 70,
    vistoria_rapida: false,
    km_saida: 3100,
    paradas: [{ id: 10, ordem: 1, local: LAVA, servico: "Lavagem completa", categoria: "outros", valor_previsto_centavos: 3500, chegou_em: "2026-10-07T10:35:00Z", saiu_em: "2026-10-07T11:10:00Z", valor_pago_centavos: 3500, despesa: { id: 76, status: "a_pagar", sem_nota: false } }],
    proxima_etapa: null,
    chegada: { km: 3112, combustivel: null, recebido_por: null, fotos: [] },
    custo_centavos: 3500,
    acoes: SEM_ACOES,
  };
  const mov2: Movimentacao = {
    id: 2,
    codigo: "MOV-0002",
    status: "em_transito",
    veiculo: { id: 501, placa: "SAK1D39", modelo: "Honda CG 160 Fan", status: "em_movimentacao" },
    filial_saida: CENTRO,
    destino: CAUCAIA,
    transferencia: true,
    categoria_destino: { id: 7, nome: "Street 150–160" },
    rota: "Centro → Lava Rápido Aldeota → Filial Caucaia",
    levado_por: JOAO,
    agendada_para: null,
    iniciada_em: "2026-10-07T13:02:00Z",
    concluida_em: null,
    duracao_minutos: null,
    vistoria_rapida: true,
    km_saida: 3120,
    paradas: [{ id: 11, ordem: 1, local: LAVA, servico: "Lavagem completa", categoria: "outros", valor_previsto_centavos: 3500, chegou_em: "2026-10-07T13:15:00Z", saiu_em: "2026-10-07T13:58:00Z", valor_pago_centavos: 3500, despesa: { id: 77, status: "a_pagar", sem_nota: false } }],
    proxima_etapa: "destino",
    chegada: null,
    fotos_chegada: [
      { posicao: "frente", url: "/exemplo/frente.jpg", url_expira_em: "2026-10-07T15:00:00Z" },
      { posicao: "lado_direito", url: "/exemplo/direita.jpg", url_expira_em: "2026-10-07T15:00:00Z" },
    ],
    custo_centavos: 3500,
    acoes: { ...SEM_ACOES, registrar_chegada: true },
  };
  const mov3: Movimentacao = {
    id: 3,
    codigo: "MOV-0003",
    status: "agendada",
    veiculo: { id: 503, placa: "PMZ3E17", modelo: "Honda Pop 110i", status: "disponivel" },
    filial_saida: CENTRO,
    destino: CENTRO,
    transferencia: false,
    rota: "Centro → Moto Peças CE → Centro",
    levado_por: JOAO,
    agendada_para: "2026-10-08T11:00:00Z",
    iniciada_em: null,
    concluida_em: null,
    duracao_minutos: null,
    vistoria_rapida: false,
    km_saida: null,
    paradas: [{ id: 12, ordem: 1, local: OFICINA, servico: "Revisão dos freios", categoria: "manutencao", valor_previsto_centavos: 12000, chegou_em: null, saiu_em: null, valor_pago_centavos: null, despesa: null }],
    proxima_etapa: null,
    chegada: null,
    custo_centavos: 0,
    acoes: { ...SEM_ACOES, editar: true, iniciar: true, cancelar: true },
  };
  return { lista: [mov1, mov2, mov3], resumos: { 1: "hoje 08:30 · 1 h 10 min", 2: "saiu 10:02 · 1 parada", 3: "amanhã 08:00" } };
}

let { lista, resumos } = semente();
let locais: LocalDeApoio[] = [...LOCAIS];
let proximoId = 4;
let proximaParada = 13;

/** Só para os testes: volta ao seed. */
export function reiniciarMovimentacoesDeExemplo() {
  ({ lista, resumos } = semente());
  locais = [...LOCAIS];
  proximoId = 4;
  proximaParada = 13;
}

const copia = <T>(x: T): T => structuredClone(x);
const achar = (id: number): Movimentacao => {
  const m = lista.find((x) => x.id === id);
  if (!m) throw new ErroApi(404, "nao_encontrada", "Movimentação não encontrada.");
  return m;
};
const transicao = (m: Movimentacao, acao: string, para: StatusDaMovimentacao) => new ErroApi(409, "transicao_movimentacao", `Não é possível ${acao} uma movimentação ${m.status.replace("_", " ")}`, { de: m.status, para });
const textoDeParadas = (n: number) => `${n} ${n === 1 ? "parada" : "paradas"}`;

function linha(m: Movimentacao): LinhaDaMovimentacao {
  const { paradas, chegada, ...resto } = m;
  void chegada;
  return { ...copia(resto), paradas_total: paradas.length, resumo: resumos[m.id] ?? m.rota };
}

function filtrar(f: FiltroDeMovimentacoes): Movimentacao[] {
  const busca = f.busca?.trim().toLowerCase();
  return lista.filter((m) => (!busca || [m.codigo, m.veiculo.placa, m.veiculo.modelo].some((t) => t.toLowerCase().includes(busca))) && (!f.filial || m.filial_saida.id === f.filial));
}

/** Efeitos de sair da filial: primeira etapa e botões da movimentação em trânsito. */
function sair(m: Movimentacao) {
  m.status = "em_transito";
  m.iniciada_em = new Date().toISOString();
  m.km_saida = 3120;
  m.veiculo = { ...m.veiculo, status: "em_movimentacao" };
  m.proxima_etapa = m.paradas.length ? `parada:${m.paradas[0]?.id}` : "destino";
  m.acoes = { ...SEM_ACOES, chegar_parada: m.paradas.length > 0, registrar_chegada: m.paradas.length === 0 };
  resumos[m.id] = `saiu agora · ${textoDeParadas(m.paradas.length)}`;
}

export const movimentacoesApi = {
  async quadro(f: FiltroDeMovimentacoes = {}): Promise<QuadroDeMovimentacoes> {
    const itens = filtrar(f);
    const colunas = (Object.keys(ROTULOS) as ColunaDoQuadro["status"][]).map((status) => {
      const doStatus = itens.filter((m) => m.status === status).map(linha);
      return { status, rotulo: ROTULOS[status], total: doStatus.length, itens: doStatus };
    });
    return { colunas };
  },

  async obter(id: number): Promise<Movimentacao> {
    return copia(achar(id));
  },

  async criar(c: NovaMovimentacao): Promise<Movimentacao> {
    const aberta = lista.find((m) => m.veiculo.id === c.veiculo_id && ["agendada", "em_transito", "no_local"].includes(m.status));
    if (aberta) throw new ErroApi(409, "MOV-03", `O veículo já está na ${aberta.codigo}.`, { movimentacao_id: aberta.id });
    const id = proximoId++;
    const destino = c.destino_filial_id === CAUCAIA.id ? CAUCAIA : CENTRO;
    const m: Movimentacao = {
      id,
      codigo: `MOV-${String(id).padStart(4, "0")}`,
      status: "agendada",
      veiculo: { id: c.veiculo_id, ...(VEICULOS[c.veiculo_id] ?? { placa: "SAK1D39", modelo: "Honda CG 160 Fan" }), status: "disponivel" },
      filial_saida: CENTRO,
      destino,
      transferencia: destino.id !== CENTRO.id,
      rota: "",
      levado_por: PESSOAS.find((p) => p.id === c.levado_por_id) ?? JOAO,
      agendada_para: c.agendada_para,
      iniciada_em: null,
      concluida_em: null,
      duracao_minutos: null,
      vistoria_rapida: destino.id !== CENTRO.id || c.vistoria_rapida,
      km_saida: null,
      paradas: c.paradas.map((p, i) => {
        const local = locais.find((l) => l.id === p.local_id) ?? LAVA;
        return {
        id: proximaParada++,
        ordem: i + 1,
        local,
        servico: p.servico,
        categoria: p.categoria ?? (local.tipo === "oficina" ? "manutencao" : "outros"),
        valor_previsto_centavos: p.valor_previsto_centavos,
        chegou_em: null,
        saiu_em: null,
        valor_pago_centavos: null,
        despesa: null,
        };
      }),
      proxima_etapa: null,
      chegada: null,
      custo_centavos: 0,
      acoes: { ...SEM_ACOES, editar: true, iniciar: true, cancelar: true },
    };
    m.rota = [m.filial_saida.nome, ...m.paradas.map((p) => p.local.nome), m.destino.nome].join(" → ");
    resumos[id] = "agendada";
    if (c.sair_agora) sair(m);
    lista = [...lista, m];
    return copia(m);
  },

  async iniciar(id: number): Promise<Movimentacao> {
    const m = achar(id);
    if (m.status !== "agendada") throw transicao(m, "iniciar", "em_transito");
    sair(m);
    return copia(m);
  },

  async cancelar(id: number, motivo: string): Promise<Movimentacao> {
    void motivo;
    const m = achar(id);
    if (m.status !== "agendada") throw transicao(m, "cancelar", "cancelada");
    m.status = "cancelada";
    m.acoes = SEM_ACOES;
    return copia(m);
  },

  async enviarFotoDaChegada(id: number, posicao: PosicaoDaFotoDaChegada, arquivo: File): Promise<FotoDaChegada> {
    const m = achar(id);
    const foto: FotoDaChegada = { posicao, url: `/exemplo/${posicao}-${arquivo.size}.jpg`, url_expira_em: "2026-10-07T15:00:00Z" };
    m.fotos_chegada = [...(m.fotos_chegada ?? []).filter((f) => f.posicao !== posicao), foto];
    return copia(foto);
  },

  async registrarChegada(id: number, c: ChegadaNoDestino): Promise<Movimentacao> {
    const m = achar(id);
    if (m.status !== "em_transito") throw transicao(m, "registrar a chegada de", "concluida");
    const campos: Record<string, string> = {};
    const fotos = m.fotos_chegada?.length ?? 0;
    if (m.vistoria_rapida && !c.combustivel) campos.combustivel = "Informe o combustível.";
    if (m.vistoria_rapida && fotos < 4) campos.fotos = `Faltam ${4 - fotos} fotos.`;
    if (m.transferencia && !c.recebido_por_id) campos.recebido_por_id = "Informe quem recebe o veículo.";
    if (Object.keys(campos).length) throw new ErroApi(400, "validacao", "Confira os campos.", undefined, campos);
    if (m.km_saida !== null && c.km < m.km_saida) throw new ErroApi(422, "VEI-01", `O km informado é menor que o atual (${m.km_saida.toLocaleString("pt-BR")}).`, { km_atual: m.km_saida });
    m.status = "concluida";
    m.concluida_em = new Date().toISOString();
    m.proxima_etapa = null;
    m.acoes = SEM_ACOES;
    m.chegada = { km: c.km, combustivel: c.combustivel ?? null, recebido_por: PESSOAS.find((p) => p.id === c.recebido_por_id) ?? null, fotos: m.fotos_chegada ?? [] };
    m.veiculo = { ...m.veiculo, status: "disponivel" };
    resumos[id] = "concluída agora";
    return copia(m);
  },

  async locais(f: { busca?: string } = {}): Promise<{ resultados: LocalDeApoio[] }> {
    const busca = f.busca?.trim().toLowerCase();
    return { resultados: copia(locais.filter((l) => l.ativo && (!busca || l.nome.toLowerCase().includes(busca)))) };
  },

  async criarLocal(c: NovoLocalDeApoio): Promise<LocalDeApoio> {
    const igual = locais.find((l) => l.nome.trim().toLowerCase() === c.nome.trim().toLowerCase());
    if (igual) throw new ErroApi(409, "local_existente", "Já existe um local com este nome.", { local_id: igual.id, ativo: igual.ativo });
    const novo: LocalDeApoio = { id: 100 + locais.length, nome: c.nome.trim(), tipo: c.tipo, ativo: true };
    locais = [...locais, novo];
    return copia(novo);
  },

  /** Sem rota no contrato (dúvida no handoff): usuários ativos da filial de saída, menos o financeiro. */
  async quemPodeLevar(filialId: number): Promise<{ id: number; nome: string }[]> {
    return PESSOAS.filter((p) => p.filial_id === filialId).map(({ id, nome }) => ({ id, nome }));
  },

  /** Sem rota no contrato (dúvida no handoff): usuários ativos da filial de destino. */
  async quemPodeReceber(filialId: number): Promise<{ id: number; nome: string }[]> {
    return PESSOAS.filter((p) => p.filial_id === filialId).map(({ id, nome }) => ({ id, nome }));
  },
};
