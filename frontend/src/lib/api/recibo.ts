// Recibo público da devolução (docs/api/vistorias.md, DEV-02, S-15): sem login e sem filial; o token vai no corpo, nunca na URL.
import { http } from "./http";
import type { ConsultaDoRecibo } from "./tipos-recibo";

export const reciboApi = {
  consultar(corpo: { token: string }): Promise<ConsultaDoRecibo> {
    return http.post("/api/publico/recibos/consultar/", corpo, { semSessao: true });
  },
};
