// O ramo da empresa na API real (docs/api/empresas.md): só o administrador.
import { http } from "./http";
import type { CorpoDoRamo, Ramo } from "./tipos-configuracoes";

export const ramoApi = {
  obter(): Promise<Ramo> {
    return http.get("/api/ramo/");
  },

  /** 422 `PLT-12` (`detalhes.motivo` "plano" ou "abertos") quando a API recusa; a mensagem já vem pronta. */
  trocar(corpo: CorpoDoRamo): Promise<Ramo> {
    return http.put("/api/ramo/", corpo);
  },
};
