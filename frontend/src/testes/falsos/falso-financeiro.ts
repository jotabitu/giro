// DADOS FALSOS do financeiro nos testes (contrato: docs/api/financeiro.md). Só api-falsa.ts importa este arquivo.
// A "API" decide valor do dia, multa, juros, status e erros; a tela só mostra. Números do seed Moto Rápida em 07 out 2026
// (docs/qa/criterios/T-017.md): Carlos e Rafael em atraso (R$ 1.646,40), caixa da Filial Centro com R$ 1.111,90.
import { ErroApi } from "@/lib/api/tipos";
import type {
  Caixa,
  CaixaDeHoje,
  CobrancaDaConta,
  ContaReceber,
  ContaReceberDetalhe,
  Despesa,
  ExportacaoCriada,
  FiltroDespesas,
  FiltroReceber,
  FormaDeRecebimento,
  LancamentoAvulso,
  ListaContasReceber,
  ListaDespesas,
  MovimentoDoCaixa,
  NovaDespesa,
  PagamentoDeDespesa,
  PedidoDeExportacaoDeDespesas,
  PedidoDeAprovacao,
} from "@/lib/api/tipos-financeiro";
import { pausa, perfilAtualFalso } from "./falso";

const HOJE = "2026-10-07";
const CENTRO = { id: 1, nome: "Filial Centro" };

const SEM_ACOES = { receber: false, gerar_pix: false, gerar_boleto: false, cobrar: false, cancelar: false, renegociar: false, estornar: false };

function conta(p: Partial<ContaReceber> & Pick<ContaReceber, "id" | "cliente" | "valor_centavos" | "vencimento" | "status">): ContaReceber {
  const paga = p.status === "paga";
  return {
    tipo: "parcela",
    numero: 1,
    total_parcelas: 4,
    origem: { tipo: "locacao", id: 1, codigo: "LOC-2790" },
    filial: CENTRO,
    veiculo_placa: null,
    dias_atraso: 0,
    faixa_atraso: null,
    forma_prevista: "pix",
    observacao: null,
    valor_hoje: { data: HOJE, dias_atraso: 0, principal_centavos: p.valor_centavos, multa_centavos: 0, juros_centavos: 0, total_centavos: p.valor_centavos, cobra_juros: true },
    pago_em: null,
    forma: null,
    multa_centavos: 0,
    juros_centavos: 0,
    estorno_de: null,
    estornada_em: null,
    cobranca_aberta: null,
    acoes: paga ? { ...SEM_ACOES, estornar: true } : { receber: true, gerar_pix: true, gerar_boleto: true, cobrar: true, cancelar: true, renegociar: true, estornar: false },
    ...p,
  };
}

const CONTAS: ContaReceber[] = [
  conta({
    id: 9011,
    cliente: { id: 1203, nome: "Rafael Sousa" },
    origem: { tipo: "locacao", id: 2790, codigo: "LOC-2790" },
    veiculo_placa: "PQD6E21",
    numero: 4,
    total_parcelas: 4,
    vencimento: "2026-09-12",
    valor_centavos: 134700,
    status: "atrasada",
    dias_atraso: 25,
    faixa_atraso: "8_30",
    forma_prevista: "boleto",
    valor_hoje: { data: HOJE, dias_atraso: 25, principal_centavos: 134700, multa_centavos: 2694, juros_centavos: 1123, total_centavos: 138517, cobra_juros: true },
  }),
  conta({
    id: 9010,
    cliente: { id: 1202, nome: "Carlos Menezes" },
    origem: { tipo: "locacao", id: 2841, codigo: "LOC-2841" },
    veiculo_placa: "QXA4B21",
    numero: 2,
    total_parcelas: 5,
    vencimento: "2026-09-30",
    valor_centavos: 29940,
    status: "atrasada",
    dias_atraso: 7,
    faixa_atraso: "1_7",
    forma_prevista: "pix_automatico",
    valor_hoje: { data: HOJE, dias_atraso: 7, principal_centavos: 29940, multa_centavos: 599, juros_centavos: 70, total_centavos: 30609, cobra_juros: true },
  }),
  conta({
    id: 9020,
    cliente: { id: 1201, nome: "Juliana Rocha" },
    origem: { tipo: "locacao", id: 2836, codigo: "LOC-2836" },
    veiculo_placa: "SAK1D39",
    numero: 3,
    total_parcelas: 8,
    vencimento: HOJE,
    valor_centavos: 32900,
    status: "vence_hoje",
  }),
  conta({
    id: 9030,
    cliente: { id: 1206, nome: "Lucas Ferreira" },
    origem: { tipo: "locacao", id: 2856, codigo: "LOC-2856" },
    numero: 2,
    total_parcelas: 4,
    vencimento: "2026-10-14",
    valor_centavos: 32900,
    status: "aberta",
  }),
  conta({
    id: 9040,
    cliente: { id: 1201, nome: "Juliana Rocha" },
    origem: { tipo: "locacao", id: 2836, codigo: "LOC-2836" },
    numero: 2,
    total_parcelas: 8,
    vencimento: "2026-09-30",
    valor_centavos: 32900,
    status: "paga",
    pago_em: "2026-10-07T11:02:00Z",
    forma: "pix",
  }),
];

// Despesas de outubro do seed (regras, "Despesas de outubro"): 6 lançamentos, R$ 7.066,70; aguardando aprovação R$ 1.200,00 (só os pneus).
const LUCIA = { id: 7, nome: "Lúcia Freitas" };
function despesa(p: Pick<Despesa, "id" | "data" | "descricao" | "categoria" | "valor_centavos" | "vencimento" | "status" | "rotulo_situacao" | "lancada_por"> & Partial<Despesa>): Despesa {
  const base = { veiculo: null, filial: { id: 1, nome: "Filial Centro" }, pago_em: null, forma: null, nota: null, origem: null, pedido_aprovacao_id: null, ...p };
  // `sem_nota` vem da API (MOV-04, T-288): aqui, só quando o falso não traz a nota.
  return { ...base, sem_nota: p.sem_nota ?? base.nota === null };
}
const DESPESAS: Despesa[] = [
  despesa({ id: 801, data: "2026-10-07", descricao: "Pneus (2 unidades)", categoria: "manutencao", veiculo: { id: 88, placa: "PMZ3E17" }, valor_centavos: 120000, vencimento: "2026-10-07", status: "aguardando_aprovacao", rotulo_situacao: "Aguardando gerente", lancada_por: { id: 5, nome: "João Silva" }, pedido_aprovacao_id: 91, nota: { url: "/notas/801.jpg", url_expira_em: "2026-10-07T13:15:00Z" } }),
  despesa({ id: 802, data: "2026-10-07", descricao: "Óleo 1 litro", categoria: "manutencao", veiculo: { id: 12, placa: "QXA4B21" }, valor_centavos: 4800, vencimento: "2026-10-07", status: "paga", rotulo_situacao: "Pago · caixa", lancada_por: { id: 4, nome: "Bruna Alves" }, pago_em: "2026-10-07T14:20:00Z", forma: "dinheiro" }),
  despesa({ id: 803, data: "2026-10-06", descricao: "Conta de luz", categoria: "fixas", valor_centavos: 41230, vencimento: "2026-10-10", status: "a_pagar", rotulo_situacao: "Vence 10 out", lancada_por: LUCIA }),
  despesa({ id: 804, data: "2026-10-05", descricao: "Aluguel do ponto", categoria: "fixas", valor_centavos: 350000, vencimento: "2026-10-05", status: "paga", rotulo_situacao: "Pago · boleto", lancada_por: LUCIA, pago_em: "2026-10-05T12:00:00Z", forma: "boleto" }),
  despesa({ id: 805, data: "2026-10-03", descricao: "IPVA ROE-2A88", categoria: "impostos", veiculo: { id: 31, placa: "ROE2A88" }, valor_centavos: 18640, vencimento: "2026-10-31", status: "a_pagar", rotulo_situacao: "A pagar", lancada_por: LUCIA }),
  despesa({ id: 806, data: "2026-10-02", descricao: "Rastreadores (86)", categoria: "rastreamento", valor_centavos: 172000, vencimento: "2026-10-02", status: "paga", rotulo_situacao: "Pago · cartão", lancada_por: LUCIA, pago_em: "2026-10-02T12:00:00Z", forma: "cartao" }),
];

const ROTULO_PAGO: Record<string, string> = { pix: "Pix", boleto: "boleto", cartao: "cartão", transferencia: "transferência", dinheiro: "caixa" };

let contas: ContaReceber[] = [];
let caixa: Caixa | null = null;
let movimentos: MovimentoDoCaixa[] = [];
let proximoMovimento = 500;
let cobradasHoje = new Set<number>();
let despesas: Despesa[] = [];
export const pedidosDeExportacao: PedidoDeExportacaoDeDespesas[] = [];
/** Pedidos de aprovação: nascem do seed na primeira leitura, e `reiniciarFinanceiroFalso` os apaga (TDZ: o seed vem depois). */
let pedidos: { id: number }[] | null = null;
let proximaDespesa = 810;

const SITUACAO: Record<NonNullable<FiltroReceber["situacao"]>, ContaReceber["status"][]> = {
  atrasadas: ["atrasada"],
  vencem_hoje: ["vence_hoje"],
  a_vencer: ["aberta"],
  pagas: ["paga"],
  canceladas: ["cancelada"],
};

function movimento(hora: string, tipo: MovimentoDoCaixa["tipo"], forma: MovimentoDoCaixa["forma"], descricao: string, valor: number): MovimentoDoCaixa {
  return { id: proximoMovimento++, hora: `2026-10-07T${hora}:00Z`, tipo, forma, descricao, valor_centavos: valor, origem: null, registrado_por: "Bruna Alves", estorno_de: null };
}

function caixaDoSeed(): Caixa {
  return {
    id: 240,
    filial: CENTRO,
    data: HOJE,
    status: "aberto",
    aberto_por: { id: 4, nome: "Bruna Alves" },
    aberto_em: "2026-10-07T10:55:00Z",
    resumo: {
      entrou_hoje_centavos: 111190,
      recebimentos: 5,
      por_forma: {
        pix: { centavos: 37390, quantidade: 2 },
        cartao: { centavos: 10900, quantidade: 1, texto: "cai em 30 dias" },
        dinheiro: { centavos: 62900, quantidade: 2 },
      },
      gaveta: { troco_centavos: 20000, entradas_dinheiro_centavos: 62900, saidas_dinheiro_centavos: 54800, esperado_centavos: 28100 },
    },
    fechamento: null,
    acoes: { sangria: true, fechar: true, receber: true },
  };
}

function movimentosDoSeed(): MovimentoDoCaixa[] {
  return [
    movimento("11:02", "entrada", "pix", "Juliana Rocha · LOC-2836 · 2ª semana", 32900),
    movimento("11:40", "entrada", "cartao", "LOC-2848 · renovação de 1 diária", 10900),
    movimento("12:15", "entrada", "dinheiro", "Lucas Ferreira · LOC-2856 · 1ª semana", 32900),
    movimento("12:15", "entrada", "dinheiro", "Lucas Ferreira · caução", 30000),
    movimento("13:30", "sangria", "dinheiro", "Depósito no banco", 50000),
    movimento("14:05", "entrada", "pix", "LOC-2826 · diária Urbana", 4490),
    movimento("14:20", "saida", "dinheiro", "Óleo · QXA4B21", 4800),
  ];
}

export type DiaDoCaixaFalso = "aberto" | "sem_caixa" | "fechado" | "aguardando";

/** Volta o financeiro ao estado do seed. O caixa pode começar sem abrir, fechado ou aguardando o gerente. */
export function reiniciarFinanceiroFalso(dia: DiaDoCaixaFalso = "aberto") {
  contas = CONTAS.map((c) => ({ ...c, acoes: { ...c.acoes }, valor_hoje: { ...c.valor_hoje } }));
  cobradasHoje = new Set();
  despesas = DESPESAS.map((d) => ({ ...d }));
  pedidos = null;
  pedidosDeExportacao.length = 0;
  proximaDespesa = 810;
  proximoMovimento = 500;
  movimentos = dia === "sem_caixa" ? [] : movimentosDoSeed();
  caixa = dia === "sem_caixa" ? null : caixaDoSeed();
  if (caixa && dia === "fechado") {
    caixa.status = "fechado";
    caixa.acoes = { sangria: false, fechar: false, receber: false };
    caixa.fechamento = { contado_centavos: 28100, esperado_centavos: 28100, diferenca_centavos: 0, motivo_diferenca: null, fechado_por: { id: 4, nome: "Bruna Alves" }, fechado_em: "2026-10-07T21:10:00Z", pedido_aprovacao_id: null };
  }
  if (caixa && dia === "aguardando") {
    caixa.status = "aguardando_aprovacao";
    caixa.acoes = { sangria: false, fechar: false, receber: false };
    caixa.fechamento = { contado_centavos: 27100, esperado_centavos: 28100, diferenca_centavos: -1000, motivo_diferenca: "Troco errado", fechado_por: null, fechado_em: null, pedido_aprovacao_id: 91 };
  }
}
reiniciarFinanceiroFalso();

const indicadores = () => ({
  previsto_mes_centavos: 5200210,
  previsto_mes_parcelas: 128,
  recebido_mes_centavos: 1340170,
  recebido_pct: "25.77",
  vence_hoje_centavos: 262580,
  vence_hoje_parcelas: 6,
  em_atraso_centavos: 164640,
  em_atraso_clientes: 2,
  em_atraso_parcelas: 2,
  faixas: { "1_7": 29940, "8_30": 134700, mais_30: 0 },
});

type PedidoSeed = Omit<PedidoDeAprovacao, "pode_decidir">;
const CENTRO_REF = { id: 1, nome: "Filial Centro" };
const pedido = (p: Partial<PedidoSeed> & Pick<PedidoSeed, "id" | "tipo" | "titulo" | "detalhe" | "origem" | "solicitante" | "pedido_em">): PedidoSeed => ({
  status: "pendente",
  filial: CENTRO_REF,
  proprio_pedido: false,
  motivo_pedido: null,
  valor_centavos: null,
  pct: null,
  decidido_por: null,
  decidido_em: null,
  motivo_recusa: null,
  ...p,
});
const RODRIGO = { id: 2, nome: "Rodrigo Pinheiro" };
const SEED_PEDIDOS: PedidoSeed[] = [
  pedido({ id: 88, tipo: "APR-01", titulo: "Desconto de 8% na venda para Diego Martins", detalhe: "VEN-0177", origem: { tipo: "venda", id: 177, codigo: "VEN-0177" }, solicitante: { id: 4, nome: "Bruna Alves" }, pedido_em: "2026-10-07T13:00:00Z", pct: "8.00", valor_centavos: 183200 }),
  pedido({ id: 89, tipo: "APR-02", titulo: "Encerrar antes do fim a LOC-2812 · Patrícia Gomes", detalhe: "a cliente pediu pelo WhatsApp", origem: { tipo: "locacao", id: 2812, codigo: "LOC-2812" }, solicitante: { id: 4, nome: "Bruna Alves" }, pedido_em: "2026-10-07T14:00:00Z", valor_centavos: 8480 }),
  pedido({ id: 91, tipo: "APR-03", titulo: "Despesa de R$ 1.200,00", detalhe: "Pneus (2 unidades) · PMZ-3E17", origem: { tipo: "despesa", id: 801, codigo: null }, solicitante: { id: 5, nome: "João Silva" }, pedido_em: "2026-10-07T14:20:00Z", valor_centavos: 120000 }),
  pedido({ id: 80, tipo: "APR-04", status: "aprovado", titulo: "Diferença de caixa de R$ 3,50", detalhe: "caixa fechado com a diferença", origem: { tipo: "caixa", id: 238, codigo: null }, solicitante: { id: 4, nome: "Bruna Alves" }, pedido_em: "2026-10-06T21:00:00Z", decidido_por: RODRIGO, decidido_em: "2026-10-06T21:30:00Z" }),
  pedido({ id: 77, tipo: "APR-01", status: "recusado", titulo: "Desconto de 12% · Pop 110i", detalhe: "VEN-0170", origem: { tipo: "venda", id: 170, codigo: "VEN-0170" }, solicitante: { id: 4, nome: "Bruna Alves" }, pedido_em: "2026-10-05T14:00:00Z", pct: "12.00", decidido_por: RODRIGO, decidido_em: "2026-10-05T15:00:00Z", motivo_recusa: "abaixo do preço mínimo" }),
  pedido({ id: 74, tipo: "APR-06", status: "aprovado", titulo: "Correção de km · RJD-5B38", detalhe: "12.480 → 12.408 km, erro de digitação", origem: { tipo: "veiculo", id: 14, codigo: null }, solicitante: { id: 5, nome: "João Silva" }, pedido_em: "2026-10-04T12:00:00Z", decidido_por: RODRIGO, decidido_em: "2026-10-04T13:00:00Z" }),
  pedido({ id: 70, tipo: "APR-05", status: "aprovado", titulo: "Desbloqueio de Ana Beatriz Lima", detalhe: "quitou o atraso", origem: { tipo: "cliente", id: 1210, codigo: null }, solicitante: { id: 4, nome: "Bruna Alves" }, pedido_em: "2026-10-02T12:00:00Z", decidido_por: RODRIGO, decidido_em: "2026-10-02T13:00:00Z" }),
];
const quemSou = (): number | null => {
  const perfil = perfilAtualFalso();
  return perfil === "vendedor" ? 4 : perfil === "vistoriador" ? 5 : perfil === "gerente" ? 2 : perfil === "administrador" ? 1 : null;
};
const comoApi = (p: PedidoSeed): PedidoDeAprovacao => ({ ...p, pode_decidir: p.status === "pendente" && ["gerente", "administrador"].includes(perfilAtualFalso() ?? "") && (p.solicitante.id !== quemSou() || perfilAtualFalso() === "administrador") });
const achaPedido = (id: number) => {
  const p = todos().find((x) => x.id === id);
  if (!p) throw new ErroApi(404, "nao_encontrado", "Pedido não encontrado.");
  return p;
};
const decidir = (id: number, status: "aprovado" | "recusado" | "cancelado", motivo: string | null = null): PedidoDeAprovacao => {
  const p = achaPedido(id);
  if (p.status !== "pendente") throw new ErroApi(409, "transicao_pedido", "Este pedido já foi decidido.");
  const novo: PedidoSeed = { ...p, status, motivo_recusa: motivo, decidido_por: status === "cancelado" ? null : RODRIGO, decidido_em: "2026-10-07T15:10:00Z" };
  pedidos = todos().map((x) => (x.id === id ? novo : x));
  return comoApi(novo);
};

const todos = (): PedidoSeed[] => {
  pedidos ??= SEED_PEDIDOS.map((p) => ({ ...p }));
  return pedidos as PedidoSeed[];
};

export const aprovacoesFalso = {
  async listar(f: { status?: PedidoDeAprovacao["status"]; tipo?: PedidoDeAprovacao["tipo"]; minhas?: boolean } = {}): Promise<{ contagens: { pendente: number }; resultados: PedidoDeAprovacao[] }> {
    await pausa(40);
    const perfil = perfilAtualFalso();
    const decide = perfil === "gerente" || perfil === "administrador";
    const eu = quemSou();
    const base = f.minhas ? todos().filter((p) => p.solicitante.id === eu) : decide ? todos().filter((p) => p.solicitante.id !== eu || perfil === "administrador") : [];
    const lista = base
      .filter((p) => p.status === (f.status ?? "pendente") && (!f.tipo || p.tipo === f.tipo))
      .sort((a, b) => (f.status && f.status !== "pendente" ? b.pedido_em.localeCompare(a.pedido_em) : a.pedido_em.localeCompare(b.pedido_em)));
    return { contagens: { pendente: base.filter((p) => p.status === "pendente").length }, resultados: lista.map(comoApi) };
  },
  async aprovar(id: number): Promise<PedidoDeAprovacao> {
    await pausa(60);
    const r = decidir(id, "aprovado");
    despesas = despesas.map((d) => (d.pedido_aprovacao_id === id ? { ...d, status: "a_pagar", rotulo_situacao: "A pagar" } : d));
    return r;
  },
  async recusar(id: number, motivo: string): Promise<PedidoDeAprovacao> {
    await pausa(60);
    if (!motivo.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { motivo: "Informe o motivo da recusa." });
    const r = decidir(id, "recusado", motivo);
    despesas = despesas.map((d) => (d.pedido_aprovacao_id === id ? { ...d, status: "recusada", rotulo_situacao: "Recusada" } : d));
    return r;
  },
  async cancelar(id: number): Promise<PedidoDeAprovacao> {
    await pausa(60);
    if (achaPedido(id).solicitante.id !== quemSou()) throw new ErroApi(403, "so_quem_pediu", "Só quem fez o pedido pode cancelar");
    return decidir(id, "cancelado");
  },
};

const semAcento = (t: string) => t.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const naoEncontrada = () => new ErroApi(404, "nao_encontrado", "Conta não encontrada.");
const semCaixa = () => new ErroApi(422, "FIN-07", "Abra o caixa do dia para receber");

export const financeiroFalso = {
  async listarContas(f: FiltroReceber = {}): Promise<ListaContasReceber> {
    await pausa(60);
    const busca = f.busca ? semAcento(f.busca) : "";
    const filtradas = contas.filter((c) => {
      if (f.situacao && !SITUACAO[f.situacao].includes(c.status)) return false;
      if (f.faixa && c.faixa_atraso !== f.faixa) return false;
      if (f.cliente && c.cliente.id !== f.cliente) return false;
      if (busca && !semAcento(`${c.cliente.nome} ${c.origem.codigo ?? ""} ${c.veiculo_placa ?? ""}`).includes(busca)) return false;
      return true;
    });
    return {
      indicadores: indicadores(),
      contagens: { todas: 130, atrasadas: 2, vencem_hoje: 6, a_vencer: 92, pagas: 30 },
      resultados: filtradas.map((c) => ({ ...c })),
      proximo: null,
      anterior: null,
    };
  },

  async obterConta(id: number): Promise<ContaReceberDetalhe> {
    await pausa(60);
    const c = contas.find((x) => x.id === id);
    if (!c) throw naoEncontrada();
    return {
      ...c,
      historico: [
        { em: "2026-10-07T13:02:00Z", acao: "conta_receber.cobrar", por: null, motivo: null },
        { em: "2026-10-07T13:02:00Z", acao: "cobranca.pix", por: null, motivo: null },
      ],
    };
  },

  async lancar(corpo: LancamentoAvulso): Promise<ContaReceber> {
    await pausa(60);
    if (corpo.valor_centavos <= 0) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { valor_centavos: "Informe um valor maior que zero." });
    const nova = conta({ id: 9100 + contas.length, cliente: { id: corpo.cliente_id, nome: "Cliente" }, tipo: corpo.tipo, numero: null, total_parcelas: null, vencimento: corpo.vencimento, valor_centavos: corpo.valor_centavos, status: "aberta", observacao: corpo.descricao.slice(0, 150) });
    contas = [...contas, nova];
    return nova;
  },

  async receber(id: number, corpo: { forma: FormaDeRecebimento; valor_centavos: number }): Promise<ContaReceber> {
    await pausa(60);
    const c = contas.find((x) => x.id === id);
    if (!c) throw naoEncontrada();
    if (!caixa || caixa.status !== "aberto") throw semCaixa();
    if (corpo.valor_centavos !== c.valor_hoje.total_centavos) throw new ErroApi(422, "FIN-01", "Não existe pagamento parcial. Receba o valor inteiro ou renegocie.");
    const paga: ContaReceber = { ...c, status: "paga", forma: corpo.forma, pago_em: `${HOJE}T15:30:00Z`, multa_centavos: c.valor_hoje.multa_centavos, juros_centavos: c.valor_hoje.juros_centavos, acoes: { ...SEM_ACOES, estornar: true } };
    contas = contas.map((x) => (x.id === id ? paga : x));
    movimentos = [...movimentos, movimento("15:30", "entrada", corpo.forma === "dinheiro" ? "dinheiro" : "cartao", `${c.cliente.nome} · ${c.origem.codigo ?? ""}`, corpo.valor_centavos)];
    return paga;
  },

  async gerarCobranca(id: number, corpo: { tipo: "pix" | "boleto"; vence_em?: string | null; no_caixa?: boolean }): Promise<CobrancaDaConta> {
    await pausa(60);
    const c = contas.find((x) => x.id === id);
    if (!c) throw naoEncontrada();
    if (corpo.no_caixa && (!caixa || caixa.status !== "aberto")) throw semCaixa();
    const cobranca: CobrancaDaConta = {
      id: 55,
      tipo: corpo.tipo,
      valor_centavos: c.valor_hoje.total_centavos,
      vence_em: corpo.vence_em ?? HOJE,
      pix_copia_e_cola: corpo.tipo === "pix" ? "00020126580014br.gov.bcb.pix0136falso-0000-0000" : null,
      qr_code_url: null,
      linha_digitavel: corpo.tipo === "boleto" ? "23793.38128 60000.000003 00000.000400 1 00000000000000" : null,
      boleto_url: null,
      status: "aguardando",
    };
    contas = contas.map((x) => (x.id === id ? { ...x, cobranca_aberta: cobranca } : x));
    return cobranca;
  },

  async cobrar(id: number): Promise<{ enviadas: number }> {
    await pausa(60);
    if (cobradasHoje.has(id)) return { enviadas: 0 };
    cobradasHoje.add(id);
    return { enviadas: 1 };
  },

  async cobrarEmLote(ids: number[]): Promise<{ enviadas: number }> {
    await pausa(60);
    const novas = ids.filter((i) => !cobradasHoje.has(i));
    novas.forEach((i) => cobradasHoje.add(i));
    return { enviadas: novas.length };
  },

  async cancelarConta(id: number, motivo: string): Promise<ContaReceber> {
    await pausa(60);
    if (!motivo.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { motivo: "Informe o motivo." });
    const c = contas.find((x) => x.id === id);
    if (!c) throw naoEncontrada();
    const nova: ContaReceber = { ...c, status: "cancelada", acoes: { ...SEM_ACOES } };
    contas = contas.map((x) => (x.id === id ? nova : x));
    return nova;
  },

  async estornarConta(id: number, motivo: string): Promise<ContaReceber> {
    await pausa(60);
    if (!motivo.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { motivo: "Informe o motivo." });
    const c = contas.find((x) => x.id === id);
    if (!c) throw naoEncontrada();
    return { ...c, estornada_em: `${HOJE}T15:40:00Z`, acoes: { ...c.acoes, estornar: false } };
  },

  async caixaDeHoje(): Promise<CaixaDeHoje> {
    await pausa(60);
    return caixa ? { ...caixa } : { caixa: null, pode_abrir: true };
  },

  async abrirCaixa(troco_centavos: number): Promise<Caixa> {
    await pausa(60);
    if (caixa) throw new ErroApi(409, "FIN-07", "O caixa de hoje desta filial já foi aberto");
    const novo = caixaDoSeed();
    novo.resumo = {
      entrou_hoje_centavos: 0,
      recebimentos: 0,
      por_forma: { pix: { centavos: 0, quantidade: 0 }, cartao: { centavos: 0, quantidade: 0 }, dinheiro: { centavos: 0, quantidade: 0 } },
      gaveta: { troco_centavos, entradas_dinheiro_centavos: 0, saidas_dinheiro_centavos: 0, esperado_centavos: troco_centavos },
    };
    caixa = novo;
    movimentos = [];
    return { ...novo };
  },

  async movimentos(_caixaId: number, tipo?: "entrada" | "saida" | "sangria"): Promise<{ resultados: MovimentoDoCaixa[] }> {
    await pausa(60);
    return { resultados: movimentos.filter((m) => !tipo || m.tipo === tipo) };
  },

  async sangria(_caixaId: number, corpo: { valor_centavos: number; descricao: string }): Promise<MovimentoDoCaixa> {
    await pausa(60);
    if (!caixa || caixa.status !== "aberto") throw new ErroApi(409, "FIN-07", "Este caixa já foi fechado");
    const g = caixa.resumo.gaveta;
    if (corpo.valor_centavos > g.esperado_centavos) throw new ErroApi(422, "sangria_maior_que_gaveta", "A sangria é maior que o dinheiro que deve estar na gaveta.");
    const m = movimento("15:45", "sangria", "dinheiro", corpo.descricao, corpo.valor_centavos);
    movimentos = [...movimentos, m];
    caixa = { ...caixa, resumo: { ...caixa.resumo, gaveta: { ...g, saidas_dinheiro_centavos: g.saidas_dinheiro_centavos + corpo.valor_centavos, esperado_centavos: g.esperado_centavos - corpo.valor_centavos } } };
    return m;
  },

  async fecharCaixa(_caixaId: number, corpo: { contado_centavos: number; motivo_diferenca?: string | null }): Promise<Caixa> {
    await pausa(60);
    if (!caixa || caixa.status !== "aberto") throw new ErroApi(409, "FIN-07", "Este caixa já foi fechado");
    const esperado = caixa.resumo.gaveta.esperado_centavos;
    const diferenca = corpo.contado_centavos - esperado;
    if (diferenca !== 0 && !corpo.motivo_diferenca?.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { motivo_diferenca: "Informe o motivo da diferença." });
    const fechamento = {
      contado_centavos: corpo.contado_centavos,
      esperado_centavos: esperado,
      diferenca_centavos: diferenca,
      motivo_diferenca: corpo.motivo_diferenca ?? null,
      fechado_por: diferenca === 0 ? { id: 4, nome: "Bruna Alves" } : null,
      fechado_em: diferenca === 0 ? `${HOJE}T21:10:00Z` : null,
      pedido_aprovacao_id: diferenca === 0 ? null : 91,
    };
    caixa = { ...caixa, status: diferenca === 0 ? "fechado" : "aguardando_aprovacao", fechamento, acoes: { sangria: false, fechar: false, receber: false } };
    return { ...caixa };
  },

  async listarDespesas(f: FiltroDespesas = {}): Promise<ListaDespesas> {
    await pausa(60);
    const doMes = despesas.filter((d) => d.data.startsWith(f.mes ?? "2026-10"));
    // `?busca=` (FIN-16): descrição ou placa, sem acento nem hífen; muda a lista e as contagens, não os indicadores.
    const normal = (t: string) => t.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase();
    const termo = normal((f.busca ?? "").trim());
    const placaDoTermo = termo.replace(/[\s-]/g, "");
    const buscadas = termo ? doMes.filter((d) => normal(d.descricao).includes(termo) || (placaDoTermo !== "" && !!d.veiculo && normal(d.veiculo.placa).includes(placaDoTermo))) : doMes;
    const lista = buscadas.filter((d) => (!f.status || d.status === f.status) && (!f.categoria || d.categoria === f.categoria) && (!f.veiculo || d.veiculo?.id === f.veiculo));
    const soma = (xs: Despesa[]) => xs.reduce((t, d) => t + d.valor_centavos, 0);
    const aguardando = doMes.filter((d) => d.status === "aguardando_aprovacao");
    const por: Record<string, number> = {};
    for (const d of doMes) por[d.categoria] = (por[d.categoria] ?? 0) + d.valor_centavos;
    const gasto = soma(doMes.filter((d) => d.status !== "recusada"));
    return {
      indicadores: {
        gasto_mes_centavos: gasto,
        despesa_por_veiculo_centavos: Math.round(gasto / 86), // FIN-16: 86 veículos ativos no seed; quem divide é a API
        aguardando_aprovacao_centavos: soma(aguardando),
        aguardando_aprovacao_quantidade: aguardando.length,
        a_pagar_semana_centavos: soma(doMes.filter((d) => d.status === "a_pagar" && d.vencimento <= "2026-10-14")),
        por_categoria: por,
      },
      contagens: {
        aguardando_aprovacao: buscadas.filter((d) => d.status === "aguardando_aprovacao").length,
        a_pagar: buscadas.filter((d) => d.status === "a_pagar").length,
        paga: buscadas.filter((d) => d.status === "paga").length,
        recusada: buscadas.filter((d) => d.status === "recusada").length,
      },
      resultados: lista.map((d) => ({ ...d })),
      proximo: null,
      anterior: null,
    };
  },

  /** Pedidos feitos à exportação, para o teste conferir o corpo: sempre o mês e a filial, nunca a busca nem a aba. */
  async exportarDespesas(pedido: PedidoDeExportacaoDeDespesas): Promise<ExportacaoCriada> {
    await pausa(40);
    pedidosDeExportacao.push(pedido);
    return { id: 17, status: "na_fila" };
  },

  async obterDespesa(id: number): Promise<Despesa> {
    await pausa(40);
    const d = despesas.find((x) => x.id === id);
    if (!d) throw new ErroApi(404, "nao_encontrado", "Despesa não encontrada.");
    return { ...d };
  },

  async lancarDespesa(corpo: NovaDespesa): Promise<Despesa> {
    await pausa(60);
    if (!corpo.descricao.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { descricao: "Informe a descrição." });
    if (corpo.valor_centavos > 50000 && corpo.pago_no_caixa) throw new ErroApi(422, "APR-03", "Despesa acima de R$ 500,00 precisa de aprovação antes de ser paga.");
    const acima = corpo.valor_centavos > 50000;
    const nova = despesa({
      id: proximaDespesa++,
      data: corpo.data,
      descricao: corpo.descricao,
      categoria: corpo.categoria,
      valor_centavos: corpo.valor_centavos,
      vencimento: corpo.vencimento,
      status: acima ? "aguardando_aprovacao" : corpo.pago_no_caixa ? "paga" : "a_pagar",
      rotulo_situacao: acima ? "Aguardando gerente" : corpo.pago_no_caixa ? "Pago · caixa" : "A pagar",
      lancada_por: { id: 1, nome: "Mariana Costa" },
      veiculo: corpo.veiculo_id ? { id: corpo.veiculo_id, placa: "SAK1D39" } : null,
      pedido_aprovacao_id: acima ? 95 : null,
      nota: corpo.nota ? { url: "/notas/nova.jpg", url_expira_em: "2026-10-07T13:15:00Z" } : null,
    });
    despesas = [nova, ...despesas];
    // O pedido APR-03 nasce com a despesa; quem a lançou é a administradora (id 1), que também decide (APR-09).
    if (acima) todos().push(pedido({ id: 95, tipo: "APR-03", titulo: "Despesa lançada", detalhe: corpo.descricao, origem: { tipo: "despesa", id: nova.id, codigo: null }, solicitante: { id: 1, nome: "Mariana Costa" }, pedido_em: "2026-10-08T13:00:00Z", valor_centavos: corpo.valor_centavos }));
    return { ...nova };
  },

  async pagarDespesa(id: number, corpo: PagamentoDeDespesa): Promise<Despesa> {
    await pausa(60);
    const atual = despesas.find((x) => x.id === id);
    if (!atual) throw new ErroApi(404, "nao_encontrado", "Despesa não encontrada.");
    if (atual.status !== "a_pagar") throw new ErroApi(409, "transicao_despesa", "Só despesa a pagar pode ser paga.");
    if (corpo.forma === "dinheiro" && (!caixa || caixa.status !== "aberto")) throw semCaixa();
    const paga: Despesa = { ...atual, status: "paga", pago_em: corpo.pago_em, forma: corpo.forma, rotulo_situacao: `Pago · ${ROTULO_PAGO[corpo.forma]}` };
    despesas = despesas.map((x) => (x.id === id ? paga : x));
    return { ...paga };
  },
};
