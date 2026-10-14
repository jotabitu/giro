// Apoio da tela de Despesas. A API decide o estado e o texto da situação; aqui só datas de formulário e o corpo do envio.
import type { NovaDespesa, CategoriaDaDespesa } from "@/lib/api";
import { diaDe, instanteDeLocal } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";

export const TAMANHO_MAXIMO_DA_NOTA = 10 * 1024 * 1024;

/** "2026-10" do instante dado, em America/Sao_Paulo: o `?mes=` da lista. */
export const mesDe = (agora: Date): string => diaDe(agora.toISOString()).slice(0, 7);

/** "Outubro" a partir do mês "2026-10". */
export function nomeDoMes(mes: string): string {
  const nome = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", month: "long" }).format(new Date(`${mes}-15T12:00:00-03:00`));
  return nome.charAt(0).toUpperCase() + nome.slice(1);
}

/** Instante de pagamento para um dia de formulário: hoje vale agora; outro dia vale o meio-dia de Brasília. */
export function pagoEmDoDia(dia: string, agora: Date): string {
  if (dia === diaDe(agora.toISOString())) return agora.toISOString();
  return instanteDeLocal(`${dia}T12:00`) ?? agora.toISOString();
}

export type ValoresDaDespesa = {
  descricao: string;
  valor: string;
  data: string;
  vencimento: string;
  categoria: CategoriaDaDespesa;
  veiculoId: number | null;
  nota: File | null;
  pagoNoCaixa: boolean;
};

/** Só o que a tela precisa para chamar a API. Valor, limite de R$ 500 e perfil são conferidos por ela. */
export function corpoDaDespesa(v: ValoresDaDespesa): NovaDespesa | null {
  const centavos = centavosDoTexto(v.valor);
  if (centavos === null || v.descricao.trim() === "" || v.data === "" || v.nota === null) return null;
  return {
    descricao: v.descricao.trim(),
    valor_centavos: centavos,
    data: v.data,
    vencimento: v.vencimento || v.data,
    categoria: v.categoria,
    veiculo_id: v.veiculoId,
    nota: v.nota,
    pago_no_caixa: v.pagoNoCaixa,
  };
}
