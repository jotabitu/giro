import type { TomStatus } from "@/design-system";
import type { TomApi } from "@/lib/api";

const TONS: Record<TomApi, TomStatus> = {
  sucesso: "sucesso",
  info: "info",
  alerta: "alerta",
  atencao: "atencao",
  perigo: "critico",
  neutro: "neutro",
  solido: "solido",
};

/** O tom vem da API (`situacao.tom`); aqui só vira o tom do componente. */
export function tomDoStatus(tom: TomApi): TomStatus {
  return TONS[tom] ?? "neutro";
}
