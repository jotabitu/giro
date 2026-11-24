// Tipos de vendas, a partir do cliente gerado do OpenAPI (docs/api/vendas.md): a venda da quitação (VEN-11) e o fluxo de
// balcão da fase 1a da T-502 (estados, simular, proposta e aprovação do desconto).
import type { components } from "./schema";

type S = components["schemas"];

export type Venda = S["Venda"];
export type VendaDetalhe = S["VendaDetalhe"];
export type ListaDeVendas = S["ListaDeVendas"];
export type OrigemDaVenda = S["OrigemVendaEnum"];
export type StatusDaVenda = S["StatusVendaEnum"];
export type AcoesDaVenda = S["AcoesDaVenda"];
export type CalculoDaVenda = S["CalculoDaVenda"];
export type AprovacaoDaVenda = S["AprovacaoDaVenda"];
export type SimulacaoDaVenda = S["SimulacaoDaVenda"];
export type InteressadoDaVenda = S["InteressadoDaVenda"];
export type VendaEnviada = S["VendaEnviada"];
/** A forma que a tela oferece: o financiamento fica fora da primeira entrega (VEN-03, VEN-18). */
export type FormaDaVenda = "a_vista" | "entrada_parcelas";
export type AcaoDaNovaVenda = S["AcaoVendaEnum"];
/** `abertas` = interessado, proposta, negociação e aguardando aprovação (docs/api/vendas.md). */
export type AbaDeVendas = "abertas" | "minhas" | "aguardando" | "vendidas";

export type FiltroDeVendas = {
  origem?: OrigemDaVenda;
  transferencia_pendente?: boolean;
  aba?: AbaDeVendas;
  status?: StatusDaVenda;
  /** AAAA-MM: nas vendidas, o mês da venda; nas outras, o da criação. */
  mes?: string;
  veiculo?: number;
  cursor?: string;
};

/** O que a tela manda para simular, criar e editar. A conta volta pronta da API. */
export type PropostaDaVenda = {
  forma?: FormaDaVenda | "";
  desconto_pct?: string;
  entrada_centavos?: number | null;
  num_parcelas?: number | null;
};

export type NovaVenda = PropostaDaVenda & {
  veiculo_id: number;
  cliente_id?: number | null;
  interessado?: InteressadoDaVenda | null;
  acao: AcaoDaNovaVenda;
  motivo?: string;
};

export type EdicaoDaVenda = PropostaDaVenda & { cliente_id?: number | null; interessado?: InteressadoDaVenda | null };
