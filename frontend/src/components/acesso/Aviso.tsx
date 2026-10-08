import { CircleAlert, Info } from "lucide-react";
import type { ReactNode } from "react";
import { Icone } from "@/design-system";

/** Faixa de aviso (neutra) ou de erro (critical) dentro de um painel. Erro usa role=alert. */
export function Aviso({ tipo = "info", children }: { tipo?: "info" | "erro"; children: ReactNode }) {
  const erro = tipo === "erro";
  return (
    <div
      role={erro ? "alert" : "note"}
      className={`flex items-start gap-2 rounded-md p-4 text-caption ${erro ? "bg-critical-soft text-critical-ink" : "bg-surface-sunken text-ink-muted"}`}
    >
      <Icone de={erro ? CircleAlert : Info} />
      <span>{children}</span>
    </div>
  );
}
