"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { filiais, type MinhaFilial } from "@/lib/api";
import { definirFilial } from "@/lib/api/http";
import { dependeDaFilial, escolhaValida, guardarEscolha, lerEscolhaGuardada, nomeDaEscolha, TODAS } from "@/lib/filial";
import { useSessao } from "@/lib/sessao";

export type FilialEscolhida = {
  /** Id da filial, ou `"todas"`; é o que vai em `X-Filial`. `null` quando a pessoa não tem filial. */
  escolha: string | null;
  nome: string | null;
  /** "Todas as filiais" escolhida: telas de uma filial só (caixa) pedem para escolher uma. */
  todas: boolean;
  filiais: MinhaFilial[];
  podeEscolherTodas: boolean;
  trocar: (escolha: string) => void;
};

const Contexto = createContext<FilialEscolhida | null>(null);

/** Quem não está dentro do provider (testes de tela) fica sem escolha: as telas usam a primeira filial da sessão. */
export function useFilial(): FilialEscolhida | null {
  return useContext(Contexto);
}

/**
 * Filial do app: lê /filiais/minhas/, guarda a escolha por pessoa e a manda em `X-Filial` em toda requisição.
 * As telas só montam depois da lista, para a primeira consulta já sair com o cabeçalho certo.
 */
export function FilialProvider({ children }: { children: ReactNode }) {
  const { eu } = useSessao();
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: ["filiais-minhas"], queryFn: () => filiais.minhas(), staleTime: 5 * 60_000 });
  const [guardada, setGuardada] = useState<string | null>(() => lerEscolhaGuardada(eu.id));

  const minhas = consulta.data;
  const escolha = minhas ? escolhaValida(minhas, guardada) : null;
  // Antes das telas filhas montarem: a escolha já está no cliente HTTP quando a primeira consulta sai.
  definirFilial(escolha);

  const trocar = useCallback(
    (nova: string) => {
      if (!minhas) return;
      const valida = escolhaValida(minhas, nova);
      if (!valida || valida === escolha) return;
      guardarEscolha(eu.id, valida);
      definirFilial(valida);
      setGuardada(valida);
      // O que está na tela era de outra filial: refaz as consultas dela.
      void cliente.resetQueries({ predicate: (q) => dependeDaFilial(q.queryKey) });
    },
    [minhas, escolha, eu.id, cliente],
  );

  const valor = useMemo<FilialEscolhida | null>(
    () =>
      minhas
        ? { escolha, nome: nomeDaEscolha(minhas, escolha), todas: escolha === TODAS, filiais: minhas.resultados, podeEscolherTodas: minhas.pode_escolher_todas, trocar }
        : null,
    [minhas, escolha, trocar],
  );

  if (consulta.isError)
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <p role="alert" className="text-body text-ink-muted">
          Não foi possível carregar suas filiais. Atualize a página.
        </p>
      </main>
    );
  if (!valor)
    return (
      <main className="grid min-h-screen place-items-center p-6" aria-busy="true">
        <p className="text-body text-ink-muted">Carregando…</p>
      </main>
    );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}
