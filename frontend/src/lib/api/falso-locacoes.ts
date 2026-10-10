// DADOS FALSOS de locações enquanto a sessão real (T-011) não liga o app à API (contrato: docs/api/locacoes.md).
// Só ./index.ts importa este arquivo. A "API" decide situação, ações, valores, estimativas e erros; a tela só mostra.
// O formato das respostas é o do OpenAPI (tipos-locacoes.ts); os números vêm da carteira de outubro (hoje = 07 out 2026).
import { pausa, perfilAtualFalso } from "./falso";
import { ErroApi } from "./tipos";
import { veiculosFalso } from "./falso-frota";
import type {
  AbaLocacoes,
  FiltroLocacoes,
  FormaDevolucaoCancelamento,
  HistoricoDaLocacao,
  ListaLocacoes,
  LocacaoCompleta,
  LocacaoResumo,
  ParcelaDaLocacao,
  ParcelaPrevista,
  PedidoDeCancelamento,
  Periodicidade,
  SimulacaoDaRenovacao,
  SimulacaoDoCancelamento,
  StatusLocacao,
  StatusParcela,
  TrocaPedida,
} from "./tipos-locacoes";
import type { Perfil } from "./tipos";

const TAMANHO = 8;
export const AGORA_DO_SEED = "2026-10-07T15:30:00Z";
const DIA = 86_400_000;

type Corpo = {
  /** Valor do período (semana ou mês) e caução, em centavos. */
  periodoCentavos: number;
  diariaCentavos: number;
  caucaoCentavos: number;
  kmSaida: number | null;
  contrato: { status: "gerado" | "enviado" | "assinado"; modelo: string; assinadoEm: string | null } | null;
};

type Semente = {
  id: number;
  status: StatusLocacao;
  cliente: { id: number; nome: string };
  veiculo: { id: number; modelo: string; placa: string };
  periodicidade: Periodicidade;
  inicio: string;
  fim: string;
  situacao: LocacaoResumo["situacao"];
  pagamento: NonNullable<LocacaoResumo["pagamento"]>;
  acao: LocacaoResumo["acao_principal"];
  sinais?: Partial<LocacaoResumo["sinais"]>;
  corpo: Corpo;
  parcelas: [tipo: "parcela" | "caucao", vencimento: string, valor: number, status: StatusParcela, forma?: string][];
  extras?: string[];
  desconto?: string;
  cancelamento?: { status: "pendente" | "aprovado"; data: string; multa: number; credito: number; devolver: number; motivo: string };
  trocaPendente?: boolean;
  eventos: [em: string, rotulo: string, detalhe: string][];
  devolucaoId?: number | null;
};

const SEMENTES: Semente[] = [
  {
    id: 2790, status: "devolucao_atrasada", cliente: { id: 1203, nome: "Rafael Sousa" }, veiculo: { id: 511, modelo: "Honda Pop 110i", placa: "PQD6E21" },
    periodicidade: "semanal", inicio: "2026-09-05T12:00:00Z", fim: "2026-09-12T12:00:00Z",
    situacao: { codigo: "devolucao_atrasada", rotulo: "Devolução atrasada 25 dias", tom: "perigo" },
    pagamento: { rotulo: "R$ 1.347,00 em aberto", tom: "alerta", em_aberto_centavos: 134700 },
    acao: { codigo: "cobrar", rotulo: "Cobrar" }, sinais: { pagamento_atrasado: true },
    corpo: { periodoCentavos: 23900, diariaCentavos: 3990, caucaoCentavos: 20000, kmSaida: 9120, contrato: { status: "assinado", modelo: "Locação semanal", assinadoEm: "2026-09-05T12:20:00Z" } },
    parcelas: [["parcela", "2026-09-05", 23900, "paga", "pix"], ["parcela", "2026-09-12", 44900, "atrasada"], ["parcela", "2026-09-19", 44900, "atrasada"], ["parcela", "2026-09-26", 44900, "atrasada"], ["caucao", "2026-09-05", 20000, "paga", "pix"]],
    eventos: [["2026-09-05T12:05:00Z", "Locação criada por Bruna Alves", ""], ["2026-09-05T12:20:00Z", "Contrato assinado pelo cliente", "assinatura no celular · IP registrado"], ["2026-09-12T12:00:00Z", "Devolução prevista", "não devolveu"]],
  },
  {
    id: 2841, status: "ativa", cliente: { id: 1208, nome: "Carlos Menezes" }, veiculo: { id: 501, modelo: "Honda CG 160 Fan", placa: "QXA4B21" },
    periodicidade: "semanal", inicio: "2026-09-23T12:00:00Z", fim: "2026-10-28T21:00:00Z",
    situacao: { codigo: "pagamento_atrasado", rotulo: "Parcela 2 atrasada", tom: "alerta" },
    pagamento: { rotulo: "R$ 299,40 em aberto", tom: "alerta", em_aberto_centavos: 29940 },
    acao: { codigo: "cobrar", rotulo: "Cobrar" }, sinais: { pagamento_atrasado: true },
    corpo: { periodoCentavos: 29940, diariaCentavos: 5490, caucaoCentavos: 30000, kmSaida: 17210, contrato: { status: "assinado", modelo: "Locação semanal", assinadoEm: "2026-09-23T12:30:00Z" } },
    parcelas: [["parcela", "2026-09-23", 29940, "paga", "pix"], ["parcela", "2026-09-30", 29940, "atrasada"], ["parcela", "2026-10-07", 29940, "vence_hoje"], ["parcela", "2026-10-14", 29940, "aberta"], ["parcela", "2026-10-21", 29940, "aberta"], ["caucao", "2026-09-23", 30000, "paga", "pix"]],
    eventos: [["2026-09-23T12:05:00Z", "Locação criada por Rodrigo Pinheiro", ""], ["2026-09-23T12:15:00Z", "Vistoria de saída · 12 fotos", "João Silva · 17.210 km · tanque 4/4"], ["2026-09-23T12:30:00Z", "Contrato assinado pelo cliente", "assinatura no celular · IP registrado"], ["2026-09-23T13:00:00Z", "Pagamento da 1ª semana", "Pix"]],
  },
  {
    id: 2836, status: "ativa", cliente: { id: 1201, nome: "Juliana Rocha" }, veiculo: { id: 502, modelo: "Yamaha Factor 150", placa: "PNB7C04" },
    periodicidade: "semanal", inicio: "2026-09-30T12:10:00Z", fim: "2026-10-14T21:00:00Z",
    situacao: { codigo: "ativa", rotulo: "Ativa", tom: "sucesso" },
    pagamento: { rotulo: "Pago", tom: "sucesso", em_aberto_centavos: 0 },
    acao: { codigo: "abrir", rotulo: "Abrir" },
    corpo: { periodoCentavos: 32900, diariaCentavos: 5490, caucaoCentavos: 30000, kmSaida: 18402, contrato: { status: "assinado", modelo: "Locação semanal", assinadoEm: "2026-09-30T12:31:00Z" } },
    parcelas: [["parcela", "2026-09-30", 32900, "paga", "pix"], ["parcela", "2026-10-07", 32900, "paga", "pix"], ["caucao", "2026-09-30", 30000, "paga", "pix"]],
    extras: ["Capacete extra"],
    eventos: [
      ["2026-09-30T12:10:00Z", "Locação criada por Bruna Alves", ""],
      ["2026-09-30T12:25:00Z", "Vistoria de saída · 12 fotos", "João Silva · 18.402 km · tanque 4/4"],
      ["2026-09-30T12:31:00Z", "Contrato assinado pela cliente", "assinatura no celular · IP registrado"],
      ["2026-10-07T11:02:00Z", "Pagamento da 2ª semana", "Pix"],
    ],
  },
  {
    id: 2850, status: "ativa", cliente: { id: 1215, nome: "Marcos Viana" }, veiculo: { id: 512, modelo: "Honda Biz 125", placa: "RJD5B38" },
    periodicidade: "mensal", inicio: "2026-10-01T12:00:00Z", fim: "2026-10-31T12:00:00Z",
    situacao: { codigo: "ativa", rotulo: "Ativa", tom: "sucesso" },
    pagamento: { rotulo: "Pix automático", tom: "sucesso", em_aberto_centavos: 0 },
    acao: { codigo: "abrir", rotulo: "Abrir" },
    corpo: { periodoCentavos: 89900, diariaCentavos: 4490, caucaoCentavos: 20000, kmSaida: 7210, contrato: { status: "assinado", modelo: "Locação mensal", assinadoEm: "2026-10-01T12:20:00Z" } },
    parcelas: [["parcela", "2026-10-01", 89900, "paga", "pix_automatico"], ["caucao", "2026-10-01", 20000, "paga", "pix"]],
    eventos: [["2026-10-01T12:00:00Z", "Locação criada por Bruna Alves", ""], ["2026-10-01T12:20:00Z", "Contrato assinado pelo cliente", "assinatura no celular · IP registrado"]],
  },
  {
    id: 2856, status: "aguardando_retirada", cliente: { id: 1206, nome: "Lucas Ferreira" }, veiculo: { id: 504, modelo: "Honda CG 160 Fan", placa: "SAK1D39" },
    periodicidade: "semanal", inicio: "2026-10-07T12:30:00Z", fim: "2026-10-14T12:30:00Z",
    situacao: { codigo: "aguardando_assinatura", rotulo: "Aguardando assinatura", tom: "neutro" },
    pagamento: { rotulo: "R$ 329,00 pago", tom: "neutro", em_aberto_centavos: 30000 },
    acao: { codigo: "abrir", rotulo: "Abrir" },
    corpo: { periodoCentavos: 32900, diariaCentavos: 5490, caucaoCentavos: 30000, kmSaida: null, contrato: { status: "enviado", modelo: "Locação semanal", assinadoEm: null } },
    parcelas: [["parcela", "2026-10-07", 32900, "paga", "pix"], ["caucao", "2026-10-07", 30000, "aberta"]],
    eventos: [["2026-10-07T12:05:00Z", "Locação criada por Bruna Alves", ""], ["2026-10-07T12:10:00Z", "Contrato enviado por WhatsApp", "aguardando assinatura"]],
  },
  {
    id: 2812, status: "ativa", cliente: { id: 1209, nome: "Patrícia Gomes" }, veiculo: { id: 508, modelo: "Yamaha NMax 160", placa: "SBC0J44" },
    periodicidade: "mensal", inicio: "2026-09-15T12:00:00Z", fim: "2026-10-15T12:00:00Z",
    situacao: { codigo: "cancelamento_pendente", rotulo: "Pedido de cancelamento", tom: "alerta" },
    pagamento: { rotulo: "Multa R$ 84,80", tom: "neutro", em_aberto_centavos: 0 },
    acao: { codigo: "abrir", rotulo: "Abrir" }, sinais: { cancelamento_pendente: true },
    corpo: { periodoCentavos: 159000, diariaCentavos: 6990, caucaoCentavos: 50000, kmSaida: 5120, contrato: { status: "assinado", modelo: "Locação mensal", assinadoEm: "2026-09-15T12:20:00Z" } },
    parcelas: [["parcela", "2026-09-15", 159000, "paga", "pix"], ["caucao", "2026-09-15", 50000, "paga", "pix"]],
    cancelamento: { status: "pendente", data: "2026-10-07", multa: 8480, credito: 37100, devolver: 28620, motivo: "Cliente mudou de cidade" },
    eventos: [["2026-09-15T12:00:00Z", "Locação criada por Bruna Alves", ""], ["2026-10-07T14:10:00Z", "Pedido de cancelamento", "Bruna Alves · aguardando o gerente"]],
  },
  {
    id: 2848, status: "ativa", cliente: { id: 1214, nome: "Diego Martins" }, veiculo: { id: 513, modelo: "Renault Kwid Zen", placa: "RKP3D26" },
    periodicidade: "diaria", inicio: "2026-10-06T12:00:00Z", fim: "2026-10-10T12:00:00Z",
    situacao: { codigo: "ativa", rotulo: "Ativa", tom: "sucesso" },
    pagamento: { rotulo: "Cartão", tom: "sucesso", em_aberto_centavos: 0 },
    acao: { codigo: "abrir", rotulo: "Abrir" },
    corpo: { periodoCentavos: 10900, diariaCentavos: 10900, caucaoCentavos: 80000, kmSaida: 52100, contrato: { status: "assinado", modelo: "Locação diária", assinadoEm: "2026-10-06T12:20:00Z" } },
    parcelas: [["parcela", "2026-10-06", 43600, "paga", "cartao"], ["caucao", "2026-10-06", 80000, "paga", "cartao"]],
    eventos: [["2026-10-06T12:00:00Z", "Locação criada por Rodrigo Pinheiro", ""], ["2026-10-06T12:20:00Z", "Contrato assinado pelo cliente", "assinatura no celular · IP registrado"]],
  },
];

const ROTULO_PERIODICIDADE: Record<Periodicidade, string> = { diaria: "diária", semanal: "semana", mensal: "mês" };
const FORMA: Record<string, string> = { pix: "pix", pix_automatico: "pix_automatico", cartao: "cartao" };
const VENDEDOR = { id: 3, nome: "Bruna Alves" };
const FILIAL = { id: 1, nome: "Filial Centro" };

const ativa = (s: Semente) => s.status === "ativa" || s.status === "devolucao_atrasada";

function acoesDe(s: Semente, perfil: Perfil | null) {
  const cria = perfil === "administrador" || perfil === "gerente" || perfil === "vendedor";
  const emCurso = !!s.cancelamento;
  const cancelar: "direto" | "pedir" | false =
    perfil === "administrador" || perfil === "gerente" ? "direto" : perfil === "vendedor" ? "pedir" : false;
  return {
    editar: false,
    confirmar: false,
    renovar: cria && ativa(s) && !emCurso,
    registrar_devolucao: ativa(s),
    trocar_veiculo: cria && s.status === "ativa" && !emCurso && !s.trocaPendente,
    cancelar: s.status === "encerrada" || s.status === "cancelada" || emCurso ? (false as const) : cancelar,
    imprimir_contrato: !!s.corpo.contrato && perfil !== "vistoriador",
    reenviar_contrato: !!s.corpo.contrato && perfil !== "vistoriador",
    continuar_vistoria: false,
    receber: false,
  };
}

function resumo(s: Semente): LocacaoResumo {
  return {
    id: s.id,
    codigo: `LOC-${s.id}`,
    status: s.status,
    cliente: s.cliente,
    veiculo: s.veiculo,
    periodicidade: s.periodicidade,
    plano_especial: null,
    inicio: s.inicio,
    fim_previsto: s.fim,
    sinais: { pagamento_atrasado: false, devolve_hoje: false, cancelamento_pendente: false, ...s.sinais },
    situacao: s.situacao,
    pagamento: s.pagamento,
    acao_principal: s.acao,
  };
}

function parcelas(s: Semente): ParcelaDaLocacao[] {
  const total = s.parcelas.filter((p) => p[0] === "parcela").length;
  let n = 0;
  return s.parcelas.map(([tipo, vencimento, valor, status, forma], i) => ({
    id: s.id * 10 + i,
    tipo,
    numero: tipo === "parcela" ? ++n : null,
    total_parcelas: tipo === "parcela" ? total : null,
    vencimento,
    valor_centavos: valor,
    status,
    forma: forma ? (FORMA[forma] ?? forma) : null,
    pago_em: status === "paga" ? `${vencimento}T12:30:00Z` : null,
    observacao: tipo === "caucao" ? "Devolver na entrega" : null,
  }));
}

function detalhe(s: Semente): LocacaoCompleta {
  const perfil = perfilAtualFalso();
  const vistoriador = perfil === "vistoriador";
  const ps = parcelas(s);
  const pago = ps.filter((p) => p.status === "paga").reduce((a, p) => a + p.valor_centavos, 0);
  const faltam = Math.round((Date.parse(s.fim) - Date.parse(AGORA_DO_SEED)) / 60000);
  const periodos = Math.max(1, Math.round((Date.parse(s.fim) - Date.parse(s.inicio)) / (s.periodicidade === "diaria" ? DIA : s.periodicidade === "semanal" ? 7 * DIA : 30 * DIA)));
  const base: LocacaoCompleta = {
    ...resumo(s),
    filial: FILIAL,
    vendedor: VENDEDOR,
    periodos,
    precos: {
      valor_periodo_centavos: s.corpo.periodoCentavos,
      diaria_centavos: s.corpo.diariaCentavos,
      caucao_centavos: s.corpo.caucaoCentavos,
      desconto_pct: s.desconto ?? "0.00",
      assinado_em_preco_de: s.inicio.slice(0, 10),
    },
    desconto: null,
    extras: (s.extras ?? []).map((nome, i) => ({ id: i + 1, nome, quantidade: 1, valor_centavos: 0, cobranca: "por_periodo" })),
    km_saida: s.corpo.kmSaida,
    km_livre: true,
    forma_pagamento: s.parcelas.find((p) => p[4])?.[4] ?? "pix",
    parcelamento_mensal: null,
    primeiro_vencimento: s.inicio.slice(0, 10),
    condicoes: {
      vistoria_saida_ok_em: s.corpo.kmSaida ? s.inicio : null,
      contrato_assinado_em: s.corpo.contrato?.assinadoEm ?? null,
      primeiro_pagamento_em: ps.some((p) => p.status === "paga") && ps.filter((p) => p.tipo === "caucao").every((p) => p.status === "paga") ? s.inicio : null,
    },
    parcelas: ps,
    total_pago_centavos: pago,
    contrato: s.corpo.contrato
      ? { id: s.id + 100, status: s.corpo.contrato.status, modelo: s.corpo.contrato.modelo, versao: 3, enviado_em: s.inicio, assinado_em: s.corpo.contrato.assinadoEm, pdf_disponivel: s.corpo.contrato.status === "assinado" }
      : null,
    devolucao: {
      prevista_para: s.fim,
      faltam_minutos: faltam,
      aviso_atraso: `Se atrasar, cobra R$ ${(s.corpo.diariaCentavos / 100).toFixed(2).replace(".", ",")} por dia a mais (diária)`,
      devolucao_id: s.devolucaoId ?? null,
    },
    trechos: [{ veiculo: s.veiculo.placa, inicio: s.inicio, fim: null }],
    cancelamento: s.cancelamento
      ? {
          status: s.cancelamento.status,
          pedido_aprovacao_id: 88,
          antes_da_retirada: false,
          data: s.cancelamento.data,
          multa_centavos: s.cancelamento.multa,
          credito_centavos: s.cancelamento.credito,
          devolver_centavos: s.cancelamento.devolver,
          cobrar_centavos: 0,
          motivo: s.cancelamento.motivo,
        }
      : null,
    acoes: acoesDe(s, perfil),
  };
  if (!vistoriador) return base;
  // O vistoriador não recebe nenhum valor: sem pagamento, preços, parcelas, extras nem desconto (docs/api/locacoes.md).
  const sem: Partial<LocacaoCompleta> = { ...base };
  delete sem.pagamento;
  delete sem.precos;
  delete sem.desconto;
  delete sem.extras;
  delete sem.parcelas;
  delete sem.total_pago_centavos;
  return sem as LocacaoCompleta;
}

function achar(id: number): Semente {
  const s = SEMENTES.find((x) => x.id === id);
  if (!s) throw new ErroApi(404, "nao_encontrado", "Locação não encontrada");
  return s;
}

function exigirCria() {
  const p = perfilAtualFalso();
  if (p !== "administrador" && p !== "gerente" && p !== "vendedor") throw new ErroApi(403, "sem_permissao", "Você não tem permissão para esta ação");
}

const iso = (ms: number) => new Date(ms).toISOString();
const dia = (ms: number) => new Date(ms - 3 * 3600_000).toISOString().slice(0, 10);

/** Fim e parcelas de `periodos` períodos a partir de `de` (o fim previsto atual), ao preço de hoje. */
function parcelasDe(s: Semente, periodos: number): { fim: string; parcelas: ParcelaPrevista[] } {
  const passo = s.periodicidade === "diaria" ? DIA : s.periodicidade === "semanal" ? 7 * DIA : 30 * DIA;
  const fimAtual = Date.parse(s.fim);
  const numeroInicial = s.parcelas.filter((p) => p[0] === "parcela").length;
  return {
    fim: iso(fimAtual + periodos * passo),
    parcelas: Array.from({ length: periodos }, (_, i) => ({ numero: numeroInicial + i + 1, vencimento: dia(fimAtual + i * passo), valor_centavos: s.corpo.periodoCentavos })),
  };
}

function simularCancelamento(s: Semente, data?: string | null): SimulacaoDoCancelamento {
  const diaPedido = data ?? dia(Date.parse(AGORA_DO_SEED));
  if (diaPedido < dia(Date.parse(AGORA_DO_SEED))) throw new ErroApi(400, "validacao", "A data não pode ser antes de hoje", undefined, { data: "A data não pode ser antes de hoje" });
  if (s.status === "encerrada" || s.status === "cancelada") throw new ErroApi(409, "transicao_locacao", "Esta locação já foi encerrada");
  if (s.status === "aguardando_retirada") {
    const pago = s.parcelas.filter((p) => p[3] === "paga").reduce((a, p) => a + p[2], 0);
    return { antes_da_retirada: true, periodo_atual: null, dias_restantes: 0, valor_restante_centavos: 0, multa_centavos: 0, credito_semanas: { semanas: 0, valor_centavos: 0 }, credito_dias: { dias: 0, valor_centavos: 0 }, parcelas_canceladas_centavos: 0, devolver_centavos: pago, cobrar_centavos: 0, avisos: [] };
  }
  if (s.id === 2812) {
    return { antes_da_retirada: false, periodo_atual: { inicio: "2026-09-15", fim: "2026-10-15", dias: 30 }, dias_restantes: 8, valor_restante_centavos: 42400, multa_centavos: 8480, credito_semanas: { semanas: 1, valor_centavos: 37100 }, credito_dias: { dias: 0, valor_centavos: 0 }, parcelas_canceladas_centavos: 0, devolver_centavos: 28620, cobrar_centavos: 0, avisos: [] };
  }
  const restantes = Math.max(0, Math.ceil((Date.parse(`${dia(Date.parse(s.fim))}T12:00:00Z`) - Date.parse(`${diaPedido}T12:00:00Z`)) / DIA));
  if (restantes === 0) throw new ErroApi(409, "sem_dias_restantes", "Não sobra nenhum dia até o fim previsto. Registre a devolução.");
  const diasDoPeriodo = s.periodicidade === "semanal" ? 7 : s.periodicidade === "mensal" ? 30 : 1;
  const restante = Math.round((s.corpo.periodoCentavos / diasDoPeriodo) * Math.min(restantes, diasDoPeriodo));
  const multa = s.periodicidade === "diaria" ? 0 : Math.max(Math.round(restante * 0.2), s.corpo.diariaCentavos);
  return {
    antes_da_retirada: false,
    periodo_atual: null,
    dias_restantes: restantes,
    valor_restante_centavos: restante,
    multa_centavos: multa,
    credito_semanas: { semanas: 0, valor_centavos: 0 },
    credito_dias: { dias: 0, valor_centavos: 0 },
    parcelas_canceladas_centavos: 0,
    devolver_centavos: 0,
    cobrar_centavos: multa,
    avisos: s.periodicidade === "diaria" ? [{ codigo: "LOC-12", mensagem: "O acerto final usa a hora da devolução." }] : [],
  };
}

function abaDe(s: Semente, aba: AbaLocacoes): boolean {
  const r = resumo(s);
  switch (aba) {
    case "abertas": return ["aguardando_retirada", "ativa", "devolucao_atrasada"].includes(s.status);
    case "precisam_acao": return r.status === "devolucao_atrasada" || r.sinais.pagamento_atrasado || r.sinais.cancelamento_pendente || r.situacao.codigo === "aguardando_assinatura";
    case "devolvem_hoje": return r.sinais.devolve_hoje;
    case "encerradas": return s.status === "encerrada";
    case "canceladas": return s.status === "cancelada";
    case "rascunhos": return s.status === "rascunho";
  }
}

const normalizar = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/-/g, "");

export const locacoesFalso = {
  async listar(f: FiltroLocacoes = {}): Promise<ListaLocacoes> {
    await pausa(200);
    if (perfilAtualFalso() === "vistoriador") throw new ErroApi(403, "sem_permissao", "Você não tem permissão para ver as locações");
    const aba = f.aba ?? "abertas";
    let lista = SEMENTES.filter((s) => abaDe(s, aba));
    if (f.periodicidade) lista = lista.filter((s) => s.periodicidade === f.periodicidade);
    if (f.veiculo) lista = lista.filter((s) => s.veiculo.id === f.veiculo);
    if (f.cliente) lista = lista.filter((s) => s.cliente.id === f.cliente);
    if (f.busca) {
      const b = normalizar(f.busca);
      lista = lista.filter((s) => normalizar(`${s.cliente.nome}LOC${s.id}${s.veiculo.placa}`).includes(b));
    }
    lista = [...lista].sort((a, b) => (f.ordem === "-inicio" ? b.inicio.localeCompare(a.inicio) : 0));
    const inicio = Number(f.cursor ?? 0);
    const conta = (a: AbaLocacoes) => SEMENTES.filter((s) => abaDe(s, a)).length;
    // Os totais da carteira inteira (42 ativas, 310 encerradas) vêm da API; as demais contagens saem das linhas de exemplo.
    return {
      indicadores: {
        ativas: 42,
        frota_alugada_pct: "71.00",
        devolvem_hoje: conta("devolvem_hoje"),
        devolvem_hoje_ate_12h: 0,
        devolucao_atrasada: 1,
        devolucao_atrasada_destaque: "Rafael · 25 dias",
        pagamentos_atrasados: 2,
        pagamentos_atrasados_centavos: 164640,
      },
      contagens: { abertas: 42, precisam_acao: conta("precisam_acao"), devolvem_hoje: conta("devolvem_hoje"), encerradas: 310, canceladas: 12, rascunhos: 0 },
      resultados: lista.slice(inicio, inicio + TAMANHO).map(resumo),
      proximo: inicio + TAMANHO < lista.length ? String(inicio + TAMANHO) : null,
      anterior: inicio > 0 ? String(Math.max(inicio - TAMANHO, 0)) : null,
    };
  },

  async obter(id: number): Promise<LocacaoCompleta> {
    await pausa(150);
    return detalhe(achar(id));
  },

  async historico(id: number): Promise<HistoricoDaLocacao> {
    await pausa(150);
    const s = achar(id);
    const vistoriador = perfilAtualFalso() === "vistoriador";
    return {
      resultados: s.eventos
        .filter(([, rotulo]) => !(vistoriador && /pagamento/i.test(rotulo)))
        .map(([em, rotulo, detalhe]) => ({ em, rotulo, detalhe, tipo: /vistoria/i.test(rotulo) ? "vistoria" : /pagamento/i.test(rotulo) ? "pagamento" : "locacao" })),
    };
  },

  async simularRenovacao(id: number, corpo: { periodos?: number | null; fim_previsto?: string | null }): Promise<SimulacaoDaRenovacao> {
    await pausa(200);
    exigirCria();
    const s = achar(id);
    if (!ativa(s)) throw new ErroApi(409, "transicao_locacao", "Só é possível renovar uma locação ativa");
    if (s.cancelamento) throw new ErroApi(409, "cancelamento_em_andamento", "Há um cancelamento em andamento nesta locação");
    const periodos = corpo.periodos ?? 0;
    if (!Number.isInteger(periodos) || periodos < 1) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { periodos: "Informe 1 período ou mais" });
    const { fim, parcelas: novas } = parcelasDe(s, periodos);
    return { fim_previsto_atual: s.fim, fim_previsto: fim, periodos, valor_periodo_centavos: s.corpo.periodoCentavos, parcelas_novas: novas, total_centavos: novas.reduce((a, p) => a + p.valor_centavos, 0) };
  },

  async renovar(id: number, corpo: { periodos?: number | null; fim_previsto?: string | null }): Promise<LocacaoCompleta> {
    const sim = await this.simularRenovacao(id, corpo);
    const s = achar(id);
    s.fim = sim.fim_previsto ?? s.fim;
    for (const p of sim.parcelas_novas) s.parcelas.splice(s.parcelas.findIndex((x) => x[0] === "caucao"), 0, ["parcela", p.vencimento, p.valor_centavos, "aberta"]);
    s.eventos.push([AGORA_DO_SEED, "Renovação", `${sim.periodos} ${sim.periodos === 1 ? ROTULO_PERIODICIDADE[s.periodicidade] : "períodos"} a mais`]);
    return detalhe(s);
  },

  async simularCancelamento(id: number, corpo: { data?: string | null } = {}): Promise<SimulacaoDoCancelamento> {
    await pausa(200);
    return simularCancelamento(achar(id), corpo.data);
  },

  /** 200 com a locação quando vale na hora; 202 com o pedido quando quem pede é o vendedor. */
  async cancelar(id: number, corpo: { motivo: string; data?: string | null; forma_devolucao: FormaDevolucaoCancelamento }): Promise<{ status: 200; locacao: LocacaoCompleta } | { status: 202; pedido: PedidoDeCancelamento }> {
    await pausa(300);
    const s = achar(id);
    const acoes = acoesDe(s, perfilAtualFalso());
    if (!acoes.cancelar) throw new ErroApi(s.cancelamento ? 409 : 403, s.cancelamento ? "cancelamento_em_andamento" : "sem_permissao", s.cancelamento ? "Já existe um pedido de cancelamento para esta locação" : "Você não tem permissão para cancelar");
    if (!corpo.motivo.trim()) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { motivo: "Informe o motivo" });
    const sim = simularCancelamento(s, corpo.data);
    const base = { data: corpo.data ?? dia(Date.parse(AGORA_DO_SEED)), multa: sim.multa_centavos, credito: sim.credito_semanas.valor_centavos, devolver: sim.devolver_centavos, motivo: corpo.motivo };
    if (acoes.cancelar === "pedir") {
      s.cancelamento = { status: "pendente", ...base };
      s.sinais = { ...s.sinais, cancelamento_pendente: true };
      s.situacao = { codigo: "cancelamento_pendente", rotulo: "Pedido de cancelamento", tom: "alerta" };
      s.pagamento = { rotulo: `Multa R$ ${(sim.multa_centavos / 100).toFixed(2).replace(".", ",")}`, tom: "neutro", em_aberto_centavos: 0 };
      s.eventos.push([AGORA_DO_SEED, "Pedido de cancelamento", "aguardando o gerente"]);
      return { status: 202, pedido: { id: 88, tipo: "APR-02", status: "pendente" } as PedidoDeCancelamento };
    }
    if (sim.antes_da_retirada) {
      s.status = "cancelada";
      s.situacao = { codigo: "cancelada", rotulo: "Cancelada", tom: "neutro" };
    } else {
      s.cancelamento = { status: "aprovado", ...base };
      s.situacao = { codigo: "cancelamento_aprovado", rotulo: "Encerramento aprovado", tom: "info" };
    }
    s.eventos.push([AGORA_DO_SEED, sim.antes_da_retirada ? "Locação cancelada" : "Encerramento antecipado aprovado", corpo.motivo]);
    return { status: 200, locacao: detalhe(s) };
  },

  async trocarVeiculo(id: number, corpo: { veiculo_novo_id: number; motivo: string }): Promise<TrocaPedida> {
    await pausa(300);
    exigirCria();
    const s = achar(id);
    if (s.status !== "ativa") throw new ErroApi(409, "transicao_locacao", "Só é possível trocar o veículo de uma locação ativa");
    if (s.trocaPendente) throw new ErroApi(409, "troca_pendente", "Já existe uma troca de veículo pendente nesta locação");
    if (!corpo.motivo.trim()) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { motivo: "Informe o motivo" });
    const novo = await veiculosFalso.obter(corpo.veiculo_novo_id);
    if (novo.status !== "disponivel") throw new ErroApi(422, "LOC-03", "Veículo indisponível no período");
    s.trocaPendente = true;
    s.devolucaoId = s.id * 10;
    s.eventos.push([AGORA_DO_SEED, "Troca de veículo pedida", corpo.motivo]);
    return { troca: { id: s.id * 10, status: "pendente", devolucao_vistoria_id: s.id * 10 + 1, saida_vistoria_id: s.id * 10 + 2 } };
  },

  async reenviarContrato(id: number): Promise<void> {
    await pausa(250);
    const s = achar(id);
    if (!s.corpo.contrato) throw new ErroApi(409, "sem_contrato", "Esta locação ainda não tem contrato");
    s.eventos.push([AGORA_DO_SEED, s.corpo.contrato.status === "assinado" ? "Contrato reenviado" : "Link de assinatura reenviado", "WhatsApp"]);
  },

  async pdfDoContrato(id: number): Promise<{ url: string; url_expira_em: string }> {
    await pausa(200);
    achar(id);
    return { url: `/contratos/LOC-${id}.pdf`, url_expira_em: iso(Date.parse(AGORA_DO_SEED) + 15 * 60_000) };
  },
};
