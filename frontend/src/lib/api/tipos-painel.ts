// Tipos do painel, a partir do cliente gerado do OpenAPI (src/lib/api/schema.d.ts, `npm run api:gerar`).
// O gerador deixa `valor` como `unknown` e os tons como `string`; aqui eles ganham os valores fechados do contrato (docs/api/painel.md).
import type { components } from "./schema";
import type { VarianteInicio } from "./tipos";
import type { TomApi } from "./tipos-frota";
import type { AgendaDoDia, ItemDaAgenda } from "./tipos-vistorias";

type S = components["schemas"];

/** Todo número de KPI vem tipado: dinheiro em centavos, percentual como texto com 2 casas. */
export type ValorTipado = { tipo: "numero"; valor: number } | { tipo: "centavos"; valor: number } | { tipo: "pct"; valor: string };

export type Situacao = { rotulo: string; tom: TomApi };

/** `valor: null` = módulo que ainda não existe (USR-08): o cartão não aparece. */
export type Kpi = Omit<S["Kpi"], "valor"> & { valor: ValorTipado | null };

export type Contadores = Omit<S["Contadores"], "contadores"> & { contadores: Record<string, number | null> };

export type DestinoPendencia = S["Destino"];

export type PendenciaInicio = S["ItemDePendencia"];

type ComSituacao<T> = Omit<T, "situacao"> & { situacao: Situacao };

export type InicioGeral = Omit<S["InicioGeral"], "kpis" | "devolucoes_semana"> & {
  kpis: Kpi[];
  devolucoes_semana: Omit<S["DevolucoesDaSemana"], "linhas"> & { linhas: ComSituacao<S["LinhaDeDevolucao"]>[] };
};

export type PassoImplantacao = S["PassoDoInicio"];

export type InicioImplantacao = S["InicioImplantacao"];

export type InicioGerente = Omit<S["InicioGerente"], "kpis" | "aprovacoes"> & {
  kpis: Kpi[];
  aprovacoes: Omit<S["AprovacoesDoInicio"], "itens"> & { itens: (Omit<S["ItemDeAprovacao"], "acoes"> & { acoes: ("recusar" | "aprovar")[] })[] };
};

export type InicioVendedor = Omit<S["InicioVendedor"], "kpis" | "precisam_acao"> & {
  kpis: Kpi[];
  precisam_acao: ComSituacao<S["LocacaoQuePrecisaDeAcao"]>[];
};

export type ItemAgenda = ItemDaAgenda;

/** Corpo de GET /api/vistorias/agenda/ (docs/api/vistorias.md). */
export type Agenda = AgendaDoDia;

export type InicioVistoriador = Omit<S["InicioVistoriador"], "agenda"> & { agenda: Agenda };

export type InicioFinanceiro = Omit<S["InicioFinanceiro"], "kpis"> & { kpis: Kpi[] };


export type Periodo = "hoje" | "7d" | "30d";

export type Inicio = (InicioGeral | InicioImplantacao | InicioGerente | InicioVendedor | InicioVistoriador | InicioFinanceiro);

/** O que a API devolve de cada variante, sem `saudacao` e `atualizado_em` (as respostas falsas juntam os dois). */
export type CorpoDoInicio<T> = Omit<T, "saudacao" | "atualizado_em">;

export type InicioDe<V extends VarianteInicio> = Extract<Inicio, { variante: V }>;
