// Textos do financeiro. Só rótulos e formatação: valor do dia, multa, juros e status vêm prontos da API (docs/api/financeiro.md).
import type { TomStatus } from "@/design-system";
import type { CategoriaDaDespesa, ContaReceber, Despesa, FormaDaBaixa, FormaDaDespesa, FormaDoMovimento, FormaPrevista, StatusDaDespesa, StatusDoCaixa, TipoDeConta } from "@/lib/api";
import { dataCurta, dinheiro, placa } from "@/lib/formatos";

const FORMAS: Record<FormaPrevista | FormaDaBaixa | FormaDoMovimento, string> = {
  pix: "Pix",
  pix_automatico: "Pix automático",
  cartao: "Cartão",
  cartao_debito: "Cartão de débito",
  cartao_credito: "Cartão de crédito",
  boleto: "Boleto",
  dinheiro: "Dinheiro",
  caucao: "Caução",
};

export const rotuloDaForma = (forma: string | null | undefined): string => (forma ? (FORMAS[forma as keyof typeof FORMAS] ?? forma) : "—");

const COBRANCAS: Record<Exclude<TipoDeConta, "parcela">, string> = {
  caucao: "Caução",
  multa: "Multa",
  avaria: "Avaria",
  acerto: "Acerto da devolução",
  outro: "Outra cobrança",
};

/** "4 de 4" para parcela; o nome da cobrança para os outros tipos. */
export function rotuloDaParcela(c: Pick<ContaReceber, "tipo" | "numero" | "total_parcelas">): string {
  if (c.tipo === "parcela") return c.numero && c.total_parcelas ? `${c.numero} de ${c.total_parcelas}` : "—";
  return COBRANCAS[c.tipo] ?? "—";
}

/** "LOC-2790 · PQD-6E21": o código da origem e a placa, quando há. */
export function origemDaConta(c: Pick<ContaReceber, "origem" | "veiculo_placa">): string {
  const placa = c.veiculo_placa ? `${c.veiculo_placa.slice(0, 3)}-${c.veiculo_placa.slice(3)}` : null;
  return [c.origem.codigo, placa].filter(Boolean).join(" · ");
}

export type SituacaoDaConta = { rotulo: string; tom: TomStatus };

/** O estado vem da API (`status`, `dias_atraso`); aqui só vira texto e tom. */
export function situacaoDaConta(c: Pick<ContaReceber, "status" | "dias_atraso">): SituacaoDaConta {
  switch (c.status) {
    case "atrasada":
      return { rotulo: c.dias_atraso === 1 ? "1 dia" : `${c.dias_atraso} dias`, tom: "critico" };
    case "vence_hoje":
      return { rotulo: "Vence hoje", tom: "alerta" };
    case "paga":
      return { rotulo: "Paga", tom: "sucesso" };
    case "cancelada":
      return { rotulo: "Cancelada", tom: "neutro" };
    case "renegociada":
      return { rotulo: "Renegociada", tom: "neutro" };
    default:
      return { rotulo: "A vencer", tom: "neutro" };
  }
}

/** "R$ 299,40 + multa de R$ 5,99 + juros de R$ 0,70". Sem multa nem juros, só o principal. */
export function composicaoDoValor(v: { principal_centavos: number; multa_centavos: number; juros_centavos: number }): string {
  const partes = [dinheiro(v.principal_centavos)];
  if (v.multa_centavos > 0) partes.push(`multa de ${dinheiro(v.multa_centavos)}`);
  if (v.juros_centavos > 0) partes.push(`juros de ${dinheiro(v.juros_centavos)}`);
  return partes.join(" + ");
}

/** "Parcela 2 de 5 · venceu 30 set" ou "Parcela 2 de 5 · vence 14 out". */
export function linhaDaConta(c: Pick<ContaReceber, "tipo" | "numero" | "total_parcelas" | "vencimento" | "status">): string {
  const nome = c.tipo === "parcela" ? `Parcela ${rotuloDaParcela(c)}` : rotuloDaParcela(c);
  const venceu = c.status === "atrasada" || c.status === "paga";
  return `${nome} · ${venceu ? "venceu" : "vence"} ${dataCurta(c.vencimento)}`;
}

export const ROTULO_STATUS_DO_CAIXA: Record<StatusDoCaixa, string> = {
  aberto: "Aberto",
  aguardando_aprovacao: "Aguardando aprovação",
  fechado: "Fechado",
  fechado_sem_conferencia: "Fechado sem conferência",
};

export const TOM_STATUS_DO_CAIXA: Record<StatusDoCaixa, TomStatus> = {
  aberto: "sucesso",
  aguardando_aprovacao: "alerta",
  fechado: "neutro",
  fechado_sem_conferencia: "atencao",
};

/** "Quarta, 07 out" a partir de AAAA-MM-DD. */
export function diaDaSemanaEData(dia: string): string {
  const d = new Date(`${dia}T12:00:00-03:00`);
  const semana = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", weekday: "long" }).format(d);
  return `${semana.charAt(0).toUpperCase()}${semana.slice(1).replace("-feira", "")}, ${dataCurta(dia)}`;
}

const ACOES: Record<string, string> = {
  "conta_receber.criar": "Conta criada",
  "conta_receber.pagar": "Pagamento recebido",
  "conta_receber.cobrar": "Cobrança enviada ao cliente",
  "conta_receber.cancelar": "Conta cancelada",
  "conta_receber.renegociar": "Conta renegociada",
  "conta_receber.estornar": "Pagamento estornado",
  "conta_receber.ajustar_valor": "Valor ajustado",
  "cobranca.pix": "Pix gerado",
  "cobranca.boleto": "Boleto gerado",
};

/** O código do evento vira texto; código desconhecido aparece como está (docs/api/financeiro.md). */
export const textoDoEvento = (acao: string): string => ACOES[acao] ?? acao;

// Despesas (FIN-05, FIN-06). O estado e o texto da situação ("Aguardando gerente", "Vence 10 out", "Pago · caixa") vêm da API.

export const CATEGORIAS_DA_DESPESA: { valor: CategoriaDaDespesa; rotulo: string }[] = [
  { valor: "fixas", rotulo: "Fixas" },
  { valor: "manutencao", rotulo: "Manutenção" },
  { valor: "rastreamento", rotulo: "Rastreamento" },
  { valor: "impostos", rotulo: "Impostos" },
  { valor: "pessoal", rotulo: "Pessoal" },
  { valor: "outros", rotulo: "Outros" },
];

export const rotuloDaCategoria = (c: CategoriaDaDespesa): string => CATEGORIAS_DA_DESPESA.find((x) => x.valor === c)?.rotulo ?? c;

export const FORMAS_DE_PAGAR_DESPESA: { valor: FormaDaDespesa; rotulo: string }[] = [
  { valor: "pix", rotulo: "Pix" },
  { valor: "boleto", rotulo: "Boleto" },
  { valor: "cartao", rotulo: "Cartão" },
  { valor: "transferencia", rotulo: "Transferência" },
  { valor: "dinheiro", rotulo: "Dinheiro" },
];

export const TOM_DA_DESPESA: Record<StatusDaDespesa, TomStatus> = {
  aguardando_aprovacao: "alerta",
  a_pagar: "info",
  paga: "sucesso",
  recusada: "critico",
};

/** "Manutenção · PMZ-3E17 · Filial Centro" ou, sem veículo, "Fixa · Filial Centro". A filial é a `filial.nome` que a API manda (FIN-06, FIL-05). */
export function origemDaDespesa(d: Pick<Despesa, "categoria" | "veiculo" | "filial">): string {
  const categoria = d.categoria === "fixas" ? "Fixa" : rotuloDaCategoria(d.categoria);
  return [categoria, d.veiculo ? placa(d.veiculo.placa) : null, d.filial.nome].filter(Boolean).join(" · ");
}
