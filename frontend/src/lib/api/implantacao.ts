// Andamento do assistente de implantação na API real (docs/api/plataforma.md): só o administrador.
import { http } from "./http";
import type { AndamentoDoAssistente } from "./tipos-implantacao";

export const implantacaoApi = {
  obter(): Promise<AndamentoDoAssistente> {
    return http.get("/api/implantacao/");
  },
};
