import type { CodigoAcaoLocacao, LocacaoCompleta, LocacaoResumo, ParcelaDaLocacao, Periodicidade, StatusParcela } from "@/lib/api";
import type { TomStatus } from "@/design-system";
import { agoraDaTela } from "@/lib/ambiente";
import { dataCurta, diaDe, horaCurta } from "@/lib/formatos";

/** Para onde a ação principal da linha leva (a API só diz qual é a ação). */
export function rotaDaAcaoLocacao(l: Pick<LocacaoResumo, "id" | "acao_principal">): string {
  const codigo: CodigoAcaoLocacao = l.acao_principal.codigo;
  if (codigo === "cobrar") return "/financeiro/receber";
  if (codigo === "receber_devolucao") return `/locacoes/${l.id}/devolucao`;
  return `/locacoes/${l.id}`;
}

const FORMAS_AVULSAS = new Set(["Pix", "Boleto", "Dinheiro"]);

/**
 * Coluna Pagamento da lista: mesmo vocabulário em todas as linhas ("Pago", "R$ X em aberto"). Quando está em dia, a API pode
 * mandar a forma de pagamento avulsa ("Pix"); isso a tela diz "Pago". "Pix automático" e "Cartão" aparecem na referência e ficam.
 */
export function rotuloDoPagamento(p: NonNullable<LocacaoResumo["pagamento"]>): string {
  return p.em_aberto_centavos === 0 && FORMAS_AVULSAS.has(p.rotulo) ? "Pago" : p.rotulo;
}

/** "05 set → 12 set". O dia de hoje sai "hoje"; a hora da devolução aparece quando a API diz que devolve hoje. */
export function periodoDaLocacao(l: Pick<LocacaoResumo, "inicio" | "fim_previsto" | "sinais">, agora: Date = agoraDaTela()): string {
  if (!l.inicio) return "—";
  const hoje = diaDe(agora.toISOString());
  const ini = diaDe(l.inicio) === hoje ? "hoje" : dataCurta(l.inicio);
  if (!l.fim_previsto) return ini;
  const fim = diaDe(l.fim_previsto) === hoje ? "hoje" : dataCurta(l.fim_previsto);
  return `${ini} → ${fim}${l.sinais.devolve_hoje ? ` ${horaCurta(l.fim_previsto)}` : ""}`;
}

/** "14 out às 18:00". */
export function dataEHora(iso: string): string {
  return `${dataCurta(iso)} às ${horaCurta(iso)}`;
}

/** "faltam 7 dias", "faltam 5 horas", "falta 1 hora", "faltam 20 minutos". Só formata o que a API mandou (`faltam_minutos`). */
export function textoFaltam(minutos: number): string {
  if (minutos <= 0) return "no prazo da devolução";
  const dias = Math.floor(minutos / 1440);
  if (dias >= 1) return `${dias === 1 ? "falta" : "faltam"} ${dias} ${dias === 1 ? "dia" : "dias"}`;
  const horas = Math.floor(minutos / 60);
  if (horas >= 1) return `${horas === 1 ? "falta" : "faltam"} ${horas} ${horas === 1 ? "hora" : "horas"}`;
  return `${minutos === 1 ? "falta" : "faltam"} ${minutos} ${minutos === 1 ? "minuto" : "minutos"}`;
}

const UNIDADE: Record<Periodicidade, [string, string]> = { diaria: ["diária", "diárias"], semanal: ["semana", "semanas"], mensal: ["mês", "meses"] };

/** "2 semanas". */
export function textoDoPeriodo(periodos: number, periodicidade: Periodicidade): string {
  const [um, varios] = UNIDADE[periodicidade];
  return `${periodos} ${periodos === 1 ? um : varios}`;
}

const FORMAS: Record<string, string> = { pix: "Pix", pix_automatico: "Pix automático", cartao: "Cartão", dinheiro: "Dinheiro", boleto: "Boleto", caucao: "Caução" };
export const rotuloDaForma = (forma: string) => FORMAS[forma] ?? forma;

const ROTULO_PARCELA: Record<StatusParcela, string> = {
  aberta: "Em aberto",
  vence_hoje: "Vence hoje",
  atrasada: "Atrasada",
  paga: "Pago",
  renegociada: "Renegociada",
  cancelada: "Cancelada",
  estornada: "Estornada",
};
const TOM_PARCELA: Record<StatusParcela, TomStatus> = { aberta: "neutro", vence_hoje: "alerta", atrasada: "critico", paga: "sucesso", renegociada: "atencao", cancelada: "neutro", estornada: "neutro" };

/** Selo da parcela: "Pago · Pix", "Atrasada", ou a observação da caução paga ("Devolver na entrega"). */
export function seloDaParcela(p: Pick<ParcelaDaLocacao, "tipo" | "status" | "forma" | "observacao">): { texto: string; tom: TomStatus } {
  if (p.tipo === "caucao" && p.status === "paga" && p.observacao) return { texto: p.observacao, tom: "info" };
  const base = ROTULO_PARCELA[p.status];
  return { texto: p.status === "paga" && p.forma ? `${base} · ${rotuloDaForma(p.forma)}` : base, tom: TOM_PARCELA[p.status] };
}

/** "1", "2" e "Caução" na coluna Parcela. */
export function rotuloDaParcela(p: Pick<ParcelaDaLocacao, "tipo" | "numero">): string {
  if (p.tipo === "caucao") return "Caução";
  if (p.tipo === "acerto") return "Acerto";
  return String(p.numero ?? "");
}

/** O que a locação mostra sobre o cancelamento: a multa e o valor a devolver são sempre a estimativa para a data (T-116). */
export function textoDaEstimativa(data: string | null): string {
  return data ? `Estimativa para ${dataCurta(data)}. O valor final sai na devolução.` : "Estimativa. O valor final sai na devolução.";
}

const ROTULO_VISTORIA_DA_TROCA: Record<"rascunho" | "concluida" | "descartada", string> = { rascunho: "Em andamento", concluida: "Concluída", descartada: "Descartada" };
export const rotuloDaVistoriaDaTroca = (status: keyof typeof ROTULO_VISTORIA_DA_TROCA) => ROTULO_VISTORIA_DA_TROCA[status];

/**
 * "Enviar contrato" (LOC-04, docs/api/contratos.md): locação aguardando a retirada, sem contrato vigente e sem desconto à espera de decisão.
 * A API ainda não manda uma ação para isso; `acoes.cancelar` só vem para quem cria locação, então vale como o perfil. A API recusa o que não couber (403, 409, 422).
 */
export function podeEnviarContrato(l: Pick<LocacaoCompleta, "status" | "contrato" | "desconto" | "acoes">): boolean {
  const semVigente = !l.contrato || l.contrato.status === "cancelado";
  return l.status === "aguardando_retirada" && semVigente && l.desconto?.status !== "pendente" && !!l.acoes.cancelar;
}
