// Preços por veículo (VEI-12 a VEI-17, ADR 0041, docs/api/veiculos.md "Preços do veículo"). Tipos do cliente gerado do OpenAPI.
import type { components } from "./schema";

type S = components["schemas"];

export type PrecosDoVeiculo = S["PrecosDoVeiculo"];
export type PrecosEntrada = S["PrecosEntrada"];
export type PlanoDoVeiculo = S["PlanoDoVeiculo"];
export type PlanoEntrada = S["PlanoEntrada"];
export type TipoDePlano = S["TipoPlanoVeiculoEnum"];
export type PeriodoDoPlano = S["PeriodoPlanoEnum"];
export type ComoPaga = S["ComoPagaEnum"];
export type FormaAceita = S["FormaAceitaEnum"];
export type PlanoCompraDoVeiculo = S["PlanoCompraDoVeiculo"];
export type PlanoCompraEntrada = S["PlanoCompraDoVeiculoEntrada"];
// T-495: a compra do veículo e a locação têm a mesma periodicidade, um enum só no OpenAPI.
export type PeriodicidadeDaCompra = S["PeriodicidadeEnum"];
export type ModoDaParcela = S["ModoParcelaEnum"];
export type ResultadoDaCompra = S["ResultadoCompra"];
export type RegrasDoVeiculo = S["RegrasDoVeiculo"];
export type RegrasEntrada = S["RegrasEntrada"];
export type CustosDoVeiculo = S["CustosDoVeiculo"];
export type CustosEntrada = S["CustosEntrada"];
export type AgendadoDoPlano = S["Agendado"];
