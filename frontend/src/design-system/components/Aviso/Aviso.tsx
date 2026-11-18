import type { ReactNode } from "react";

export type TomAviso = "atencao" | "info" | "critico";

const CLASSE: Record<TomAviso, string> = {
  atencao: "wl-note",
  info: "wl-note wl-note--info",
  critico: "wl-note wl-note--critical",
};

/** Nota curta dentro de um painel ou ao lado de um campo. O texto carrega o significado; o tom só reforça. */
export function Aviso({ tom = "atencao", children }: { tom?: TomAviso; children: ReactNode }) {
  return (
    <div className={CLASSE[tom]} role={tom === "critico" ? "alert" : "note"}>
      {children}
    </div>
  );
}
