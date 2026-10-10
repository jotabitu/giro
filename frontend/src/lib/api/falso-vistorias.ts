// DADOS FALSOS de vistorias, devolução e acerto enquanto a sessão real (T-011) não liga o app à API (contrato: docs/api/vistorias.md).
// Só ./index.ts importa este arquivo. A "API" decide pendências, acerto, resultado, botão e erros; a tela só mostra.
// Números do caso de referência (DEV-03): LOC-2836, tanque de 16 L, litro a R$ 5,50: combustível 3200 + retrovisor 8500, caução 30000, devolve 18300.
import { clientesFalso } from "./falso-clientes";
import { pausa, perfilAtualFalso } from "./falso";
import { aplicarDevolucaoEncerrada, aplicarSaidaConcluida, dadosDaLocacaoParaVistoria, AGORA_DO_SEED, type DadosDaLocacaoParaVistoria } from "./falso-locacoes";
import { ErroApi } from "./tipos";
import type {
  AcertoDaDevolucao,
  AgendaDoDia,
  AvariaAberta,
  Combustivel,
  DevolucaoCompleta,
  DiaDaAgenda,
  EdicaoDaVistoria,
  FormaDevolucaoAcerto,
  FotoDaVistoria,
  ItemDaAgenda,
  ItemDoAcerto,
  NovaAvaria,
  NovoItemDoAcerto,
  PendenciaDaVistoria,
  PosicaoFoto,
  Vistoria,
} from "./tipos-vistorias";

const OBRIGATORIAS: PosicaoFoto[] = ["frente", "traseira", "lado_esquerdo", "lado_direito", "painel"];
const ROTULO_POSICAO: Record<PosicaoFoto, string> = { frente: "Frente", traseira: "Traseira", lado_esquerdo: "Lateral esquerda", lado_direito: "Lateral direita", painel: "Painel e hodômetro", avaria: "Foto de avaria" };
const NIVEL: Record<Combustivel, number> = { reserva: 0, um_quarto: 0.25, meio: 0.5, tres_quartos: 0.75, cheio: 1 };
const FRACAO: Record<number, string> = { 0.25: "1/4", 0.5: "1/2", 0.75: "3/4", 1: "tanque cheio" };
const ITENS_DO_RAMO: [string, string][] = [
  ["retrovisores", "Retrovisores"],
  ["luzes", "Faróis, setas e buzina"],
  ["pneus_freios", "Pneus e freios"],
  ["riscos", "Riscos ou amassados"],
  ["capacete", "Capacete entregue"],
  ["documento", "Documento (CRLV) no veículo"],
];
const TANQUE_L = 16;
const PRECO_LITRO = 550;
const TAXA_COMBUSTIVEL = 1000;
const DIA = 86_400_000;

const reais = (c: number) => `R$ ${(c / 100).toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".")}`;
const dataBR = (iso: string) => new Date(iso).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo", day: "2-digit", month: "2-digit" });
const diaDe = (iso: string) => new Date(Date.parse(iso) - 3 * 3600_000).toISOString().slice(0, 10);

function imagem(rotulo: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="220"><rect width="320" height="220" fill="#d9d9de"/><text x="160" y="116" font-family="sans-serif" font-size="16" fill="#555" text-anchor="middle">${rotulo}</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

let proximaFoto = 900;
const foto = (posicao: PosicaoFoto, em: string): FotoDaVistoria => ({ id: proximaFoto++, posicao, tirada_em: em, url: imagem(ROTULO_POSICAO[posicao]), url_expira_em: new Date(Date.parse(AGORA_DO_SEED) + 15 * 60_000).toISOString() });

type Registro = {
  v: Vistoria;
  /** Km atual do veículo (`VEI-01`): a vistoria não aceita km menor. */
  kmDoVeiculo: number;
  dados: DadosDaLocacaoParaVistoria;
  extras: { valor_centavos: number | null }[];
};
const VISTORIAS = new Map<number, Registro>();
let proximaVistoria = 3100;

function itensIniciais(dados: DadosDaLocacaoParaVistoria, ok: boolean | null): Vistoria["itens"] {
  return [...ITENS_DO_RAMO.map(([codigo, rotulo]) => ({ codigo, rotulo, ok, observacao: null })), ...dados.extras.map((e, i) => ({ codigo: `extra_${i + 1}`, rotulo: e.replace(/ extra$/i, "") === e ? e : `${e.replace(/ extra$/i, "")} entregue`, ok, observacao: null }))];
}

function resumoDaLocacao(d: DadosDaLocacaoParaVistoria, vistoriador: boolean): Vistoria["resumo_locacao"] {
  return { periodicidade: d.periodicidade, inicio: d.inicio, fim_previsto: d.fim, km_livre: true, caucao_paga: d.caucaoPaga, ...(vistoriador ? {} : { diaria_centavos: d.diariaCentavos, caucao_centavos: d.caucaoCentavos }) };
}

function novaVistoria(d: DadosDaLocacaoParaVistoria, tipo: "saida" | "devolucao", cnh: string | null, km: number, ultima: { km: number; em: string }): Registro {
  const id = proximaVistoria++;
  const v: Vistoria = {
    id,
    tipo,
    status: "rascunho",
    locacao: { id: d.id, codigo: d.codigo },
    veiculo: { id: d.veiculo.id, placa: d.veiculo.placa, modelo: d.veiculo.modelo, ano: 2025 },
    cliente: { nome: d.cliente.nome, cnh },
    km: null,
    km_ultima_leitura: ultima,
    combustivel: null,
    fotos: [],
    fotos_obrigatorias: { feitas: 0, total: 5, faltam: [...OBRIGATORIAS] },
    itens: itensIniciais(d, null),
    avarias: [],
    observacoes: null,
    responsavel: { id: 5, nome: "João Silva" },
    concluida_em: null,
    substitui: null,
    motivo_correcao: null,
    vigente: true,
    pendencias: [],
    pode_concluir: false,
    resumo_locacao: resumoDaLocacao(d, false),
  };
  void km;
  const r: Registro = { v, kmDoVeiculo: ultima.km, dados: d, extras: [] };
  VISTORIAS.set(id, r);
  return r;
}

/** Recalcula o que a API recalcula a cada leitura: fotos obrigatórias, pendências e se pode concluir. */
function montar(r: Registro): Vistoria {
  const v = r.v;
  const feitas = OBRIGATORIAS.filter((p) => v.fotos.some((f) => f.posicao === p));
  const faltam = OBRIGATORIAS.filter((p) => !feitas.includes(p));
  const pendencias: string[] = [];
  if (faltam.length > 0) pendencias.push("fotos");
  if (v.km === null) pendencias.push("km");
  if (!v.combustivel) pendencias.push("combustivel");
  if (v.itens.some((i) => i.ok === null)) pendencias.push("itens");
  const vistoriador = perfilAtualFalso() === "vistoriador";
  return { ...v, fotos_obrigatorias: { feitas: feitas.length, total: OBRIGATORIAS.length, faltam }, pendencias, pode_concluir: pendencias.length === 0 && v.status === "rascunho", resumo_locacao: resumoDaLocacao(r.dados, vistoriador) };
}

function achar(id: number): Registro {
  const r = VISTORIAS.get(id);
  if (!r) throw new ErroApi(404, "nao_encontrado", "Vistoria não encontrada");
  return r;
}

function exigirVistoria() {
  const p = perfilAtualFalso();
  if (p !== "administrador" && p !== "gerente" && p !== "vendedor" && p !== "vistoriador") throw new ErroApi(403, "sem_permissao", "Você não tem permissão para esta ação");
}

function exigirRascunho(r: Registro) {
  if (r.v.status !== "rascunho") throw new ErroApi(409, "vistoria_concluida", "A vistoria já foi concluída e não pode mais ser editada");
}

// ---- Sementes -------------------------------------------------------------------------------------------------------

function semear() {
  // LOC-2856, Lucas: vistoria de saída em rascunho, a da referência (3 de 5 fotos, km 3.120, 3/4, 1 avaria já registrada).
  const lucas = dadosDaLocacaoParaVistoria(2856);
  const r = novaVistoria(lucas, "saida", "Categoria A · válida", 3120, { km: 3118, em: "2026-10-05" });
  VISTORIAS.delete(r.v.id);
  r.v.id = 3001;
  VISTORIAS.set(3001, r);
  r.v.km = 3120;
  r.v.combustivel = "tres_quartos";
  r.v.fotos = [foto("frente", "2026-10-07T12:41:00Z"), foto("traseira", "2026-10-07T12:41:30Z"), foto("lado_esquerdo", "2026-10-07T12:42:00Z")];
  r.v.itens = itensIniciais(lucas, true).map((i) => (i.codigo === "riscos" ? { ...i, ok: null } : i));
  r.v.avarias = [{ id: 51, descricao: "Risco no tanque, lado esquerdo", preexistente: true, foto_id: null, vai_para_oficina: false, origem: "Registrado na vistoria anterior; não será cobrado do cliente na devolução." }];
  r.kmDoVeiculo = 3118;
}

type SementeDevolucao = { id: number; locacaoId: number; saidaKm: number; chegadaKm: number | null; chegadaCombustivel: Combustivel | null; fotos: boolean; devolvidaEm: string; avaria?: { descricao: string; valor: number | null } };
const SEMENTES_DEVOLUCAO: SementeDevolucao[] = [
  // Juliana: no horário, a conta do caso de referência.
  { id: 701, locacaoId: 2836, saidaKm: 18402, chegadaKm: 19630, chegadaCombustivel: "tres_quartos", fotos: true, devolvidaEm: "2026-10-14T20:30:00Z", avaria: { descricao: "Retrovisor esquerdo", valor: 8500 } },
  // Rafael: 25 dias de atraso, parcelas em aberto e a caução não cobre.
  { id: 702, locacaoId: 2790, saidaKm: 9120, chegadaKm: null, chegadaCombustivel: null, fotos: false, devolvidaEm: AGORA_DO_SEED },
  // Carlos: devolução antes do fim previsto, sem encerramento aprovado (DEV-07).
  { id: 703, locacaoId: 2841, saidaKm: 17210, chegadaKm: null, chegadaCombustivel: null, fotos: false, devolvidaEm: AGORA_DO_SEED },
];

type Devolucao = {
  id: number;
  locacaoId: number;
  chegadaId: number;
  saidaId: number;
  status: "rascunho" | "concluida";
  forma: FormaDevolucaoAcerto | null;
  informados: ItemDoAcerto[];
  devolvidaEm: string;
  concluidaEm: string | null;
  reciboEm: string | null;
};
const DEVOLUCOES = new Map<number, Devolucao>();
let proximoItem = 8000;

function criarDevolucao(s: { id: number; locacaoId: number; saidaKm: number; chegadaKm: number | null; chegadaCombustivel: Combustivel | null; fotos: boolean; devolvidaEm: string; avaria?: SementeDevolucao["avaria"] }): Devolucao {
  const d = dadosDaLocacaoParaVistoria(s.locacaoId);
  const saida = novaVistoria({ ...d, extras: d.extras }, "saida", "Categoria A · válida", s.saidaKm, { km: s.saidaKm, em: "2026-09-30" });
  Object.assign(saida.v, { status: "concluida", km: s.saidaKm, combustivel: "cheio", concluida_em: d.inicio, itens: itensIniciais(d, true) });
  saida.v.fotos = OBRIGATORIAS.map((p) => foto(p, d.inicio));
  const chegada = novaVistoria(d, "devolucao", "Categoria A · válida", s.chegadaKm ?? 0, { km: s.saidaKm, em: "2026-09-30" });
  chegada.v.km = s.chegadaKm;
  chegada.v.combustivel = s.chegadaCombustivel;
  if (s.fotos) {
    chegada.v.fotos = OBRIGATORIAS.map((p) => foto(p, s.devolvidaEm));
    chegada.v.itens = itensIniciais(d, true).map((i) => (i.codigo === "retrovisores" && s.avaria ? { ...i, ok: false, observacao: s.avaria.descricao } : i));
  }
  if (s.avaria) {
    const f = chegada.v.fotos[1] ?? foto("avaria", s.devolvidaEm);
    chegada.v.avarias = [{ id: 52, descricao: s.avaria.descricao, preexistente: false, foto_id: f.id, vai_para_oficina: false, valor_centavos: s.avaria.valor, origem: null }];
  }
  chegada.kmDoVeiculo = s.saidaKm;
  const dev: Devolucao = { id: s.id, locacaoId: s.locacaoId, chegadaId: chegada.v.id, saidaId: saida.v.id, status: "rascunho", forma: s.id === 701 ? "pix" : null, informados: [], devolvidaEm: s.devolvidaEm, concluidaEm: null, reciboEm: null };
  DEVOLUCOES.set(dev.id, dev);
  return dev;
}

let semeado = false;
function garantirSementes() {
  if (semeado) return;
  semeado = true;
  semear();
  for (const s of SEMENTES_DEVOLUCAO) criarDevolucao(s);
}

// ---- Acerto ---------------------------------------------------------------------------------------------------------

function combustivelDoAcerto(saida: Combustivel | null, agora: Combustivel | null, nomeDoVeiculo?: string): ItemDoAcerto | null {
  if (!saida || !agora) return null;
  const faltou = NIVEL[saida] - NIVEL[agora];
  const base = { id: 1, tipo: "combustivel" as const, modo: "calculado" as const, avaria_id: null, conta_id: null };
  if (faltou <= 0) return { ...base, descricao: "Combustível", valor_centavos: 0 };
  const litros = TANQUE_L * faltou;
  const valor = Math.round(litros * PRECO_LITRO) + TAXA_COMBUSTIVEL;
  return { ...base, descricao: `Combustível${nomeDoVeiculo ? ` da ${nomeDoVeiculo}` : ""} (faltou ${FRACAO[faltou]} tanque, ${litros} L × ${reais(PRECO_LITRO)} + ${reais(TAXA_COMBUSTIVEL)})`, valor_centavos: valor };
}

/** O devido numa parcela vencida: principal, multa de 2% e juros de 1% ao mês pro rata (`FIN-03`). */
function devidoDaParcela(principal: number, dias: number) {
  const multa = Math.round(principal * 0.02);
  const juros = Math.round((principal * 0.01 * dias) / 30);
  return { total: principal + multa + juros, multa, juros };
}

function acertoDe(dev: Devolucao): AcertoDaDevolucao {
  const chegada = achar(dev.chegadaId).v;
  const saida = achar(dev.saidaId).v;
  const d = dadosDaLocacaoParaVistoria(dev.locacaoId);
  const itens: ItemDoAcerto[] = [];
  const combustivel = combustivelDoAcerto(saida.combustivel, chegada.combustivel);
  if (combustivel) itens.push(combustivel);
  for (const a of chegada.avarias.filter((x) => !x.preexistente)) {
    const informado = dev.informados.find((i) => i.avaria_id === a.id);
    itens.push({ id: informado?.id ?? 2000 + a.id, tipo: "avaria", descricao: a.descricao, valor_centavos: informado?.valor_centavos ?? a.valor_centavos ?? 0, modo: "informado", avaria_id: a.id, conta_id: null });
  }
  const atrasoDias = Math.max(0, Math.floor((Date.parse(dev.devolvidaEm) - Date.parse(d.fim)) / DIA));
  itens.push({ id: 3, tipo: "atraso", descricao: atrasoDias > 0 ? `Atraso (${atrasoDias} ${atrasoDias === 1 ? "diária" : "diárias"} × ${reais(d.diariaCentavos)})` : "Atraso", valor_centavos: atrasoDias * d.diariaCentavos, modo: "calculado", avaria_id: null, conta_id: null });
  const hoje = diaDe(dev.devolvidaEm);
  for (const p of d.parcelasAbertas.filter((x) => x.vencimento <= hoje)) {
    const dias = Math.max(0, Math.round((Date.parse(`${hoje}T12:00:00Z`) - Date.parse(`${p.vencimento}T12:00:00Z`)) / DIA));
    const devido = devidoDaParcela(p.valorCentavos, dias);
    const venc = dias === 0 ? `vence hoje, ${dataBR(`${p.vencimento}T12:00:00Z`)}` : `venceu em ${dataBR(`${p.vencimento}T12:00:00Z`)} (multa ${reais(devido.multa)} e juros ${reais(devido.juros)})`;
    itens.push({ id: 4000 + p.numero, tipo: "parcela_aberta", descricao: `Parcela ${p.numero} de ${p.total} · ${venc}`, valor_centavos: devido.total, modo: "calculado", avaria_id: null, conta_id: 9000 + p.numero });
  }
  itens.push(...dev.informados.filter((i) => i.tipo !== "avaria"));
  const total = itens.reduce((a, i) => a + i.valor_centavos, 0);
  const saldo = d.caucaoCentavos - total;
  const tipo = saldo > 0 ? "devolver" : saldo < 0 ? "cobrar" : "zerado";
  const antecipada = diaDe(dev.devolvidaEm) < diaDe(d.fim) && !d.cancelamentoAprovado;
  return {
    status: dev.status === "concluida" ? "concluido" : "rascunho",
    caucao_centavos: d.caucaoCentavos,
    itens,
    creditos: [],
    total_cobrancas_centavos: total,
    total_creditos_centavos: 0,
    saldo_centavos: saldo,
    resultado: {
      tipo,
      valor_centavos: Math.abs(saldo),
      texto: tipo === "devolver" ? `Desconta ${reais(total)} da caução de ${reais(d.caucaoCentavos)}` : tipo === "cobrar" ? `A caução de ${reais(d.caucaoCentavos)} não cobre. O resto vira uma conta com vencimento em 3 dias` : "A caução cobre tudo",
      botao: tipo === "devolver" ? `Encerrar e devolver ${reais(saldo)}` : tipo === "cobrar" ? `Encerrar e cobrar ${reais(-saldo)}` : "Encerrar",
    },
    avisos: dev.status === "rascunho" && antecipada ? [{ codigo: "DEV-07", mensagem: "A devolução é antes do fim do contrato. Peça o encerramento antecipado ao gerente." }] : [],
    forma_devolucao: dev.forma,
  };
}

function comparacao(dev: Devolucao): DevolucaoCompleta["comparacao"] {
  const saida = achar(dev.saidaId).v;
  const chegada = achar(dev.chegadaId).v;
  const rodou = saida.km !== null && chegada.km !== null ? chegada.km - saida.km : null;
  const faltou = saida.combustivel && chegada.combustivel ? NIVEL[saida.combustivel] - NIVEL[chegada.combustivel] : 0;
  return {
    km: { saida: saida.km, agora: chegada.km, rodou, texto: rodou === null ? "Informe o km de agora" : `Rodou ${new Intl.NumberFormat("pt-BR").format(rodou)} km · plano com km livre` },
    combustivel: { saida: saida.combustivel, agora: chegada.combustivel, faltou: faltou > 0 ? `${FRACAO[faltou]} tanque` : null, litros_faltantes: faltou > 0 ? (TANQUE_L * faltou).toFixed(1) : null },
    fotos: (["lado_esquerdo", "painel", "frente", "traseira", "lado_direito"] as PosicaoFoto[]).flatMap((p) => {
      const s = saida.fotos.find((f) => f.posicao === p) ?? null;
      const a = chegada.fotos.find((f) => f.posicao === p) ?? null;
      return s || a ? [{ posicao: p, saida: s, agora: a }] : [];
    }),
    itens: chegada.itens.map((i) => ({ codigo: i.codigo, rotulo: i.rotulo, saida: "ok", agora: i.ok === null ? null : i.ok ? "ok" : (i.observacao ?? "com problema"), novo: i.ok === false })),
  };
}

function montarDevolucao(dev: Devolucao): DevolucaoCompleta {
  const d = dadosDaLocacaoParaVistoria(dev.locacaoId);
  const vistoriador = perfilAtualFalso() === "vistoriador";
  const base: DevolucaoCompleta = {
    id: dev.id,
    status: dev.status,
    locacao: { id: d.id, codigo: d.codigo, status: d.status, cliente: d.cliente.nome, veiculo: `${d.veiculo.modelo} · ${d.veiculo.placa}`, no_horario: diaDe(dev.devolvidaEm) <= diaDe(d.fim) && Date.parse(dev.devolvidaEm) <= Date.parse(d.fim) + 3600_000 },
    vistoria: montar(achar(dev.chegadaId)),
    comparacao: comparacao(dev),
    acerto: acertoDe(dev),
    devolvida_em: dev.devolvidaEm,
    concluida_em: dev.concluidaEm,
    recibo_enviado_em: dev.reciboEm,
  };
  if (!vistoriador) return base;
  const sem = { ...base } as Partial<DevolucaoCompleta>;
  delete sem.acerto;
  return sem as DevolucaoCompleta;
}

function exigirAcerto() {
  const p = perfilAtualFalso();
  if (p !== "administrador" && p !== "gerente" && p !== "vendedor") throw new ErroApi(403, "sem_permissao", "Você não tem permissão para o acerto");
}

function acharDevolucao(id: number): Devolucao {
  garantirSementes();
  const d = DEVOLUCOES.get(id);
  if (!d) throw new ErroApi(404, "nao_encontrado", "Devolução não encontrada");
  return d;
}

// ---- API falsa --------------------------------------------------------------------------------------------------------

export const vistoriasFalso = {
  /** POST /api/locacoes/{id}/vistorias/ com tipo "saida": 201 com o rascunho, ou 200 com o que já existe. */
  async iniciarSaida(locacaoId: number): Promise<Vistoria> {
    await pausa(200);
    garantirSementes();
    exigirVistoria();
    const d = dadosDaLocacaoParaVistoria(locacaoId);
    if (d.status !== "aguardando_retirada" && !d.trocaPendente) throw new ErroApi(409, "transicao_locacao", "A vistoria de saída só vale para uma locação aguardando a retirada");
    const existente = [...VISTORIAS.values()].find((r) => r.dados.id === locacaoId && r.v.tipo === "saida" && r.v.status === "rascunho");
    if (existente) return montar(existente);
    const cliente = await clientesFalso.obter(d.cliente.id);
    const cnh = "cnh" in cliente && cliente.cnh?.categoria ? `Categoria ${cliente.cnh.categoria} · válida` : null;
    return montar(novaVistoria(d, "saida", cnh, 0, { km: 7420, em: "2026-10-05" }));
  },

  async obter(id: number): Promise<Vistoria> {
    await pausa(150);
    garantirSementes();
    exigirVistoria();
    return montar(achar(id));
  },

  async editar(id: number, patch: EdicaoDaVistoria): Promise<Vistoria> {
    await pausa(200);
    garantirSementes();
    exigirVistoria();
    const r = achar(id);
    exigirRascunho(r);
    if (patch.km !== undefined) {
      if (patch.km !== null && (!Number.isInteger(patch.km) || patch.km < 0)) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { km: "Informe só números" });
      r.v.km = patch.km;
    }
    if (patch.combustivel !== undefined) r.v.combustivel = patch.combustivel;
    if (patch.observacoes !== undefined) r.v.observacoes = patch.observacoes;
    for (const i of patch.itens ?? []) {
      const item = r.v.itens.find((x) => x.codigo === i.codigo);
      if (item) Object.assign(item, { ok: i.ok, observacao: i.observacao ?? item.observacao });
    }
    return montar(r);
  },

  /** `multipart/form-data` com a posição e o arquivo. JPG ou PNG até 10 MB; a de posição fixa substitui a anterior. */
  async enviarFoto(id: number, posicao: PosicaoFoto, arquivo: File): Promise<FotoDaVistoria> {
    await pausa(300);
    garantirSementes();
    exigirVistoria();
    const r = achar(id);
    exigirRascunho(r);
    if (!["image/jpeg", "image/png"].includes(arquivo.type)) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { arquivo: "Envie uma foto em JPG ou PNG" });
    if (arquivo.size > 10 * 1024 * 1024) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { arquivo: "A foto passa de 10 MB. Envie uma menor." });
    const nova = foto(posicao, AGORA_DO_SEED);
    r.v.fotos = posicao === "avaria" ? [...r.v.fotos, nova] : [...r.v.fotos.filter((f) => f.posicao !== posicao), nova];
    return nova;
  },

  async registrarAvaria(id: number, a: NovaAvaria): Promise<Vistoria> {
    await pausa(200);
    garantirSementes();
    exigirVistoria();
    const r = achar(id);
    exigirRascunho(r);
    if (!a.descricao.trim()) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { descricao: "Descreva a avaria" });
    if (!r.v.fotos.some((f) => f.id === a.foto_id)) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { foto_id: "A foto da avaria é obrigatória e tem de ser desta vistoria" });
    if (a.valor_centavos !== undefined && a.valor_centavos !== null && (perfilAtualFalso() === "vistoriador" || r.v.tipo === "saida")) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { valor_centavos: "O valor da avaria é informado por quem fecha a conta" });
    r.v.avarias = [...r.v.avarias, { id: 60 + r.v.avarias.length + id, descricao: a.descricao.trim(), preexistente: r.v.tipo === "saida", foto_id: a.foto_id, vai_para_oficina: r.v.tipo === "devolucao" && !!a.vai_para_oficina, valor_centavos: r.v.tipo === "devolucao" ? (a.valor_centavos ?? null) : null, origem: null }];
    return montar(r);
  },

  async removerAvaria(id: number, avariaId: number): Promise<Vistoria> {
    await pausa(150);
    garantirSementes();
    exigirVistoria();
    const r = achar(id);
    exigirRascunho(r);
    const a = r.v.avarias.find((x) => x.id === avariaId);
    if (!a) throw new ErroApi(404, "nao_encontrado", "Avaria não encontrada");
    if (a.preexistente && r.v.tipo === "saida") throw new ErroApi(409, "avaria_preexistente", "Esta avaria vem da vistoria anterior e não se remove aqui");
    r.v.avarias = r.v.avarias.filter((x) => x.id !== avariaId);
    return montar(r);
  },

  /** 200 com a vistoria concluída; 422 com todas as pendências em `detalhes.pendencias`. */
  async concluir(id: number): Promise<Vistoria> {
    await pausa(300);
    garantirSementes();
    exigirVistoria();
    const r = achar(id);
    exigirRascunho(r);
    const v = montar(r);
    const pendencias: PendenciaDaVistoria[] = [];
    if (v.fotos_obrigatorias.faltam.length > 0) pendencias.push({ codigo: "VIS-01", mensagem: `Faltam ${v.fotos_obrigatorias.faltam.length} ${v.fotos_obrigatorias.faltam.length === 1 ? "foto obrigatória" : "fotos obrigatórias"}`, faltam: v.fotos_obrigatorias.faltam });
    const semResposta = v.itens.filter((i) => i.ok === null);
    if (semResposta.length > 0) pendencias.push({ codigo: "VIS-02", mensagem: "Confira todos os itens da lista", itens: semResposta.map((i) => i.codigo) });
    if (!v.combustivel) pendencias.push({ codigo: "VIS-03", mensagem: "Informe o nível de combustível" });
    if (v.km === null) pendencias.push({ codigo: "km_nao_informado", mensagem: "Informe a quilometragem" });
    else if (v.km < r.kmDoVeiculo) pendencias.push({ codigo: "VEI-01", mensagem: `O km informado é menor que o atual do veículo (${new Intl.NumberFormat("pt-BR").format(r.kmDoVeiculo)} km). Corrija o km do veículo antes.`, km_atual: r.kmDoVeiculo, corrigir_km: `/api/veiculos/${v.veiculo.id}/corrigir-km/` });
    if (v.tipo === "saida") {
      const cliente = await clientesFalso.obter(r.dados.cliente.id);
      if (cliente.status === "incompleto") pendencias.push({ codigo: "CLI-03", mensagem: "Cadastro do cliente incompleto. Envie os documentos antes da retirada." });
      if (cliente.status === "bloqueado") pendencias.push({ codigo: "CLI-05", mensagem: "Cliente bloqueado por atraso. Quite o que deve antes da retirada." });
    }
    if (pendencias.length > 0) {
      const [primeira] = pendencias as [PendenciaDaVistoria];
      throw new ErroApi(422, primeira.codigo, pendencias.length === 1 ? primeira.mensagem : `Resolva as ${pendencias.length} pendências antes de concluir`, { pendencias });
    }
    r.v.status = "concluida";
    r.v.concluida_em = AGORA_DO_SEED;
    if (v.tipo === "saida" && v.km !== null) aplicarSaidaConcluida(r.dados.id, v.km, AGORA_DO_SEED);
    return montar(r);
  },

  async corrigir(id: number, corpo: { motivo: string }): Promise<Vistoria> {
    await pausa(250);
    garantirSementes();
    const p = perfilAtualFalso();
    if (p !== "administrador" && p !== "gerente") throw new ErroApi(403, "sem_permissao", "Só o gerente e o administrador corrigem uma vistoria concluída");
    const r = achar(id);
    if (r.v.status !== "concluida") throw new ErroApi(409, "vistoria_nao_concluida", "Só uma vistoria concluída se corrige");
    if (!corpo.motivo.trim()) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { motivo: "Informe o motivo da correção" });
    const copia: Registro = { ...r, v: { ...r.v, id: proximaVistoria++, status: "rascunho", concluida_em: null, substitui: r.v.id, motivo_correcao: corpo.motivo, fotos: [...r.v.fotos], itens: r.v.itens.map((i) => ({ ...i })), avarias: [...r.v.avarias] } };
    VISTORIAS.set(copia.v.id, copia);
    return montar(copia);
  },

  /** GET /api/vistorias/agenda/?dia=: retiradas e devoluções previstas, em ordem de horário. */
  async agenda(dia: DiaDaAgenda = "hoje"): Promise<AgendaDoDia> {
    await pausa(200);
    garantirSementes();
    exigirVistoria();
    const todos: ItemDaAgenda[] = [
      { id: "devolucao-2790", tipo: "devolucao", horario: "2026-09-12T12:00:00Z", veiculo: { id: 511, placa: "PQD6E21", modelo: "Honda Pop 110i" }, cliente: { nome: "Rafael Sousa" }, locacao: { id: 2790, codigo: "LOC-2790" }, situacao: { codigo: "atrasada", rotulo: "Atrasada", tom: "perigo" }, vistoria_id: null, acao: { codigo: "abrir", rotulo: "Abrir" } },
      { id: "saida-2856", tipo: "saida", horario: "2026-10-07T12:30:00Z", veiculo: { id: 504, placa: "SAK1D39", modelo: "Honda CG 160 Fan" }, cliente: { nome: "Lucas Ferreira" }, locacao: { id: 2856, codigo: "LOC-2856" }, situacao: { codigo: "em_andamento", rotulo: "Em andamento", tom: "alerta" }, vistoria_id: 3001, acao: { codigo: "continuar", rotulo: "Continuar" } },
      { id: "devolucao-2848", tipo: "devolucao", horario: "2026-10-10T12:00:00Z", veiculo: { id: 513, placa: "RKP3D26", modelo: "Renault Kwid Zen" }, cliente: { nome: "Diego Martins" }, locacao: { id: 2848, codigo: "LOC-2848" }, situacao: { codigo: "agendada", rotulo: "Agendada", tom: "info" }, vistoria_id: null, acao: { codigo: "abrir", rotulo: "Abrir" } },
    ];
    const hoje = diaDe(AGORA_DO_SEED);
    const doDia = (i: ItemDaAgenda) => (dia === "hoje" ? diaDe(i.horario) <= hoje && (diaDe(i.horario) === hoje || i.situacao.codigo === "atrasada") : dia === "amanha" ? diaDe(i.horario) === "2026-10-08" : diaDe(i.horario) >= hoje && diaDe(i.horario) <= "2026-10-13");
    const lista = todos.filter(doDia);
    const saidas = lista.filter((i) => i.tipo === "saida").length;
    const devolucoes = lista.length - saidas;
    const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;
    const rotuloDia = dia === "hoje" ? "Quarta, 07 out" : dia === "amanha" ? "Quinta, 08 out" : "07 a 13 out";
    return {
      resumo: `${rotuloDia} · ${plural(saidas, "saída", "saídas")} e ${plural(devolucoes, "devolução", "devoluções")}`,
      proxima: dia === "hoje" ? { item_id: "saida-2856", em_minutos: 20 } : null,
      avarias_abertas: 2,
      resultados: lista,
    };
  },

  /** GET /api/vistorias/avarias/: as ainda não reparadas. */
  async avarias(): Promise<{ resultados: AvariaAberta[] }> {
    await pausa(200);
    exigirVistoria();
    const f = (posicao: PosicaoFoto, em: string) => foto(posicao, em);
    return {
      resultados: [
        { id: 51, descricao: "Risco no tanque, lado esquerdo", veiculo: { id: 504, placa: "SAK1D39", modelo: "Honda CG 160 Fan" }, locacao: { id: 2856, codigo: "LOC-2856" }, registrada_em: "2026-09-18T15:10:00Z", foto: f("avaria", "2026-09-18T15:10:00Z"), vai_para_oficina: false },
        { id: 44, descricao: "Amassado no paralama dianteiro", veiculo: { id: 501, placa: "QXA4B21", modelo: "Honda CG 160 Fan" }, locacao: { id: 2841, codigo: "LOC-2841" }, registrada_em: "2026-09-22T11:40:00Z", foto: f("avaria", "2026-09-22T11:40:00Z"), vai_para_oficina: true },
      ],
    };
  },

  // ---- Devolução --------------------------------------------------------------------------------------------------

  /** POST /api/locacoes/{id}/devolucao/: 201 com a devolução e a chegada em rascunho, ou 200 com a que já existe. */
  async abrirDevolucao(locacaoId: number): Promise<DevolucaoCompleta> {
    await pausa(250);
    garantirSementes();
    exigirVistoria();
    const d = dadosDaLocacaoParaVistoria(locacaoId);
    if (d.status !== "ativa" && d.status !== "devolucao_atrasada") throw new ErroApi(409, "transicao_locacao", "Só é possível devolver uma locação ativa");
    const existente = [...DEVOLUCOES.values()].find((x) => x.locacaoId === locacaoId);
    if (existente) return montarDevolucao(existente);
    return montarDevolucao(criarDevolucao({ id: 800 + locacaoId, locacaoId, saidaKm: d.kmSaida ?? 1000, chegadaKm: null, chegadaCombustivel: null, fotos: false, devolvidaEm: AGORA_DO_SEED }));
  },

  async obterDevolucao(id: number): Promise<DevolucaoCompleta> {
    await pausa(150);
    exigirVistoria();
    return montarDevolucao(acharDevolucao(id));
  },

  async definirForma(id: number, forma: FormaDevolucaoAcerto): Promise<DevolucaoCompleta> {
    await pausa(150);
    exigirAcerto();
    const dev = acharDevolucao(id);
    if (dev.status === "concluida") throw new ErroApi(409, "acerto_concluido", "O acerto já foi encerrado");
    dev.forma = forma;
    return montarDevolucao(dev);
  },

  async adicionarItem(id: number, item: NovoItemDoAcerto): Promise<DevolucaoCompleta> {
    await pausa(200);
    exigirAcerto();
    const dev = acharDevolucao(id);
    if (dev.status === "concluida") throw new ErroApi(409, "acerto_concluido", "O acerto já foi encerrado");
    const campos: Record<string, string> = {};
    if (!item.descricao.trim()) campos.descricao = "Descreva o item";
    if (!Number.isInteger(item.valor_centavos) || item.valor_centavos < 0) campos.valor_centavos = "Informe um valor em reais";
    if (Object.keys(campos).length > 0) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, campos);
    dev.informados.push({ id: proximoItem++, tipo: item.tipo, descricao: item.descricao.trim(), valor_centavos: item.valor_centavos, modo: "informado", avaria_id: null, conta_id: null });
    return montarDevolucao(dev);
  },

  async editarItem(id: number, itemId: number, patch: { descricao?: string; valor_centavos?: number }): Promise<DevolucaoCompleta> {
    await pausa(200);
    exigirAcerto();
    const dev = acharDevolucao(id);
    if (dev.status === "concluida") throw new ErroApi(409, "acerto_concluido", "O acerto já foi encerrado");
    const item = acertoDe(dev).itens.find((i) => i.id === itemId);
    if (!item) throw new ErroApi(404, "item_nao_encontrado", "Item do acerto não encontrado");
    if (item.modo === "calculado") throw new ErroApi(409, "item_calculado", "Este item é calculado e não se edita");
    if (patch.valor_centavos !== undefined && (!Number.isInteger(patch.valor_centavos) || patch.valor_centavos < 0)) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { valor_centavos: "Informe um valor em reais" });
    const guardado = dev.informados.find((i) => i.id === itemId);
    if (guardado) Object.assign(guardado, patch);
    else dev.informados.push({ ...item, ...patch });
    return montarDevolucao(dev);
  },

  async removerItem(id: number, itemId: number): Promise<DevolucaoCompleta> {
    await pausa(150);
    exigirAcerto();
    const dev = acharDevolucao(id);
    if (dev.status === "concluida") throw new ErroApi(409, "acerto_concluido", "O acerto já foi encerrado");
    const item = acertoDe(dev).itens.find((i) => i.id === itemId);
    if (!item) throw new ErroApi(404, "item_nao_encontrado", "Item do acerto não encontrado");
    if (item.tipo !== "multa_transito" && item.tipo !== "avaria") throw new ErroApi(409, "item_da_vistoria", "Este item vem da vistoria e não se remove");
    if (item.avaria_id) throw new ErroApi(409, "item_da_vistoria", "Este item vem da vistoria e não se remove");
    dev.informados = dev.informados.filter((i) => i.id !== itemId);
    return montarDevolucao(dev);
  },

  /** 200 com a devolução concluída. 422 `vistoria_pendente`, 422 `DEV-07`, 400 sem forma de devolução quando há saldo a devolver. */
  async encerrar(id: number): Promise<DevolucaoCompleta> {
    await pausa(400);
    exigirAcerto();
    const dev = acharDevolucao(id);
    if (dev.status === "concluida") throw new ErroApi(409, "acerto_concluido", "O acerto já foi encerrado");
    const chegada = achar(dev.chegadaId);
    if (chegada.v.status !== "concluida") throw new ErroApi(422, "vistoria_pendente", "Conclua a vistoria de chegada antes de encerrar a devolução");
    const d = dadosDaLocacaoParaVistoria(dev.locacaoId);
    if (d.trocaPendente) throw new ErroApi(409, "troca_pendente", "Há uma troca de veículo pendente nesta locação");
    const acerto = acertoDe(dev);
    if (acerto.avisos.some((a) => a.codigo === "DEV-07")) throw new ErroApi(422, "DEV-07", "A devolução é antes do fim do contrato. Peça o encerramento antecipado ao gerente.", { fim_previsto: d.fim, devolvida_em: dev.devolvidaEm });
    if (acerto.resultado.tipo === "devolver" && !dev.forma) throw new ErroApi(400, "validacao", "Escolha como devolver o saldo ao cliente", undefined, { forma_devolucao: "Escolha como devolver o saldo ao cliente" });
    dev.status = "concluida";
    dev.concluidaEm = AGORA_DO_SEED;
    dev.reciboEm = AGORA_DO_SEED;
    aplicarDevolucaoEncerrada(dev.locacaoId, AGORA_DO_SEED, d.cancelamentoAprovado);
    return montarDevolucao(dev);
  },

  async recibo(id: number): Promise<{ url: string; url_expira_em: string }> {
    await pausa(250);
    exigirAcerto();
    const dev = acharDevolucao(id);
    if (dev.status !== "concluida") throw new ErroApi(409, "devolucao_em_rascunho", "O recibo sai depois que a devolução é encerrada");
    return { url: `/recibos/DEV-${dev.id}.pdf`, url_expira_em: new Date(Date.parse(AGORA_DO_SEED) + 15 * 60_000).toISOString() };
  },

  async reenviarRecibo(id: number): Promise<void> {
    await pausa(250);
    exigirAcerto();
    const dev = acharDevolucao(id);
    if (dev.status !== "concluida") throw new ErroApi(409, "devolucao_em_rascunho", "O recibo sai depois que a devolução é encerrada");
    dev.reciboEm = AGORA_DO_SEED;
  },
};
