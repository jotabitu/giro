// DADOS FALSOS da assinatura nos testes (docs/api/plataforma.md). Só api-falsa.ts importa este arquivo.
// Seed: Moto Rápida em teste (07 a 21 out, 14 dias), plano Profissional R$ 449,00; uso 86/150, 1/3 e 5/10, sem aviso (PLT-03).
import type { Assinatura } from "@/lib/api/tipos-assinatura";
import { pausa } from "./falso";

const SEED: Assinatura = {
  plano: { nome: "Profissional", preco_contratado_centavos: 44900, ciclo: "mensal" },
  status: "em_teste",
  teste: { fim: "2026-10-21", dias_restantes: 14 },
  faixa_aviso: null,
  uso: {
    veiculos: { usado: 86, limite: 150, aviso: false, bloqueado: false },
    filiais: { usado: 1, limite: 3, aviso: false, bloqueado: false },
    usuarios: { usado: 5, limite: 10, aviso: false, bloqueado: false },
  },
  somente_leitura: false,
};

let atual: Assinatura = SEED;
/** Troca partes da assinatura para o teste de um estado (inadimplente, suspensa, uso perto do limite). */
export function definirAssinaturaFalsa(mudanca: Partial<Assinatura> | null) {
  atual = mudanca ? { ...SEED, ...mudanca } : SEED;
}

export const assinaturaFalso = {
  async obter(): Promise<Assinatura> {
    await pausa(40);
    return structuredClone(atual);
  },
};
