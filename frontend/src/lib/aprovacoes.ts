// Textos de Aprovações. Título, detalhe, estado e quem pode decidir vêm prontos da API (docs/api/aprovacoes.md); aqui só rótulos e formatação.
import type { QueryClient } from "@tanstack/react-query";
import type { PedidoDeAprovacao, TipoDoPedido } from "@/lib/api";
import { dataCurta } from "@/lib/formatos";

/**
 * Depois de aprovar, recusar ou cancelar: as listas de pedidos e despesas e os números do menu (Aprovações, Despesas)
 * são lidos de novo na hora, sem esperar o intervalo de 60 s dos contadores (T-241).
 */
export function atualizarAposDecisao(cliente: QueryClient): Promise<unknown> {
  return Promise.all(["aprovacoes", "despesas", "contadores"].map((k) => cliente.invalidateQueries({ queryKey: [k] })));
}

export const TIPOS_DE_PEDIDO: { valor: TipoDoPedido; rotulo: string; efeito: string }[] = [
  { valor: "APR-01", rotulo: "Desconto", efeito: "Ao aprovar, o preço com desconto é liberado." },
  { valor: "APR-02", rotulo: "Cancelamento", efeito: "Ao aprovar, a locação é cancelada e a multa e o acerto são calculados." },
  { valor: "APR-03", rotulo: "Despesa", efeito: "Acima de R$ 500 precisa da sua aprovação. Aprovada, vai para o financeiro pagar." },
  { valor: "APR-04", rotulo: "Diferença de caixa", efeito: "Ao aprovar, o caixa fecha com a diferença registrada." },
  { valor: "APR-05", rotulo: "Desbloqueio", efeito: "Ao aprovar, o cliente volta a ficar ativo." },
  { valor: "APR-06", rotulo: "Correção de km", efeito: "Ao aprovar, o km é corrigido com o motivo do pedido." },
];

export const rotuloDoTipo = (t: TipoDoPedido): string => TIPOS_DE_PEDIDO.find((x) => x.valor === t)?.rotulo ?? t;
export const efeitoDoTipo = (t: TipoDoPedido): string => TIPOS_DE_PEDIDO.find((x) => x.valor === t)?.efeito ?? "";

/** "há 40 min", "há 2 h", "há 3 dias": quanto o pedido espera ou esperou. */
export function haQuanto(iso: string, agora: Date): string {
  const min = Math.max(0, Math.floor((agora.getTime() - new Date(iso).getTime()) / 60_000));
  if (min < 1) return "agora há pouco";
  if (min < 60) return `há ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `há ${h} h`;
  const d = Math.floor(h / 24);
  return `há ${d} ${d === 1 ? "dia" : "dias"}`;
}

/** Para onde o "Ver ..." do pedido leva. Venda e ordem de serviço ainda não têm tela: sem link. */
export function linkDaOrigem(o: PedidoDeAprovacao["origem"]): { href: string; rotulo: string } | null {
  switch (o.tipo) {
    case "despesa":
      return { href: `/financeiro/despesas/${o.id}`, rotulo: "Ver despesa" };
    case "locacao":
      return { href: `/locacoes/${o.id}`, rotulo: "Ver locação" };
    case "cliente":
      return { href: `/clientes/${o.id}`, rotulo: "Ver cliente" };
    case "veiculo":
      return { href: `/veiculos/${o.id}`, rotulo: "Ver veículo" };
    case "caixa":
      return { href: "/financeiro/caixa", rotulo: "Ver caixa" };
    default:
      return null;
  }
}

/** "Rodrigo aprovou · 06 out · motivo": a linha de "Decididas recentemente". */
export function linhaDaDecisao(p: Pick<PedidoDeAprovacao, "status" | "decidido_por" | "decidido_em" | "motivo_recusa" | "detalhe">): string {
  const quem = p.decidido_por ? p.decidido_por.nome.split(" ")[0] : "Quem pediu";
  const verbo = p.status === "aprovado" ? "aprovou" : p.status === "recusado" ? "recusou" : "cancelou";
  const quando = p.decidido_em ? dataCurta(p.decidido_em) : "";
  const motivo = p.status === "recusado" && p.motivo_recusa ? `"${p.motivo_recusa}"` : p.status === "aprovado" ? p.detalhe : "";
  return [`${quem} ${verbo}`, quando, motivo].filter(Boolean).join(" · ");
}
