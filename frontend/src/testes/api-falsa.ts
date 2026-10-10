// Faz o papel de `@/lib/api` nos testes (alias em vitest.config.ts): a mesma fronteira, com as fixtures de ./falsos.
// Fora dos testes ninguém importa esta pasta (regra no-restricted-imports do ESLint).
import { clientesFalso } from "./falsos/falso-clientes";
import { veiculosFalso } from "./falsos/falso-frota";
import { contasFalso, marcaFalsa } from "./falsos/falso";
import { relatoriosFalso } from "./falsos/falso-painel";
import { locacoesFalso } from "./falsos/falso-locacoes";
import { vistoriasFalso } from "./falsos/falso-vistorias";

export const contas = contasFalso;
export const marcaDaEmpresa = marcaFalsa;
export const relatorios = relatoriosFalso;
export const veiculos = veiculosFalso;
export const clientes = clientesFalso;
export const locacoes = locacoesFalso;
export const vistorias = vistoriasFalso;
export * from "@/lib/api/tipos";
export * from "@/lib/api/tipos-frota";
export * from "@/lib/api/tipos-clientes";
export * from "@/lib/api/tipos-painel";
export * from "@/lib/api/tipos-locacoes";
export * from "@/lib/api/tipos-vistorias";
