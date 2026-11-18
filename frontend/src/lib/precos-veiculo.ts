import type {
  ComoPaga,
  CustosDoVeiculo,
  CustosEntrada,
  FormaAceita,
  ModoDaParcela,
  PeriodicidadeDaCompra,
  PeriodoDoPlano,
  PlanoCompraEntrada,
  PlanoDoVeiculo,
  PlanoEntrada,
  PrecosDoVeiculo,
  PrecosEntrada,
  RegrasEntrada,
  TipoDePlano,
} from "@/lib/api";
import { dataCurta, dinheiro } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";

// Preços por veículo (VEI-12 a VEI-17, ADR 0041). A tela só formata e converte o que a pessoa digita em centavos;
// valor, margem, parcela, juros e alertas são da API (`GET` e `POST .../simular/`). Aqui não há conta de negócio.

// ---------------------------------------------------------------- Leitura do que se digita

const NUMERO = /\d[\d.,]*/;
const numeroDe = (t: string): string | null => NUMERO.exec(t)?.[0] ?? null;

/** "R$ 1.250,50", "0,35 por km" ou "54,90" em centavos. Vazio ou fora de formato volta `undefined`; a API confere o resto. */
export function centavosDoCampo(t: string): number | undefined {
  const n = numeroDe(t);
  return n ? (centavosDoTexto(n) ?? undefined) : undefined;
}

/** "1.000 km", "até 3 dias" ou "104" em número inteiro. */
export function inteiroDoCampo(t: string): number | undefined {
  const n = numeroDe(t);
  if (!n) return undefined;
  const digitos = n.replace(/[.,]/g, "");
  return digitos ? Number(digitos) : undefined;
}

/** "1,00%", "até 10%" ou "85" em decimal de 2 casas ("1.00"), como a API recebe. */
export function percentualDoCampo(t: string): string | undefined {
  const n = numeroDe(t);
  if (!n) return undefined;
  const s = n.replace(/\./g, "").replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(s)) return undefined;
  const [inteiro = "0", frac = ""] = s.split(".");
  return `${inteiro}.${frac.padEnd(2, "0")}`;
}

/** "1.00" da API em "1,00%", o texto do campo. */
export const textoDoPercentual = (pct: string | null | undefined): string => (pct == null ? "" : `${pct.replace(".", ",")}%`);

export const textoDoDinheiro = (centavos: number | null | undefined): string => (centavos == null ? "" : dinheiro(centavos));

// ---------------------------------------------------------------- Rótulos

export const ROTULO_DO_TIPO: Record<TipoDePlano, string> = { diaria: "Diária", semanal: "Semanal", mensal: "Mensal", entregador: "Entregador", outro: "Outro" };

const PERIODO: Record<PeriodoDoPlano, { por: string; em: string; plural: string }> = {
  dia: { por: "por dia", em: "dia", plural: "dias" },
  semana: { por: "por semana", em: "semana", plural: "semanas" },
  mes: { por: "por mês", em: "mês", plural: "meses" },
};
export const porPeriodo = (p: PeriodoDoPlano) => PERIODO[p].por;
export const periodoPlural = (p: PeriodoDoPlano) => PERIODO[p].plural;

export const ROTULO_DA_FORMA: Record<FormaAceita, string> = { pix: "Pix", boleto: "Boleto", cartao: "Cartão", dinheiro: "Dinheiro" };
export const FORMAS: FormaAceita[] = ["pix", "boleto", "cartao", "dinheiro"];

/** "Pix ou boleto", "Pix, boleto ou cartão". */
export function textoDasFormas(formas: FormaAceita[]): string {
  const nomes = FORMAS.filter((f) => formas.includes(f)).map((f) => ROTULO_DA_FORMA[f].toLowerCase());
  if (nomes.length === 0) return "—";
  const texto = nomes.length === 1 ? (nomes[0] as string) : `${nomes.slice(0, -1).join(", ")} ou ${nomes[nomes.length - 1]}`;
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

const numeroBr = (n: number) => new Intl.NumberFormat("pt-BR").format(n);

/** "1.000 km por semana" ou "livre". */
export const textoDaFranquia = (km: number | null, p: PeriodoDoPlano): string => (km == null ? "livre" : `${numeroBr(km)} km ${PERIODO[p].por}`);

export const textoDoPrazoMinimo = (n: number | null, p: PeriodoDoPlano): string => (n == null ? "Sem mínimo" : `${numeroBr(n)} ${n === 1 ? PERIODO[p].em : PERIODO[p].plural}`);

/** Caução em parcelas: 1 é "À vista". */
export const textoDaCaucaoEm = (parcelas: number): string => (parcelas <= 1 ? "À vista" : `${parcelas}x`);
export const OPCOES_DE_PARCELAS_DA_CAUCAO = Array.from({ length: 12 }, (_, i) => i + 1);

const PAGAMENTO_BASE: Record<ComoPaga, string> = {
  tudo_na_retirada: "Tudo na retirada",
  semana_adiantado: "Toda semana, adiantado",
  mes_quatro_semanais: "4 semanais",
  mes_uma_parcela: "1 parcela no mês",
  mes_duas_quinzenais: "2 quinzenais",
};
export const PAGAMENTOS_DO_PERIODO: Record<PeriodoDoPlano, ComoPaga[]> = {
  dia: ["tudo_na_retirada"],
  semana: ["semana_adiantado"],
  mes: ["mes_quatro_semanais", "mes_uma_parcela", "mes_duas_quinzenais"],
};
export const pagamentoPadrao = (p: PeriodoDoPlano): ComoPaga => PAGAMENTOS_DO_PERIODO[p][0] as ComoPaga;

/** "4 semanais de R$ 247,50" quando a API devolveu a parcela do mês dividido; sem ela, o nome da opção. */
export function textoDoPagamento(como: ComoPaga, parcelaDoMes?: PlanoDoVeiculo["parcela_do_mes"]): string {
  if (!parcelaDoMes || como === "mes_uma_parcela") return PAGAMENTO_BASE[como];
  const nome = como === "mes_duas_quinzenais" ? "quinzenais" : "semanais";
  return `${parcelaDoMes.parcelas} ${nome} de ${dinheiro(parcelaDoMes.parcela_centavos)}`;
}

export const ROTULO_DA_PERIODICIDADE_DA_COMPRA: Record<PeriodicidadeDaCompra, string> = { diaria: "Diárias", semanal: "Semanais", quinzenal: "Quinzenais", mensal: "Mensais" };
const UNIDADE_DA_COMPRA: Record<PeriodicidadeDaCompra, { por: string; plural: string }> = {
  diaria: { por: "por dia", plural: "dias" },
  semanal: { por: "por semana", plural: "semanas" },
  quinzenal: { por: "a cada 14 dias", plural: "quinzenas" },
  mensal: { por: "por mês", plural: "meses" },
};
export const porPeriodoDaCompra = (p: PeriodicidadeDaCompra) => UNIDADE_DA_COMPRA[p].por;
export const pluralDaCompra = (p: PeriodicidadeDaCompra) => UNIDADE_DA_COMPRA[p].plural;
export const MODOS_DA_PARCELA: { valor: ModoDaParcela; rotulo: string }[] = [
  { valor: "calcular", rotulo: "Calcular pelos juros" },
  { valor: "digitar", rotulo: "Digitar a parcela" },
];

/** "R$ 289,00 a partir de 01 dez". */
export const textoDoAgendado = (a: { valor_centavos: number; a_partir_de: string }): string => `${dinheiro(a.valor_centavos)} a partir de ${dataCurta(a.a_partir_de)}`;

/** Sem esse tom a margem não tem cor: a API diz se está abaixo da mínima. */
export const tomDaMargem = (abaixo: boolean) => (abaixo ? ("alerta" as const) : ("sucesso" as const));

/** "84,00" da API em "84%". */
export const textoDaOcupacao = (pct: string): string => `${Number(pct).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;

/** "1.46" da API em "1,46%". */
export const textoDosJuros = (pct: string): string => `${pct.replace(".", ",")}%`;

export const textoDeMeses = (meses: string): string => `${Number(meses).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} meses`;

// ---------------------------------------------------------------- Textos fixos (VEI-12, VEI-15; aprovados pelo Produto)

export const TEXTO_DESLIGAR = "Este plano deixa de aparecer na Nova locação. As locações já confirmadas continuam com o preço delas.";
export const TEXTO_DESLIGAR_O_ULTIMO =
  "Este é o último plano ligado. Sem nenhum plano ligado, esta moto fica indisponível, com o motivo sem preço, e não aparece na Nova locação. As locações já confirmadas continuam com o preço delas.";

// ---------------------------------------------------------------- Rascunho da tela

export type PlanoRascunho = {
  /** `id` do plano, ou o tipo enquanto o veículo ainda não tem a linha. */
  chave: string;
  id: number | null;
  tipo: TipoDePlano;
  rotulo: string;
  periodo: PeriodoDoPlano;
  ligado: boolean;
  valor: string;
  comoPaga: ComoPaga;
  caucao: string;
  caucaoParcelas: number;
  formas: FormaAceita[];
  franquia: string;
  prazoMinimo: string;
};

export type CompraRascunho = {
  ligado: boolean;
  periodicidade: PeriodicidadeDaCompra;
  parcelas: string;
  entrada: string;
  juros: string;
  modo: ModoDaParcela;
  parcelaMoto: string;
  adicional: string;
  caucao: string;
};

export type RegrasRascunho = { kmExcedente: string; diaAtraso: string; descontoPct: string; prazoCaucao: string; multaMinima: string };

export type Rascunho = { valorVenda: string; planos: PlanoRascunho[]; regras: RegrasRascunho; compra: CompraRascunho };

const PERIODO_DO_TIPO: Record<TipoDePlano, PeriodoDoPlano> = { diaria: "dia", semanal: "semana", mensal: "mes", entregador: "semana", outro: "dia" };

export const chaveDoPlano = (p: Pick<PlanoDoVeiculo, "id" | "tipo">): string => (p.id != null ? String(p.id) : p.tipo);

export function planoParaRascunho(p: PlanoDoVeiculo): PlanoRascunho {
  const periodo = p.periodo ?? PERIODO_DO_TIPO[p.tipo];
  return {
    chave: chaveDoPlano(p),
    id: p.id,
    tipo: p.tipo,
    rotulo: p.rotulo,
    periodo,
    ligado: p.ligado,
    valor: p.valor_centavos > 0 ? dinheiro(p.valor_centavos) : "",
    comoPaga: p.como_paga ?? pagamentoPadrao(periodo),
    caucao: textoDoDinheiro(p.caucao_centavos),
    caucaoParcelas: p.caucao_parcelas,
    formas: [...p.formas_aceitas],
    franquia: p.franquia_km == null ? "" : `${numeroBr(p.franquia_km)} km`,
    prazoMinimo: p.prazo_minimo_periodos == null ? "" : String(p.prazo_minimo_periodos),
  };
}

export function compraParaRascunho(c: PrecosDoVeiculo["plano_compra"]): CompraRascunho {
  if (!c) return { ligado: false, periodicidade: "semanal", parcelas: "", entrada: dinheiro(0), juros: textoDoPercentual("0.00"), modo: "calcular", parcelaMoto: "", adicional: dinheiro(0), caucao: dinheiro(0) };
  return {
    ligado: c.ligado,
    periodicidade: c.periodicidade,
    parcelas: String(c.parcelas),
    entrada: dinheiro(c.entrada_centavos),
    juros: textoDoPercentual(c.juros_mes_pct),
    modo: c.modo,
    parcelaMoto: c.modo === "digitar" ? dinheiro(c.parcela_moto_centavos) : "",
    adicional: dinheiro(c.adicional_centavos),
    caucao: dinheiro(c.caucao_centavos),
  };
}

export function rascunhoDoDocumento(d: PrecosDoVeiculo): Rascunho {
  return {
    valorVenda: textoDoDinheiro(d.valor_venda_centavos),
    planos: d.planos.map(planoParaRascunho),
    regras: {
      kmExcedente: `${dinheiro(d.regras.km_excedente_centavos)} por km`,
      diaAtraso: `${dinheiro(d.regras.dia_atraso_centavos)} por dia`,
      descontoPct: `até ${textoDoPercentual(d.regras.desconto_sem_aprovacao_pct).replace(",00%", "%")}`,
      prazoCaucao: d.regras.prazo_devolucao_caucao_dias == null ? "" : `até ${d.regras.prazo_devolucao_caucao_dias} dias`,
      multaMinima: dinheiro(d.regras.multa_minima_centavos),
    },
    compra: compraParaRascunho(d.plano_compra),
  };
}

// ---------------------------------------------------------------- Rascunho para o corpo da API

/** Erros de campo, na chave `plano.<chave>.<campo da API>`, `regras.<campo>`, `compra.<campo>`, `custos.<campo>` ou `valor_venda_centavos`. */
export type ErrosDeCampo = Record<string, string>;

const MSG_VALOR = "Informe um valor em reais, como 54,90.";
const MSG_NUMERO = "Informe um número.";
const MSG_PERCENTUAL = "Informe um percentual, como 10 ou 1,50.";

type Acumulador = { erros: ErrosDeCampo };

function dinheiroOu(a: Acumulador, chave: string, texto: string, vazio: number | null): number | null {
  if (texto.trim() === "") return vazio;
  const c = centavosDoCampo(texto);
  if (c === undefined) {
    a.erros[chave] = MSG_VALOR;
    return vazio;
  }
  return c;
}

function inteiroOu(a: Acumulador, chave: string, texto: string, vazio: number | null): number | null {
  if (texto.trim() === "") return vazio;
  const n = inteiroDoCampo(texto);
  if (n === undefined) {
    a.erros[chave] = MSG_NUMERO;
    return vazio;
  }
  return n;
}

function percentualOu(a: Acumulador, chave: string, texto: string, vazio: string | null): string | null {
  if (texto.trim() === "") return vazio;
  const p = percentualDoCampo(texto);
  if (p === undefined) {
    a.erros[chave] = MSG_PERCENTUAL;
    return vazio;
  }
  return p;
}

export function planoParaCorpo(p: PlanoRascunho, a: Acumulador): PlanoEntrada {
  const k = (campo: string) => `plano.${p.chave}.${campo}`;
  const franquiaLivre = p.franquia.trim() === "" || /livre/i.test(p.franquia);
  return {
    ...(p.id != null ? { id: p.id } : { tipo: p.tipo }),
    periodo: p.periodo,
    ligado: p.ligado,
    valor_centavos: dinheiroOu(a, k("valor_centavos"), p.valor, 0) ?? 0,
    como_paga: p.comoPaga,
    formas_aceitas: FORMAS.filter((f) => p.formas.includes(f)),
    caucao_centavos: dinheiroOu(a, k("caucao_centavos"), p.caucao, null),
    caucao_parcelas: p.caucaoParcelas,
    franquia_km: franquiaLivre ? null : inteiroOu(a, k("franquia_km"), p.franquia, null),
    prazo_minimo_periodos: inteiroOu(a, k("prazo_minimo_periodos"), p.prazoMinimo, null),
  };
}

export function compraParaCorpo(c: CompraRascunho, a: Acumulador): PlanoCompraEntrada {
  const k = (campo: string) => `compra.${campo}`;
  return {
    ligado: c.ligado,
    periodicidade: c.periodicidade,
    parcelas: inteiroOu(a, k("parcelas"), c.parcelas, 0) ?? 0,
    entrada_centavos: dinheiroOu(a, k("entrada_centavos"), c.entrada, 0) ?? 0,
    juros_mes_pct: percentualOu(a, k("juros_mes_pct"), c.juros, "0.00") ?? "0.00",
    modo: c.modo,
    parcela_moto_centavos: c.modo === "digitar" ? (dinheiroOu(a, k("parcela_moto_centavos"), c.parcelaMoto, 0) ?? 0) : 0,
    adicional_centavos: dinheiroOu(a, k("adicional_centavos"), c.adicional, 0) ?? 0,
    caucao_centavos: dinheiroOu(a, k("caucao_centavos"), c.caucao, 0) ?? 0,
  };
}

export function regrasParaCorpo(r: RegrasRascunho, a: Acumulador): RegrasEntrada {
  const k = (campo: string) => `regras.${campo}`;
  return {
    km_excedente_centavos: dinheiroOu(a, k("km_excedente_centavos"), r.kmExcedente, 0) ?? 0,
    dia_atraso_centavos: dinheiroOu(a, k("dia_atraso_centavos"), r.diaAtraso, 0) ?? 0,
    multa_minima_centavos: dinheiroOu(a, k("multa_minima_centavos"), r.multaMinima, 0) ?? 0,
    desconto_sem_aprovacao_pct: percentualOu(a, k("desconto_sem_aprovacao_pct"), r.descontoPct, "0.00") ?? "0.00",
    prazo_devolucao_caucao_dias: inteiroOu(a, k("prazo_devolucao_caucao_dias"), r.prazoCaucao, null),
  };
}

const igual = (x: unknown, y: unknown) => JSON.stringify(x) === JSON.stringify(y);

export type CorpoMontado = {
  corpo: PrecosEntrada;
  erros: ErrosDeCampo;
  /** Chaves dos planos na ordem em que vão em `planos[]`, para achar o plano de `planos.N.campo` do erro da API. */
  planosEnviados: string[];
  /** Tem alguma coisa para gravar (a diferença do rascunho para a base). */
  mudou: boolean;
};

/**
 * O corpo do `PUT` e do `simular` só com o que mudou em relação à base (o que a API mostrou por último): planos, venda,
 * regras e compra que a pessoa não tocou ficam de fora e não são recriados nem regravados.
 */
export function corpoDaDiferenca(r: Rascunho, base: Rascunho, opcoes: { confirmarJuros?: boolean } = {}): CorpoMontado {
  const a: Acumulador = { erros: {} };
  const corpo: PrecosEntrada = { confirmar_juros: opcoes.confirmarJuros ?? false };
  const planosEnviados: string[] = [];
  let mudou = false;

  if (r.valorVenda !== base.valorVenda) {
    corpo.valor_venda_centavos = dinheiroOu(a, "valor_venda_centavos", r.valorVenda, null);
    mudou = true;
  }
  const planos: PlanoEntrada[] = [];
  for (const p of r.planos) {
    const antes = base.planos.find((b) => b.chave === p.chave);
    if (antes && igual(antes, p)) continue;
    planos.push(planoParaCorpo(p, a));
    planosEnviados.push(p.chave);
  }
  if (planos.length) {
    corpo.planos = planos;
    mudou = true;
  }
  if (!igual(r.regras, base.regras)) {
    corpo.regras = regrasParaCorpo(r.regras, a);
    mudou = true;
  }
  if (!igual(r.compra, base.compra)) {
    corpo.plano_compra = compraParaCorpo(r.compra, a);
    mudou = true;
  }
  return { corpo, erros: a.erros, planosEnviados, mudou };
}

/** O corpo só de um plano (liga e desliga e agendamento): vale o que está digitado nele. */
export function corpoDoPlano(p: PlanoRascunho, extra: Partial<PlanoEntrada> = {}): CorpoMontado {
  const a: Acumulador = { erros: {} };
  return { corpo: { planos: [{ ...planoParaCorpo(p, a), ...extra }], confirmar_juros: false }, erros: a.erros, planosEnviados: [p.chave], mudou: true };
}

/** O corpo só da compra, para o liga e desliga dela. */
export function corpoDaCompra(c: CompraRascunho, opcoes: { confirmarJuros?: boolean } = {}): CorpoMontado {
  const a: Acumulador = { erros: {} };
  return { corpo: { plano_compra: compraParaCorpo(c, a), confirmar_juros: opcoes.confirmarJuros ?? false }, erros: a.erros, planosEnviados: [], mudou: true };
}

/** Chaves de erro da API (`planos.0.valor_centavos`, `plano_compra.entrada_centavos`) nas chaves da tela. */
export function errosDaApi(campos: Record<string, string> | undefined, planosEnviados: string[]): ErrosDeCampo {
  const saida: ErrosDeCampo = {};
  for (const [campo, msg] of Object.entries(campos ?? {})) {
    const plano = /^planos\.(\d+)\.(.+)$/.exec(campo);
    if (plano) {
      const chave = planosEnviados[Number(plano[1])];
      saida[`plano.${chave ?? "?"}.${(plano[2] as string).split(".")[0]}`] = msg;
      if ((plano[2] as string).startsWith("agendado")) saida[`plano.${chave ?? "?"}.agendado`] = msg;
    } else if (campo.startsWith("plano_compra.")) saida[`compra.${campo.slice("plano_compra.".length)}`] = msg;
    else saida[campo] = msg;
  }
  return saida;
}

// ---------------------------------------------------------------- Custos mensais (modal)

export type CustosRascunho = { manutencao: string; seguro: string; ipvaAno: string; rastreador: string; ocupacao: string };

export function custosParaRascunho(c: CustosDoVeiculo | undefined): CustosRascunho {
  return {
    manutencao: dinheiro(c?.manutencao_mes_centavos ?? 0),
    seguro: dinheiro(c?.seguro_mes_centavos ?? 0),
    ipvaAno: dinheiro(c?.ipva_ano_centavos ?? 0),
    rastreador: dinheiro(c?.rastreador_mes_centavos ?? 0),
    ocupacao: textoDoPercentual(c?.ocupacao_esperada_pct),
  };
}

/** A revenda estimada não tem campo na tela de referência: vai o valor que já estava. */
export function custosParaCorpo(r: CustosRascunho, atual: CustosDoVeiculo | undefined): { custos: CustosEntrada; erros: ErrosDeCampo } {
  const a: Acumulador = { erros: {} };
  const custos: CustosEntrada = {
    manutencao_mes_centavos: dinheiroOu(a, "custos.manutencao_mes_centavos", r.manutencao, 0) ?? 0,
    seguro_mes_centavos: dinheiroOu(a, "custos.seguro_mes_centavos", r.seguro, 0) ?? 0,
    rastreador_mes_centavos: dinheiroOu(a, "custos.rastreador_mes_centavos", r.rastreador, 0) ?? 0,
    ipva_ano_centavos: dinheiroOu(a, "custos.ipva_ano_centavos", r.ipvaAno, 0) ?? 0,
    ocupacao_esperada_pct: percentualOu(a, "custos.ocupacao_esperada_pct", r.ocupacao, null),
  };
  if (atual) custos.revenda_estimada_centavos = atual.revenda_estimada_centavos;
  return { custos, erros: a.erros };
}

// ---------------------------------------------------------------- Quem vê e quantos planos há ligados

/** A API manda `ligado` de cada plano e da compra; "o último" é só para escolher o texto do diálogo. */
export function ehOUltimoLigado(d: PrecosDoVeiculo, planoChave: string | "compra"): boolean {
  const outrosPlanos = d.planos.some((p) => p.ligado && chaveDoPlano(p) !== planoChave);
  const compra = planoChave !== "compra" && d.plano_compra?.ligado === true;
  return !outrosPlanos && !compra;
}

/** "56.26" da API em "56,3%": uma casa, só para a exibição. */
export const textoDaMargem = (pct: string): string => `${Number(pct).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
