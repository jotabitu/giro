// Vendas na API real (docs/api/vendas.md). Só abre com o recurso `vendas_comissoes` (PLT-12); o vistoriador recebe 403.
import { http } from "./http";
import type { FiltroDeVendas, ListaDeVendas } from "./tipos-vendas";

export const vendasApi = {
  listar(f: FiltroDeVendas = {}): Promise<ListaDeVendas> {
    return http.get("/api/vendas/", { origem: f.origem, transferencia_pendente: f.transferencia_pendente ? "true" : undefined, cursor: f.cursor });
  },
};
