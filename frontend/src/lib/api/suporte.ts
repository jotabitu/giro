// Controle do suporte na API real (docs/api/contas.md, "Controle do administrador", PLT-07): só o administrador.
import { http } from "./http";
import type { AcessoDoSuporte, BloqueioDoSuporte, ControleDoSuporte, SituacaoDoSuporte } from "./tipos-suporte";

export const suporteApi = {
  /** Acessos dos últimos 90 dias, com contagens e rótulos. As contagens não dependem do filtro. */
  listar(situacao: SituacaoDoSuporte = "todos"): Promise<ControleDoSuporte> {
    return http.get("/api/suporte/", { situacao });
  },

  bloquear(motivo?: string): Promise<BloqueioDoSuporte> {
    return http.post("/api/suporte/bloquear/", motivo ? { motivo } : {});
  },

  liberar(motivo?: string): Promise<BloqueioDoSuporte> {
    return http.post("/api/suporte/liberar/", motivo ? { motivo } : {});
  },

  revogar(id: number): Promise<AcessoDoSuporte> {
    return http.post(`/api/suporte/acessos/${id}/revogar/`, {});
  },
};
