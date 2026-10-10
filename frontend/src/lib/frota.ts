import type { Veiculo } from "@/lib/api";
import { dataCurta, dinheiro, km, nomeCurto } from "@/lib/formatos";

/** Terceiro dado do cartão do celular: o que mais interessa conforme a situação (a API já decidiu a situação). */
export function fatoDoVeiculo(v: Veiculo): { rotulo: string; valor: string } {
  if (v.locacao_atual && v.status === "reservado") return { rotulo: "Retirada", valor: dataCurta(v.locacao_atual.inicio) };
  if (v.locacao_atual) return { rotulo: "Cliente", valor: nomeCurto(v.locacao_atual.cliente_nome) };
  if (v.manutencao?.os_aberta) return { rotulo: "OS", valor: v.manutencao.os_aberta.codigo };
  if (v.manutencao?.proxima) return { rotulo: "Revisão", valor: km(v.manutencao.proxima.km) };
  return { rotulo: "Filial", valor: v.filial.nome };
}

export const diaria = (v: Veiculo) => dinheiro(v.preco_vigente.diaria_centavos);

/** Rótulo e tom do documento do veículo a partir do que a API devolveu. */
export function situacaoDoDocumento(
  situacao: "em_dia" | "vence_em_breve" | "vencido",
  dias: number | null,
  rotuloFixo?: string,
): { rotulo: string; tom: "sucesso" | "alerta" | "critico" } {
  if (rotuloFixo && situacao === "em_dia") return { rotulo: rotuloFixo, tom: "sucesso" };
  if (situacao === "vencido") return { rotulo: "Vencido", tom: "critico" };
  if (situacao === "vence_em_breve") return { rotulo: dias === null ? "Vence em breve" : `Vence em ${dias} ${dias === 1 ? "dia" : "dias"}`, tom: "alerta" };
  return { rotulo: "Em dia", tom: "sucesso" };
}
