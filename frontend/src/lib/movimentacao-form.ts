import { z } from "zod";
import type { NovaMovimentacao } from "@/lib/api";
import { instanteDeLocal } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";

// Formulário da Nova movimentação (T-289, docs/api/movimentacoes.md, MOV-01). O esquema só confere o que falta preencher;
// quem vale é a API (veículo que não se movimenta, local inativo, categoria no destino, hora no passado).

const paradaVazia = { local_id: "", servico: "", valor_previsto: "" };

export const esquemaMovimentacao = z
  .object({
    veiculo_id: z.string().min(1, "Escolha o veículo."),
    paradas: z.array(
      z.object({
        local_id: z.string().min(1, "Escolha o local de apoio."),
        servico: z.string().trim().min(1, "Diga o serviço."),
        valor_previsto: z.string().refine((t) => t.trim() === "" || centavosDoTexto(t) !== null, "Informe um valor, como 35,00."),
      }),
    ),
    destino_filial_id: z.string().min(1, "Escolha a filial de destino."),
    categoria_destino_id: z.string(),
    levado_por_id: z.string().min(1, "Escolha quem leva."),
    quando: z.enum(["agora", "agendar"]),
    dia: z.string(),
    hora: z.string(),
    vistoria_rapida: z.boolean(),
  })
  .superRefine((v, ctx) => {
    if (v.quando !== "agendar") return;
    if (!v.dia) ctx.addIssue({ code: "custom", path: ["dia"], message: "Informe o dia." });
    if (!v.hora) ctx.addIssue({ code: "custom", path: ["hora"], message: "Informe a hora." });
  });

export type ValoresMovimentacao = z.infer<typeof esquemaMovimentacao>;

export const VALORES_INICIAIS_MOVIMENTACAO: ValoresMovimentacao = {
  veiculo_id: "",
  paradas: [],
  destino_filial_id: "",
  categoria_destino_id: "",
  levado_por_id: "",
  quando: "agora",
  dia: "",
  hora: "",
  vistoria_rapida: false,
};

export const novaParada = () => ({ ...paradaVazia });

/** Corpo do POST /api/movimentacoes/. Categoria da parada fica de fora (a API aplica o padrão da MOV-04); a hora vai em UTC. */
export function paraCorpoMovimentacao(v: ValoresMovimentacao): NovaMovimentacao {
  const agendada = v.quando === "agendar" ? instanteDeLocal(`${v.dia}T${v.hora}`) : null;
  return {
    veiculo_id: Number(v.veiculo_id),
    paradas: v.paradas.map((p) => ({ local_id: Number(p.local_id), servico: p.servico.trim(), valor_previsto_centavos: centavosDoTexto(p.valor_previsto) ?? 0 })),
    destino_filial_id: Number(v.destino_filial_id),
    categoria_destino_id: v.categoria_destino_id ? Number(v.categoria_destino_id) : null,
    levado_por_id: Number(v.levado_por_id),
    sair_agora: v.quando === "agora",
    agendada_para: agendada,
    vistoria_rapida: v.vistoria_rapida,
  };
}

/** Campo da API no corpo → campo do formulário (`paradas[0].local_id` vira `paradas.0.local_id`). */
export function campoDoFormulario(campo: string): string {
  const parada = /^paradas\[(\d+)\]\.(local_id|servico|valor_previsto_centavos)$/.exec(campo);
  if (parada) return `paradas.${parada[1]}.${parada[2] === "valor_previsto_centavos" ? "valor_previsto" : parada[2]}`;
  const simples: Record<string, string> = { veiculo_id: "veiculo_id", destino_filial_id: "destino_filial_id", categoria_destino_id: "categoria_destino_id", levado_por_id: "levado_por_id", agendada_para: "dia" };
  return simples[campo] ?? "";
}
