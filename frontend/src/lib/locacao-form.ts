import { z } from "zod";
import type { EntradaDaLocacao, ExtraDeLocacao, FormaPagamento, LocacaoCompleta, Periodicidade, PlanoDoVeiculo, TipoDaLocacao } from "@/lib/api";
import { agoraDaTela } from "@/lib/ambiente";
import { dinheiro, instanteDeLocal, localDeInstante } from "@/lib/formatos";
import { textoDoPagamento } from "@/lib/precos-veiculo";

export const FORMAS_DE_PAGAMENTO: { valor: FormaPagamento; rotulo: string }[] = [
  { valor: "pix_automatico", rotulo: "Pix automático" },
  { valor: "pix", rotulo: "Pix" },
  { valor: "cartao", rotulo: "Cartão" },
  { valor: "boleto", rotulo: "Boleto" },
  { valor: "dinheiro", rotulo: "Dinheiro" },
];

/** Só o que a tela precisa ter para chamar a API; o resto (formato, limites, regras) é conferido por ela e o erro volta no campo. */
export const esquemaLocacao = z.object({
  tipo: z.enum(["comum", "intencao_compra"]),
  plano_veiculo_id: z.number().int().positive().nullable(),
  cliente_id: z.number().int().positive("Escolha o cliente"),
  veiculo_id: z.number().int().positive("Escolha o veículo"),
  inicio: z.string().min(1, "Informe a retirada"),
  fim: z.string(),
  extras: z.array(z.number()),
  desconto: z.string().trim(),
  forma_pagamento: z.enum(["pix", "pix_automatico", "cartao", "boleto", "dinheiro"]),
  primeiro_vencimento: z.string(),
});
export type ValoresLocacao = Omit<z.infer<typeof esquemaLocacao>, "cliente_id" | "veiculo_id" | "tipo"> & { tipo: TipoDaLocacao } & { cliente_id: number | null; veiculo_id: number | null };

/** "07/10 09:30" arredondado para os próximos 30 minutos, em `datetime-local`. */
export function retiradaPadrao(agora = agoraDaTela()): string {
  const meia = 30 * 60_000;
  return localDeInstante(new Date(Math.ceil(agora.getTime() / meia) * meia).toISOString());
}

export function valoresIniciais(cliente: number | null, veiculo: number | null, agora = agoraDaTela()): ValoresLocacao {
  return { tipo: "comum", plano_veiculo_id: null, cliente_id: cliente, veiculo_id: veiculo, inicio: retiradaPadrao(agora), fim: "", extras: [], desconto: "0", forma_pagamento: "pix_automatico", primeiro_vencimento: "" };
}

/** Percentual com até 2 casas ("5", "2,5"). A validação final é da API. */
export const descontoValido = (t: string) => /^\d+([.,]\d{1,2})?$/.test(t.trim());

/**
 * Corpo de simular, criar e atualizar. `null` enquanto falta cliente, veículo, plano ou uma data válida.
 * O valor, o período, o parcelamento do mês e a caução vêm do plano do veículo (LOC-01, ADR 0041): a tela só manda o id dele.
 */
export function corpoDaLocacao(v: ValoresLocacao, plano?: Pick<PlanoDoVeiculo, "id" | "prazo_minimo_periodos"> | null): EntradaDaLocacao | null {
  const inicio = instanteDeLocal(v.inicio);
  if (v.tipo === "intencao_compra") {
    // LOC-16: o plano é o de compra do veículo; prazo, parcelas e valor vêm dele. Sem desconto, extras nem parcelamento (CA-420-02).
    if (!v.cliente_id || !v.veiculo_id || !inicio) return null;
    return { tipo: "intencao_compra", cliente_id: v.cliente_id, veiculo_id: v.veiculo_id, inicio, extras: [], desconto_pct: "0", forma_pagamento: v.forma_pagamento };
  }
  const planoId = plano?.id ?? v.plano_veiculo_id;
  if (!v.cliente_id || !v.veiculo_id || !inicio || !descontoValido(v.desconto) || !planoId) return null;
  const fim = instanteDeLocal(v.fim);
  return {
    tipo: "comum",
    cliente_id: v.cliente_id,
    veiculo_id: v.veiculo_id,
    plano_veiculo_id: planoId,
    inicio,
    // VEI-12: o prazo mínimo do plano é o número de períodos de partida; a API confere o resto.
    periodos: fim ? null : (plano?.prazo_minimo_periodos ?? 1),
    fim_previsto: fim,
    extras: v.extras.map((extra_id) => ({ extra_id, quantidade: 1 })),
    desconto_pct: v.desconto.trim().replace(",", "."),
    forma_pagamento: v.forma_pagamento,
  };
}

/** Volta um rascunho (detalhe da locação) para o formulário, para retomar de onde parou. */
export function valoresDoRascunho(l: LocacaoCompleta, extras: ExtraDeLocacao[]): ValoresLocacao {
  return {
    tipo: l.tipo,
    plano_veiculo_id: l.plano_veiculo?.id ?? null,
    cliente_id: l.cliente.id,
    veiculo_id: l.veiculo.id,
    inicio: l.inicio ? localDeInstante(l.inicio) : "",
    fim: l.fim_previsto ? localDeInstante(l.fim_previsto) : "",
    extras: (l.extras ?? []).flatMap((e) => extras.find((x) => x.nome === e.nome)?.id ?? []),
    desconto: l.precos?.desconto_pct ?? "0",
    forma_pagamento: (l.forma_pagamento as FormaPagamento) || "pix",
    primeiro_vencimento: l.primeiro_vencimento ?? "",
  };
}

/** O período do plano do veículo (dia, semana, mês) na periodicidade da locação. */
export const periodicidadeDoPlano = (periodo: string | null | undefined): Periodicidade => (periodo === "dia" ? "diaria" : periodo === "mes" ? "mensal" : "semanal");

const POR_PERIODO: Record<string, string> = { dia: "dia", semana: "semana", mes: "mês" };

/** "R$ 329,00 / semana", "R$ 1.190,00 / mês": o valor e o período são os do plano (VEI-12). */
export const valorDoPlano = (p: Pick<PlanoDoVeiculo, "valor_centavos" | "periodo">): string => `${dinheiro(p.valor_centavos)} / ${POR_PERIODO[p.periodo ?? "semana"]}`;

/** As linhas do cartão do plano na Nova locação: como paga, caução, franquia e prazo mínimo, todos os textos do plano. */
export function linhasDoPlano(p: PlanoDoVeiculo): string[] {
  const periodo = POR_PERIODO[p.periodo ?? "semana"];
  const plural = p.periodo === "mes" ? "meses" : `${periodo}s`;
  const linhas: string[] = [];
  if (p.como_paga) linhas.push(textoDoPagamento(p.como_paga, p.parcela_do_mes));
  if (p.caucao_centavos != null) linhas.push(`Caução ${dinheiro(p.caucao_centavos)} ${p.caucao_parcelas <= 1 ? "à vista" : `em ${p.caucao_parcelas}x`}`);
  linhas.push(p.franquia_km == null ? "Km livre" : `${new Intl.NumberFormat("pt-BR").format(p.franquia_km)} km por ${periodo}`);
  if (p.prazo_minimo_periodos) linhas.push(`Mínimo de ${p.prazo_minimo_periodos} ${p.prazo_minimo_periodos === 1 ? periodo : plural}`);
  return linhas;
}

/** As formas de pagamento que o plano aceita (VEI-12). O Pix automático conta como Pix. */
export const formasDoPlano = (p: Pick<PlanoDoVeiculo, "formas_aceitas"> | undefined) =>
  FORMAS_DE_PAGAMENTO.filter((f) => !p || p.formas_aceitas.includes(f.valor === "pix_automatico" ? "pix" : f.valor));
