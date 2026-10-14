import type { Combustivel, PendenciaDaVistoria, PosicaoFoto, Vistoria } from "@/lib/api";
import { ErroApi, vistorias as apiVistorias } from "@/lib/api";

/** Os cinco níveis do tanque, na ordem da tela (Reserva, 1/4, 1/2, 3/4, Cheio). */
export const NIVEIS: { valor: Combustivel; rotulo: string; curto: string }[] = [
  { valor: "reserva", rotulo: "Reserva", curto: "R" },
  { valor: "um_quarto", rotulo: "1/4", curto: "1/4" },
  { valor: "meio", rotulo: "1/2", curto: "1/2" },
  { valor: "tres_quartos", rotulo: "3/4", curto: "3/4" },
  { valor: "cheio", rotulo: "Cheio", curto: "4/4" },
];

export const rotuloDoNivel = (c: Combustivel | null): string => (c ? (NIVEIS.find((n) => n.valor === c)?.rotulo ?? c) : "—");

/** "saiu com tanque cheio", "saiu com 3/4". */
export const textoDoNivelNaSaida = (c: Combustivel | null): string => (c === "cheio" ? "saiu com tanque cheio" : c ? `saiu com ${rotuloDoNivel(c)}` : "");

/** Posições das fotos na ordem da tela; a última (avaria) não é obrigatória. */
export const POSICOES: { valor: PosicaoFoto; rotulo: string; obrigatoria: boolean }[] = [
  { valor: "frente", rotulo: "Frente", obrigatoria: true },
  { valor: "traseira", rotulo: "Traseira", obrigatoria: true },
  { valor: "lado_esquerdo", rotulo: "Lateral esquerda", obrigatoria: true },
  { valor: "lado_direito", rotulo: "Lateral direita", obrigatoria: true },
  { valor: "painel", rotulo: "Painel e hodômetro", obrigatoria: true },
  { valor: "avaria", rotulo: "Foto de avaria", obrigatoria: false },
];

export const rotuloDaPosicao = (p: string): string => POSICOES.find((x) => x.valor === p)?.rotulo ?? p;

/** "3 de 5 obrigatórias". */
export const textoDeFotos = (v: Pick<Vistoria, "fotos_obrigatorias">): string => `${v.fotos_obrigatorias.feitas} de ${v.fotos_obrigatorias.total} obrigatórias`;

/** O que falta para concluir, no texto da tela ("Faltam 2 fotos obrigatórias"). A lista de códigos vem da API (`pendencias`). */
export function textoDaPendencia(v: Pick<Vistoria, "pendencias" | "fotos_obrigatorias">): string | null {
  const [primeira] = v.pendencias;
  if (!primeira) return null;
  if (primeira === "fotos") {
    const n = v.fotos_obrigatorias.faltam.length;
    return `${n === 1 ? "Falta" : "Faltam"} ${n} ${n === 1 ? "foto obrigatória" : "fotos obrigatórias"}`;
  }
  if (primeira === "km") return "Informe a quilometragem";
  if (primeira === "combustivel") return "Informe o nível de combustível";
  if (primeira === "itens") return "Confira todos os itens da lista";
  return primeira;
}

/** As pendências do 422 `detalhes.pendencias` (todas de uma vez), ou a mensagem única do erro. */
export function pendenciasDoErro(erro: unknown): PendenciaDaVistoria[] {
  if (!(erro instanceof ErroApi) || erro.status !== 422) return [];
  const lista = erro.detalhes?.pendencias;
  if (Array.isArray(lista) && lista.length > 0) return lista as PendenciaDaVistoria[];
  return [{ codigo: erro.codigo, mensagem: erro.message }];
}

/** Para onde a pendência leva a pessoa: o veículo (km, documentos) ou a locação (cadastro do cliente). */
export function linkDaPendencia(p: PendenciaDaVistoria, v: Pick<Vistoria, "veiculo" | "locacao">): { href: string; rotulo: string } | null {
  if (p.codigo === "VEI-01") return { href: `/veiculos/${v.veiculo.id}`, rotulo: "Corrigir km" };
  if (p.codigo === "VEI-03") return { href: `/veiculos/${v.veiculo.id}`, rotulo: "Ver documentos" };
  if (p.codigo.startsWith("CLI-")) return { href: `/locacoes/${v.locacao.id}`, rotulo: "Ver a locação" };
  return null;
}

/**
 * A mensagem do `VEI-01` ("O km informado é menor que o atual…") para a vistoria com km digitado.
 * A vistoria só traz o código curto da pendência; a mensagem vem do 422 da conclusão, que com o km pendente nunca conclui.
 */
export async function avisoDoKmDaApi(v: Pick<Vistoria, "id" | "km" | "pendencias">): Promise<PendenciaDaVistoria | null> {
  if (v.km === null || !v.pendencias.includes("km")) return null;
  try {
    await apiVistorias.concluir(v.id);
    return null;
  } catch (erro) {
    return pendenciasDoErro(erro).find((p) => p.codigo === "VEI-01") ?? null;
  }
}
