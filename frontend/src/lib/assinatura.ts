// Textos de Administração › Assinatura. Plano, preço, estado, faixa de aviso e uso vêm da API (docs/api/plataforma.md, "Do lado da empresa").
import type { TomStatus } from "@/design-system";
import type { Assinatura, UsoDoItemDaAssinatura } from "@/lib/api";
import { dataCurta, dinheiro } from "@/lib/formatos";

const SITUACAO: Record<string, { rotulo: string; tom: TomStatus }> = {
  ativa: { rotulo: "Ativa", tom: "sucesso" },
  inadimplente: { rotulo: "Fatura em atraso", tom: "alerta" },
  suspensa: { rotulo: "Suspensa", tom: "critico" },
  pausada: { rotulo: "Pausada", tom: "neutro" },
  cancelada: { rotulo: "Cancelada", tom: "neutro" },
};

/** "Teste grátis até 21 out" no teste; nos outros estados, o rótulo do estado. Estado desconhecido aparece como veio. */
export function situacaoDaAssinatura(a: Pick<Assinatura, "status" | "teste">): { rotulo: string; tom: TomStatus } {
  if (a.status === "em_teste") return { rotulo: a.teste ? `Teste grátis até ${dataCurta(a.teste.fim)}` : "Teste grátis", tom: "marca" };
  return SITUACAO[a.status] ?? { rotulo: a.status, tom: "neutro" };
}

/** "R$ 449,00 por mês" (ou "por ano"); durante o teste, o preço vale depois dele. */
export function precoDoPlano(a: Pick<Assinatura, "plano" | "status">): string {
  const ciclo = a.plano.ciclo === "anual" ? "por ano" : "por mês";
  return `${dinheiro(a.plano.preco_contratado_centavos)} ${ciclo}${a.status === "em_teste" ? ", depois do teste" : ""}`;
}

export const ITENS_DO_USO = [
  { chave: "veiculos", singular: "veículo", plural: "veículos", rotulo: "Veículos" },
  { chave: "filiais", singular: "filial", plural: "filiais", rotulo: "Filiais" },
  { chave: "usuarios", singular: "usuário", plural: "usuários", rotulo: "Usuários" },
] as const;

/** Largura da barra: o quanto do limite já foi usado (0 a 100). Sem limite, a barra fica vazia. */
export const percentualDeUso = (u: Pick<UsoDoItemDaAssinatura, "usado" | "limite">): number => (u.limite ? Math.min(100, (u.usado / u.limite) * 100) : 0);

/** Aviso a partir de 90% e bloqueio em 100% (PLT-03); o texto diz o que muda, sem depender só da cor. */
export function avisoDeUso(u: Pick<UsoDoItemDaAssinatura, "aviso" | "bloqueado">): string | null {
  if (u.bloqueado) return "No limite: não dá para cadastrar mais. O que já existe continua funcionando.";
  if (u.aviso) return "Perto do limite.";
  return null;
}
