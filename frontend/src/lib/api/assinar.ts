// Assinatura pública do contrato (docs/api/contratos.md, S-15): sem login e sem filial; o token vai no corpo, nunca na URL.
import { http } from "./http";
import type { AssinaturaFeita, ConsultaDaAssinatura } from "./tipos-assinar";

export const assinarApi = {
  consultar(corpo: { token: string }): Promise<ConsultaDaAssinatura> {
    return http.post("/api/publico/assinaturas/consultar/", corpo, { semSessao: true });
  },

  assinar(corpo: { token: string; aceite: boolean; nome_completo: string }): Promise<AssinaturaFeita> {
    return http.post("/api/publico/assinaturas/assinar/", corpo, { semSessao: true });
  },
};
