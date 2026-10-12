import { z } from "zod";
import type { EntradaDaLocacao, ExtraDeLocacao, FormaPagamento, LocacaoCompleta, ParcelamentoMensal, PlanoEspecial, Periodicidade } from "@/lib/api";
import { agoraDaTela } from "@/lib/ambiente";
import { instanteDeLocal, localDeInstante } from "@/lib/formatos";

/** Modalidade escolhida na tela: uma periodicidade da tabela ou um plano especial (`especial:<id>`). */
export type Modalidade = Periodicidade | `especial:${number}`;

export const FORMAS_DE_PAGAMENTO: { valor: FormaPagamento; rotulo: string }[] = [
  { valor: "pix_automatico", rotulo: "Pix automático" },
  { valor: "pix", rotulo: "Pix" },
  { valor: "cartao", rotulo: "Cartão" },
  { valor: "boleto", rotulo: "Boleto" },
  { valor: "dinheiro", rotulo: "Dinheiro" },
];

/** Só o que a tela precisa ter para chamar a API; o resto (formato, limites, regras) é conferido por ela e o erro volta no campo. */
export const esquemaLocacao = z.object({
  cliente_id: z.number().int().positive("Escolha o cliente"),
  veiculo_id: z.number().int().positive("Escolha o veículo"),
  modalidade: z.string().min(1),
  inicio: z.string().min(1, "Informe a retirada"),
  fim: z.string(),
  extras: z.array(z.number()),
  desconto: z.string().trim(),
  forma_pagamento: z.enum(["pix", "pix_automatico", "cartao", "boleto", "dinheiro"]),
  parcelamento_mensal: z.enum(["a_vista", "quatro_semanais"]),
  primeiro_vencimento: z.string(),
});
export type ValoresLocacao = Omit<z.infer<typeof esquemaLocacao>, "modalidade" | "cliente_id" | "veiculo_id"> & { modalidade: Modalidade; cliente_id: number | null; veiculo_id: number | null };

/** "07/10 09:30" arredondado para os próximos 30 minutos, em `datetime-local`. */
export function retiradaPadrao(agora = agoraDaTela()): string {
  const meia = 30 * 60_000;
  return localDeInstante(new Date(Math.ceil(agora.getTime() / meia) * meia).toISOString());
}

export function valoresIniciais(cliente: number | null, veiculo: number | null, agora = agoraDaTela()): ValoresLocacao {
  return { cliente_id: cliente, veiculo_id: veiculo, modalidade: "semanal", inicio: retiradaPadrao(agora), fim: "", extras: [], desconto: "0", forma_pagamento: "pix_automatico", parcelamento_mensal: "a_vista", primeiro_vencimento: "" };
}

/** Percentual com até 2 casas ("5", "2,5"). A validação final é da API. */
export const descontoValido = (t: string) => /^\d+([.,]\d{1,2})?$/.test(t.trim());

const periodicidadeDe = (m: Modalidade, planos: PlanoEspecial[]): Periodicidade => (m.startsWith("especial:") ? (planos.find((p) => `especial:${p.id}` === m)?.periodicidade ?? "semanal") : (m as Periodicidade));

/** Corpo de simular, criar e atualizar. `null` enquanto falta cliente, veículo ou uma data válida. */
export function corpoDaLocacao(v: ValoresLocacao, planos: PlanoEspecial[]): EntradaDaLocacao | null {
  const inicio = instanteDeLocal(v.inicio);
  if (!v.cliente_id || !v.veiculo_id || !inicio || !descontoValido(v.desconto)) return null;
  const periodicidade = periodicidadeDe(v.modalidade, planos);
  const fim = instanteDeLocal(v.fim);
  return {
    cliente_id: v.cliente_id,
    veiculo_id: v.veiculo_id,
    periodicidade,
    plano_especial_id: v.modalidade.startsWith("especial:") ? Number(v.modalidade.slice(9)) : null,
    inicio,
    periodos: fim ? null : 1,
    fim_previsto: fim,
    extras: v.extras.map((extra_id) => ({ extra_id, quantidade: 1 })),
    desconto_pct: v.desconto.trim().replace(",", "."),
    forma_pagamento: v.forma_pagamento,
    parcelamento_mensal: periodicidade === "mensal" ? (v.parcelamento_mensal as ParcelamentoMensal) : null,
  };
}

/** Volta um rascunho (detalhe da locação) para o formulário, para retomar de onde parou. */
export function valoresDoRascunho(l: LocacaoCompleta, extras: ExtraDeLocacao[]): ValoresLocacao {
  const periodicidade = l.periodicidade;
  return {
    cliente_id: l.cliente.id,
    veiculo_id: l.veiculo.id,
    modalidade: l.plano_especial ? `especial:${l.plano_especial.id}` : periodicidade,
    inicio: l.inicio ? localDeInstante(l.inicio) : "",
    fim: l.fim_previsto ? localDeInstante(l.fim_previsto) : "",
    extras: (l.extras ?? []).flatMap((e) => extras.find((x) => x.nome === e.nome)?.id ?? []),
    desconto: l.precos?.desconto_pct ?? "0",
    forma_pagamento: (l.forma_pagamento as FormaPagamento) || "pix",
    parcelamento_mensal: (l.parcelamento_mensal as ParcelamentoMensal | null) ?? "a_vista",
    primeiro_vencimento: l.primeiro_vencimento ?? "",
  };
}

/** Opções de Parcelamento por modalidade (os textos da referência); o cronograma real vem da simulação. */
export function opcoesDeParcelamento(p: Periodicidade): { valor: ParcelamentoMensal; rotulo: string }[] {
  if (p === "diaria") return [{ valor: "a_vista", rotulo: "À vista na retirada" }];
  if (p === "semanal") return [{ valor: "a_vista", rotulo: "Semanal · cobra a cada 7 dias" }];
  return [
    { valor: "a_vista", rotulo: "Mensal · cobra a cada mês" },
    { valor: "quatro_semanais", rotulo: "Mensal em 4 semanais" },
  ];
}
