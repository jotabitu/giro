// Seletor de filial falso (docs/api/filiais.md): administrador e financeiro veem todas e "Todas as filiais";
// gerente, vendedor e vistoriador, só as suas. Quem responde é o perfil de quem está logado.
import type { MinhasFiliais } from "@/lib/api/tipos";
import { contasFalso, pausa } from "./falso";

const CENTRO = { id: 1, nome: "Filial Centro", nome_curto: "Filial Centro", matriz: true, cidade: "Fortaleza", uf: "CE" };
const ALDEOTA = { id: 2, nome: "Filial Aldeota", nome_curto: "Filial Aldeota", matriz: false, cidade: "Fortaleza", uf: "CE" };

export const filiaisFalso = {
  async minhas(): Promise<MinhasFiliais> {
    await pausa(0);
    const eu = await contasFalso.eu();
    const todas = eu.perfil === "administrador" || eu.perfil === "financeiro";
    const ids = new Set(eu.filiais.map((f) => f.id));
    return { pode_escolher_todas: todas, resultados: [CENTRO, ALDEOTA].filter((f) => ids.has(f.id)) };
  },
};
