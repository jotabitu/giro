const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

function paraData(iso: string): Date {
  return /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T12:00:00-03:00`) : new Date(iso);
}

/** Centavos em "R$ 1.250,00". */
export function dinheiro(centavos: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(centavos / 100).replace(/ /g, " ");
}

/** "06 out" para listas. Aceita AAAA-MM-DD ou instante UTC; o dia é o de America/Sao_Paulo. */
export function dataCurta(iso: string): string {
  const partes = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", day: "2-digit", month: "numeric" }).formatToParts(paraData(iso));
  const dia = partes.find((p) => p.type === "day")?.value ?? "";
  const mes = Number(partes.find((p) => p.type === "month")?.value ?? "1");
  return `${dia} ${MESES[mes - 1]}`;
}

/** "06/10/2026" para formulários. */
export function dataCompleta(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", day: "2-digit", month: "2-digit", year: "numeric" }).format(paraData(iso));
}

/** Saudação pela hora de Brasília. */
export function saudacao(agora = new Date()): string {
  const h = Number(new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", hour: "2-digit", hour12: false }).format(agora)) % 24;
  return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite";
}
