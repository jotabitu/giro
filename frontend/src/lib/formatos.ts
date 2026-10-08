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

/** "12.430 km". */
export function km(valor: number): string {
  return `${new Intl.NumberFormat("pt-BR").format(valor)} km`;
}

/** Placa sem hífen da API para "SAK-1D39". */
export function placa(p: string): string {
  return p.length === 7 ? `${p.slice(0, 3)}-${p.slice(3)}` : p;
}

/** "mar 2026" para "cliente desde" e datas de compra. */
export function mesAno(iso: string): string {
  const d = paraData(iso);
  const partes = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", month: "numeric", year: "numeric" }).formatToParts(d);
  const mes = Number(partes.find((p) => p.type === "month")?.value ?? "1");
  return `${MESES[mes - 1]} ${partes.find((p) => p.type === "year")?.value ?? ""}`;
}

export function soDigitos(t: string): string {
  return t.replace(/\D/g, "");
}

/** "85988771203" para "(85) 98877-1203". Número incompleto sai como veio. */
export function celular(n: string): string {
  const d = soDigitos(n);
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return n;
}

/** Máscaras enquanto a pessoa digita; a API recebe só os dígitos. */
export function mascaraCelular(t: string): string {
  const d = soDigitos(t).slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

export function mascaraCpf(t: string): string {
  const d = soDigitos(t).slice(0, 11);
  return d.replace(/^(\d{3})(\d)/, "$1.$2").replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3").replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export function mascaraCnpj(t: string): string {
  const d = soDigitos(t).slice(0, 14);
  return d.replace(/^(\d{2})(\d)/, "$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3").replace(/\.(\d{3})(\d)/, ".$1/$2").replace(/(\d{4})(\d)/, "$1-$2");
}

export function mascaraCep(t: string): string {
  const d = soDigitos(t).slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

/** Percentual que a API manda como texto ("86.00") para "86%". */
export function percentual(texto: string): string {
  return `${Math.round(Number(texto))}%`;
}

/** "Carlos Menezes" para "Carlos M." (cartão do celular). */
export function nomeCurto(nome: string): string {
  const partes = nome.trim().split(/\s+/);
  const ultimo = partes.length > 1 ? partes[partes.length - 1] : undefined;
  return ultimo ? `${partes[0]} ${ultimo.charAt(0)}.` : (partes[0] ?? "");
}

/** "Lucas Ferreira" para "LF" (avatar da lista de clientes). */
export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  const primeira = partes[0]?.charAt(0) ?? "";
  const ultima = partes.length > 1 ? (partes[partes.length - 1]?.charAt(0) ?? "") : "";
  return (primeira + ultima).toUpperCase();
}
