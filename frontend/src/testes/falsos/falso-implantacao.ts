// DADOS FALSOS de docs/api/plataforma.md ("GET /api/implantacao/"): Profissional com 5 dos 8 passos, próximo "contrato".
import type { AndamentoDoAssistente } from "@/lib/api/tipos-implantacao";
import { pausa } from "./falso";

const ROTULOS: [string, string][] = [
  ["marca", "Empresa e marca"],
  ["filial", "Primeira filial"],
  ["ramo", "O que a empresa faz"],
  ["precos", "Tabela de preços"],
  ["contrato", "Modelo de contrato"],
  ["recebimentos", "Recebimentos"],
  ["importar", "Importar dados"],
  ["equipe", "Convidar equipe"],
];

/** Monta o andamento como a API: `feitos` são as chaves marcadas, `sem` tira passos do plano (Essencial sem `recebimentos`). */
export function andamentoFalso(feitos: string[], sem: string[] = []): AndamentoDoAssistente {
  const lista = ROTULOS.filter(([c]) => !sem.includes(c));
  const passos = lista.map(([passo, rotulo], i) => ({ passo, numero: i + 1, rotulo, feito: feitos.includes(passo), feito_em: feitos.includes(passo) ? "2026-10-07" : null }));
  return { concluida: false, total: passos.length, feitos: passos.filter((p) => p.feito).length, proximo: passos.find((p) => !p.feito)?.passo ?? null, passos };
}

export const ANDAMENTO_PROFISSIONAL = andamentoFalso(["marca", "filial", "ramo", "precos", "equipe"]);

export const implantacaoFalso = {
  async obter(): Promise<AndamentoDoAssistente> {
    await pausa();
    return ANDAMENTO_PROFISSIONAL;
  },
};
