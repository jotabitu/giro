import type { AndamentoDoAssistente, PassoDoAssistente } from "@/lib/api";

// Rotas do assistente (docs/telas/README.md, telas 5 a 12). A ordem, os números e os rótulos vêm de GET /api/implantacao/;
// aqui só fica qual passo já tem tela. Todos os passos da lista têm tela (os recebimentos entraram na T-397).
const COM_TELA: string[] = ["marca", "filial", "ramo", "precos", "contrato", "recebimentos", "importar", "equipe"];

export const rotaDoPasso = (passo: string): string => `/implantacao/${passo}`;

export const passoTemTela = (passo: string): boolean => COM_TELA.includes(passo);

export function passoDe(andamento: AndamentoDoAssistente, chave: string): PassoDoAssistente | null {
  return andamento.passos.find((p) => p.passo === chave) ?? null;
}

/** Passo anterior e seguinte na ordem que a API mandou (no Essencial `recebimentos` nem vem na lista). */
export function vizinhos(andamento: AndamentoDoAssistente, chave: string): { anterior: PassoDoAssistente | null; seguinte: PassoDoAssistente | null } {
  const i = andamento.passos.findIndex((p) => p.passo === chave);
  if (i < 0) return { anterior: null, seguinte: null };
  return { anterior: andamento.passos[i - 1] ?? null, seguinte: andamento.passos[i + 1] ?? null };
}

/** Destino de "Continuar" e "Pular": o próximo passo, ou o início quando o último foi o da lista. */
export const destinoDepoisDe = (andamento: AndamentoDoAssistente, chave: string): string => {
  const { seguinte } = vizinhos(andamento, chave);
  return seguinte ? rotaDoPasso(seguinte.passo) : "/inicio";
};

export const destinoAntesDe = (andamento: AndamentoDoAssistente, chave: string): string => {
  const { anterior } = vizinhos(andamento, chave);
  return anterior ? rotaDoPasso(anterior.passo) : "/inicio";
};
