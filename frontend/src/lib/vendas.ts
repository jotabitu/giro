// Vendas (VEN-01 a VEN-19). Preço final, saldo, parcelas, comissão, "precisa do gerente", forma e situação vêm prontos da API
// (docs/api/vendas.md); aqui só rótulos, tons e formatação do que a pessoa digita. Nenhuma conta de negócio.
import type { QueryClient } from "@tanstack/react-query";
import type { CalculoDaVenda, FormaDaVenda, StatusDaVenda, Venda } from "@/lib/api";
import { dataCurta, dinheiro } from "@/lib/formatos";

export const FORMAS: { valor: FormaDaVenda; titulo: string; apoio: string }[] = [
  { valor: "a_vista", titulo: "À vista", apoio: "Pix ou TED" },
  { valor: "entrada_parcelas", titulo: "Entrada + parcelas", apoio: "boleto ou Pix mensal" },
];

/** Os estados em que a venda ainda está em andamento (VEN-13). */
export const EM_ANDAMENTO: StatusDaVenda[] = ["interessado", "proposta", "negociacao", "aguardando_aprovacao"];

/** Tom do selo da situação: a API manda o texto (`situacao_texto`); o tom só acompanha o estado. */
export function tomDaVenda(status: StatusDaVenda): "neutro" | "alerta" | "sucesso" | "info" {
  switch (status) {
    case "aguardando_aprovacao":
      return "alerta";
    case "vendida":
      return "sucesso";
    case "proposta":
    case "negociacao":
      return "info";
    default:
      return "neutro";
  }
}

const DIA_MS = 86_400_000;
const diaLocal = (d: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(d);

/** Último contato (VEN-16): "há 20 min", "há 1 h", "ontem", "há 8 dias". */
export function ultimoContato(iso: string | null | undefined, agora: Date): string {
  if (!iso) return "—";
  const quando = new Date(iso);
  const min = Math.max(0, Math.floor((agora.getTime() - quando.getTime()) / 60_000));
  if (min < 1) return "agora há pouco";
  if (min < 60) return `há ${min} min`;
  const hoje = diaLocal(agora);
  if (diaLocal(quando) === hoje) return min < 12 * 60 ? `há ${Math.floor(min / 60)} h` : "hoje";
  const dias = Math.round((Date.parse(hoje) - Date.parse(diaLocal(quando))) / DIA_MS);
  return dias === 1 ? "ontem" : `há ${dias} dias`;
}

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** "2026-10-07" → "outubro". */
export const mesPorExtenso = (hoje: string): string => MESES[Number(hoje.slice(5, 7)) - 1] ?? "";
/** "2026-10-07" → "2026-10" (o `?mes=` da lista). */
export const mesDoDia = (hoje: string): string => hoje.slice(0, 7);
export const comMaiuscula = (t: string): string => t.charAt(0).toUpperCase() + t.slice(1);

/** "8" ou "8,5" (o que se digita) → "8.00" e "8.50", como a API recebe. Vazio é 0. A API confere o limite. */
export function pctDoCampo(t: string): string {
  const limpo = t.replace(/[^\d,.]/g, "").replace(",", ".");
  if (!limpo) return "0";
  const n = Number(limpo);
  return Number.isFinite(n) ? n.toFixed(2) : limpo;
}

/** "8.00" → "8", "7.50" → "7,5": o desconto como ele aparece no campo. */
export function campoDoPct(pct: string | null | undefined): string {
  if (!pct) return "";
  const n = Number(pct);
  return n === 0 ? "" : String(n).replace(".", ",");
}

/** "8.00" → "8%", "7.50" → "7,5%": o percentual que a API manda, sem arredondar. */
export const pctTexto = (pct: string): string => `${Number(pct).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;

/** O resumo da proposta, linha por linha, como a API calculou (VEN-02, VEN-04, FIN-09). */
export function linhasDoResumo(c: Pick<CalculoDaVenda, "preco_tabela_centavos" | "desconto_pct" | "desconto_centavos" | "preco_final_centavos" | "forma" | "entrada_centavos" | "num_parcelas" | "parcela_centavos" | "ultima_parcela_centavos" | "comissao_centavos">): { rotulo: string; valor: string }[] {
  const linhas = [{ rotulo: "Preço de tabela", valor: dinheiro(c.preco_tabela_centavos) }];
  if (c.desconto_centavos > 0) linhas.push({ rotulo: `Desconto ${pctTexto(c.desconto_pct)}`, valor: `− ${dinheiro(c.desconto_centavos)}` });
  linhas.push({ rotulo: "Preço final", valor: dinheiro(c.preco_final_centavos) });
  if (c.forma === "entrada_parcelas") {
    if (c.entrada_centavos != null) linhas.push({ rotulo: "Entrada", valor: dinheiro(c.entrada_centavos) });
    if (c.num_parcelas && c.parcela_centavos != null) {
      const ultima = c.ultima_parcela_centavos != null && c.ultima_parcela_centavos !== c.parcela_centavos ? ` (última ${dinheiro(c.ultima_parcela_centavos)})` : "";
      linhas.push({ rotulo: "Saldo", valor: `${c.num_parcelas} × ${dinheiro(c.parcela_centavos)}${ultima}` });
    }
  }
  linhas.push({ rotulo: "Comissão", valor: dinheiro(c.comissao_centavos) });
  return linhas;
}

/** "VEN-0177 · Bruna": o código e o primeiro nome de quem vende. */
export const codigoEVendedor = (v: Pick<Venda, "codigo" | "vendedor" | "locacao">): string =>
  [v.locacao ? `${v.codigo} · ${v.locacao.codigo}` : v.codigo, v.vendedor && !v.locacao ? v.vendedor.nome.split(" ")[0] : null].filter(Boolean).join(" · ");

/** "Enviada em 07 out" / "Vence em 14 out" (VEN-13): só as datas da API; a frase com o e-mail entra com a 1c. */
export const dataDaProposta = (iso: string | null | undefined): string | null => (iso ? dataCurta(iso) : null);

/** Depois de qualquer ação na venda: a lista, o detalhe, as aprovações e os contadores do menu. */
export function atualizarVendas(cliente: QueryClient): Promise<unknown> {
  return Promise.all(["vendas", "venda", "aprovacoes", "contadores"].map((k) => cliente.invalidateQueries({ queryKey: [k] })));
}

/** Link do WhatsApp do aparelho (VEN-16): nada sai pelo sistema. Só para o interessado, que traz o celular. */
export const linkDoWhatsApp = (celular: string): string => `https://wa.me/55${celular.replace(/\D/g, "")}`;
