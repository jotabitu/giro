// Fronteira da API para as telas: cada módulo chama a API real (docs/api/openapi.yaml) pelo cliente de ./http.
// Nos testes, o alias de vitest.config.ts troca este módulo pelas fixtures de src/testes/.
import { clientesApi } from "./clientes";
import { contasApi } from "./contas";
import { locacoesApi } from "./locacoes";
import { marcaApi } from "./marca";
import { relatoriosApi } from "./relatorios";
import { veiculosApi } from "./veiculos";
import { vistoriasApi } from "./vistorias";

export const contas = contasApi;
export const relatorios = relatoriosApi;
export const veiculos = veiculosApi;
export const clientes = clientesApi;
export const locacoes = locacoesApi;
export const marca = marcaApi;
export const vistorias = vistoriasApi;
export * from "./tipos";
export * from "./tipos-frota";
export * from "./tipos-clientes";
export * from "./tipos-painel";
export * from "./tipos-locacoes";
export * from "./tipos-vistorias";
