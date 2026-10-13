// Faz o papel de `@/lib/api` nos testes (alias em vitest.config.ts): a mesma fronteira, com as fixtures de ./falsos.
// Fora dos testes ninguém importa esta pasta (regra no-restricted-imports do ESLint).
import { aprovacoesFalso } from "./falsos/falso-financeiro";
import { clientesFalso } from "./falsos/falso-clientes";
import { veiculosFalso } from "./falsos/falso-frota";
import { contasFalso, marcaFalsa } from "./falsos/falso";
import { ambienteFalso } from "./falsos/falso-ambiente";
import { relatoriosFalso } from "./falsos/falso-painel";
import { filiaisFalso } from "./falsos/falso-filiais";
import { financeiroFalso } from "./falsos/falso-financeiro";
import { locacoesFalso } from "./falsos/falso-locacoes";
import { vistoriasFalso } from "./falsos/falso-vistorias";

export const contas = contasFalso;
export const marca = marcaFalsa;
export const filiais = filiaisFalso;
export const ambiente = ambienteFalso;
export const relatorios = relatoriosFalso;
export const veiculos = veiculosFalso;
export const clientes = clientesFalso;
export const locacoes = locacoesFalso;
export const vistorias = vistoriasFalso;
export const financeiro = financeiroFalso;
export const aprovacoes = aprovacoesFalso;
export * from "@/lib/api/tipos";
export * from "@/lib/api/tipos-frota";
export * from "@/lib/api/tipos-clientes";
export * from "@/lib/api/tipos-painel";
export * from "@/lib/api/tipos-locacoes";
export * from "@/lib/api/tipos-vistorias";
export * from "@/lib/api/tipos-financeiro";
