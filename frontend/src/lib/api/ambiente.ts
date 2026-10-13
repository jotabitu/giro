// Ambiente (docs/api/README.md, ADR 0021): o "hoje" do relógio do domínio e se a data é simulada. Pública.
import { chamar } from "./http";
import type { Ambiente, EscopoDoAmbiente } from "./tipos";

const CAMINHO: Record<EscopoDoAmbiente, string> = { empresa: "/api/ambiente/", plataforma: "/api/plataforma/ambiente/" };

export const ambienteApi = {
  /** `null` quando a rota não existe (backend sem a T-142), falha ou vem fora do contrato: a tela segue sem faixa e sem erro. */
  async obter(escopo: EscopoDoAmbiente): Promise<Ambiente | null> {
    try {
      const a = await chamar<Partial<Ambiente>>("GET", CAMINHO[escopo], { semSessao: true });
      return typeof a?.hoje === "string" && /^\d{4}-\d{2}-\d{2}$/.test(a.hoje) && typeof a.data_simulada === "boolean" ? { hoje: a.hoje, data_simulada: a.data_simulada } : null;
    } catch {
      return null;
    }
  },
};
