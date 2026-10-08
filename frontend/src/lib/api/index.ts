// Fronteira da API para as telas. Hoje aponta para dados falsos; trocar aqui pela API real.
// Só este arquivo importa os módulos falso*.ts.
import { clientesFalso } from "./falso-clientes";
import { veiculosFalso } from "./falso-frota";
import { contasFalso, marcaFalsa } from "./falso";
import { relatoriosFalso } from "./falso-painel";

export const contas = contasFalso;
export const marcaDaEmpresa = marcaFalsa;
export const relatorios = relatoriosFalso;
export const veiculos = veiculosFalso;
export const clientes = clientesFalso;
export * from "./tipos";
export * from "./tipos-frota";
export * from "./tipos-clientes";
export * from "./tipos-painel";
