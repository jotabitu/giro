// Painel na API real (docs/api/painel.md): início por variante e contadores do menu.
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
