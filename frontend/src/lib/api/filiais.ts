// Filiais na API real (docs/api/filiais.md): só o seletor do topo do menu.
import { chamar } from "./http";
import type { MinhasFiliais } from "./tipos";

export const filiaisApi = {
  /** As filiais ativas da pessoa e se ela pode escolher "Todas as filiais" (USR-07). */
  minhas(): Promise<MinhasFiliais> {
    return chamar<MinhasFiliais>("GET", "/api/filiais/minhas/", { semFilial: true });
  },
};
