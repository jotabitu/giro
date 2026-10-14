// Textos de Auditoria e Exportar dados. Resumo, detalhe e estado vêm prontos da API (docs/api/auditoria.md); aqui só rótulos, tons e formatação.
import type { TomStatus } from "@/design-system";
import type { CategoriaDeAuditoria, EventoDeAuditoria, FiltroAuditoria, PeriodoDaAuditoria, PessoaDaAuditoria, StatusDaExportacao } from "@/lib/api";

export const CATEGORIAS_DA_AUDITORIA: { valor: CategoriaDeAuditoria; rotulo: string }[] = [
  { valor: "financeiro", rotulo: "Financeiro" },
  { valor: "operacao", rotulo: "Operação" },
  { valor: "configuracoes", rotulo: "Configurações" },
  { valor: "seguranca", rotulo: "Segurança" },
  { valor: "suporte", rotulo: "Suporte" },
];

export const PERIODOS_DA_AUDITORIA: { valor: PeriodoDaAuditoria; rotulo: string }[] = [
  { valor: "7d", rotulo: "Últimos 7 dias" },
  { valor: "30d", rotulo: "Últimos 30 dias" },
  { valor: "90d", rotulo: "Últimos 90 dias" },
];

/** Regras de bloqueio de login: o evento aparece em crítico (`USR-06`, `PLT-08`). */
const REGRAS_DE_BLOQUEIO = new Set(["USR-06", "PLT-08"]);

/**
 * Tom do selo do resumo: suporte em alerta (AUD-03, a linha também ganha destaque), bloqueio de login em crítico,
 * mudanças de configuração e de segurança em info. O resto é texto simples (`null`).
 */
export function tomDoEvento(e: Pick<EventoDeAuditoria, "categoria" | "suporte" | "regra">): TomStatus | null {
  if (e.suporte || e.categoria === "suporte") return "alerta";
  if (e.regra && REGRAS_DE_BLOQUEIO.has(e.regra)) return "critico";
  if (e.categoria === "configuracoes" || e.categoria === "seguranca") return "info";
  return null;
}

/** O filtro "Pessoa" vai na URL como `usuario:4`, `sistema` ou `suporte`. */
export const valorDaPessoa = (p: Pick<PessoaDaAuditoria, "tipo" | "id">): string => (p.tipo === "usuario" ? `usuario:${p.id}` : p.tipo);

export function filtroDaPessoa(valor: string | null): Pick<FiltroAuditoria, "ator" | "ator_tipo"> {
  if (valor === "sistema" || valor === "suporte") return { ator_tipo: valor };
  const m = /^usuario:(\d+)$/.exec(valor ?? "");
  return m ? { ator: Number(m[1]) } : {};
}

export const ROTULO_DA_EXPORTACAO: Record<StatusDaExportacao, { rotulo: string; tom: TomStatus }> = {
  na_fila: { rotulo: "Na fila", tom: "info" },
  pronta: { rotulo: "Pronto", tom: "sucesso" },
  expirada: { rotulo: "Expirado", tom: "neutro" },
  falhou: { rotulo: "Falhou", tom: "critico" },
};

/** "CSV · 180 KB" a partir do formato e do tamanho que a API mandou. */
export function arquivoDaExportacao(formato: string, bytes: number | null): string {
  const nome = formato === "csv" ? "CSV" : formato === "zip" ? "ZIP" : "Planilha";
  if (bytes === null) return nome;
  const unidade = bytes >= 1e9 ? [1e9, "GB"] : bytes >= 1e6 ? [1e6, "MB"] : [1e3, "KB"];
  return `${nome} · ${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(bytes / (unidade[0] as number))} ${unidade[1]}`;
}

/** Período "Este ano": de 1º de janeiro até o dia dado (AAAA-MM-DD). */
export const esteAno = (hoje: string): { de: string; ate: string } => ({ de: `${hoje.slice(0, 4)}-01-01`, ate: hoje });
