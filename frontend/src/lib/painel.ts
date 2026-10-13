import { agoraDaTela } from "@/lib/ambiente";
import { dataCurta, dinheiro } from "@/lib/formatos";
import type { ValorTipado } from "@/lib/api";
import { tomDoStatus } from "@/lib/tom";

/** Percentual da API ("71.00", "66.67") em "71%" e "66,67%". */
export function percentual(texto: string): string {
  const [inteiro = "0", casas = ""] = texto.split(".");
  const util = casas.replace(/0+$/, "");
  return `${inteiro}${util ? `,${util}` : ""}%`;
}

/** Dinheiro curto do KPI: "R$ 18,4 mil" a partir de R$ 10.000; abaixo disso, o valor inteiro ("R$ 1.646,40"). */
export function dinheiroCurto(centavos: number): string {
  const reais = centavos / 100;
  if (Math.abs(reais) < 10_000) return dinheiro(centavos);
  const mil = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(reais / 1000);
  return `R$ ${mil.replace(/,0$/, "")} mil`;
}

/** Só formata. O número já veio calculado da API. */
export function formatarValor(v: ValorTipado): string {
  if (v.tipo === "centavos") return dinheiroCurto(v.valor);
  if (v.tipo === "pct") return percentual(v.valor);
  return new Intl.NumberFormat("pt-BR").format(v.valor);
}

export { tomDoStatus };

/** "atualizado há 6 min" a partir de `atualizado_em`. */
export function atualizadoHa(iso: string, agora = new Date()): string {
  const min = Math.max(0, Math.round((agora.getTime() - new Date(iso).getTime()) / 60_000));
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  const h = Math.floor(min / 60);
  return h < 24 ? `há ${h} h` : `há ${Math.floor(h / 24)} d`;
}

/** Horário da agenda em "09:30" no fuso de Brasília. */
export function horaCurta(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(iso));
}

const PERFIL: Record<string, string> = { administrador: "Administrador", gerente: "Gerente", vendedor: "Vendedor", vistoriador: "Vistoriador", financeiro: "Financeiro" };

export function rotuloDoPerfil(perfil: string): string {
  return PERFIL[perfil] ?? perfil;
}

const diaSp = (d: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(d);

/** "09:30" quando é hoje; "06 out 18:00" nos outros dias (devolução atrasada). */
export function horarioDaAgenda(iso: string, agora = agoraDaTela()): string {
  const d = new Date(iso);
  if (diaSp(d) === diaSp(agora)) return horaCurta(iso);
  return `${dataCurta(iso)} ${horaCurta(iso)}`;
}
