// Assinatura e uso do plano da empresa na API real (docs/api/plataforma.md). Só leitura na fase 1.
import { http } from "./http";
import type { Assinatura } from "./tipos-assinatura";

export const assinaturaApi = {
  obter(): Promise<Assinatura> {
    return http.get("/api/assinatura/");
  },
};
