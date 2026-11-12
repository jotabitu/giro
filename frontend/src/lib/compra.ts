// Compra pública (docs/api/compra.md). Só formata o que a pessoa digita e o que a API devolve:
// preço, datas do teste, situação do CNPJ e textos dos passos vêm prontos da API.

export const soDigitos = (texto: string): string => texto.replace(/\D/g, "");

/** "12345678000195" vira "12.345.678/0001-95" enquanto a pessoa digita. */
export function mascararCnpj(texto: string): string {
  const d = soDigitos(texto).slice(0, 14);
  return d
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
}

/** "85998124410" vira "(85) 99812-4410"; fixo com 10 dígitos, "(85) 3212-4410". */
export function mascararCelular(texto: string): string {
  const d = soDigitos(texto).slice(0, 11);
  if (d.length <= 2) return d.length ? `(${d}` : "";
  const resto = d.slice(2);
  const corte = d.length === 11 ? 5 : 4;
  return resto.length > corte ? `(${d.slice(0, 2)}) ${resto.slice(0, corte)}-${resto.slice(corte)}` : `(${d.slice(0, 2)}) ${resto}`;
}

/** 44900 vira "R$ 449". Valor inteiro sem centavos, como no card do plano. */
export function reaisInteiros(centavos: number): string {
  return `R$ ${Math.floor(centavos / 100).toLocaleString("pt-BR")}`;
}

/** 44900 vira "R$ 449,00". */
export function reais(centavos: number): string {
  return `R$ ${(centavos / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** "2026-10-22" vira "22 out" (data sem hora, sem fuso). */
export function diaEMes(data: string): string {
  const [, mes, dia] = data.split("-").map(Number);
  return `${String(dia).padStart(2, "0")} ${MESES[(mes ?? 1) - 1]}`;
}

/** Hora em São Paulo de um momento da API ("09:12:04"). */
export function horaEmSaoPaulo(momento: string): string {
  return new Date(momento).toLocaleTimeString("pt-BR", { timeZone: "America/Sao_Paulo", hour12: false });
}

// A chave do pedido fica em memória e no sessionStorage da aba, nunca na URL (compra.md).
const CHAVE_DA_SESSAO = "giro.compra.pedido";

export function guardarPedido(chave: string | null): void {
  try {
    if (chave) sessionStorage.setItem(CHAVE_DA_SESSAO, chave);
    else sessionStorage.removeItem(CHAVE_DA_SESSAO);
  } catch {
    // aba privada ou armazenamento bloqueado: a chave fica só em memória
  }
}

export function pedidoGuardado(): string | null {
  try {
    return sessionStorage.getItem(CHAVE_DA_SESSAO);
  } catch {
    return null;
  }
}
