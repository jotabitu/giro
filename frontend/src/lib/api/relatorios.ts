// Painel na API real (docs/api/painel.md). O app `relatorios` do backend ainda não expõe rotas
// (ausentes do openapi.yaml): enquanto isso, as chamadas respondem 404 e as telas mostram o estado de erro.
import { http } from "./http";
import type { Contadores, Inicio, Periodo } from "./tipos-painel";

export const relatoriosApi = {
  contadores(): Promise<Contadores> {
    return http.get("/api/painel/contadores/");
  },

  inicio(periodo: Periodo = "7d"): Promise<Inicio> {
    return http.get("/api/painel/inicio/", { periodo });
  },
};
