import type { Ambiente, EscopoDoAmbiente } from "@/lib/api/tipos";

/** Ambiente das fixtures: data real, sem faixa. Os testes que precisam da data simulada trocam `resposta`. */
export const ambienteFalso = {
  resposta: null as Ambiente | null,
  async obter(escopo: EscopoDoAmbiente): Promise<Ambiente | null> {
    void escopo;
    return this.resposta;
  },
};
