// Tipos de Administração › Assinatura, a partir do cliente gerado (docs/api/assinatura.md).
import type { components } from "./schema";

type S = components["schemas"];

export type Assinatura = S["Assinatura"];
export type UsoDoItemDaAssinatura = S["UsoDoItemNaAssinatura"];
export type FormaDePagamento = S["FormaDePagamento"];
export type FormaDaAssinatura = S["FormaAssinaturaEnum"];
export type DadosFiscais = S["DadosFiscais"];
export type EnderecoDaNota = S["EnderecoDaNota"];
export type OfertaDoPlano = S["Oferta"];
export type PlanoParaMudar = S["PlanoParaMudar"];
export type PlanosParaMudar = S["PlanosParaMudar"];
export type CicloDaAssinatura = S["CicloEnum"];
export type PedidoDeMudancaDePlano = S["PedidoDeMudanca"];
export type SimulacaoDeMudanca = S["Simulacao"];
export type ConfirmacaoDeMudanca = S["ConfirmarMudanca"];
export type RespostaDaForma = S["RespostaDaForma"];
export type ProximoPasso = S["ProximoPasso"];
export type FaturaDaAssinatura = S["FaturaDaLista"];
export type FaturaDetalhada = S["FaturaDetalhe"];
export type ListaDeFaturas = S["ListaDeFaturas"];
export type CobrancaDaFatura = S["CobrancaDaFatura"];
export type MeioDePagarFatura = S["MeioDePagarEnum"];
export type CorrecaoDeDadosFiscais = Partial<{ razao_social: string; endereco: EnderecoDaNota; email_cobranca: string }>;
