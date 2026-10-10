"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { contas, ErroApi, type Eu } from "@/lib/api";
import { aoPerderSessao } from "@/lib/api/http";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";

const CHAVE = ["eu"] as const;

type Sessao = { eu: Eu; sair: () => Promise<void> };
const Contexto = createContext<Sessao | null>(null);

/** Quem está logado: renova o access (cookie de refresh) e lê /auth/eu/. Sem sessão, vai para o login. */
export function SessaoProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const cliente = useQueryClient();
  useMarcaDaEmpresa();

  const consulta = useQuery({
    queryKey: CHAVE,
    queryFn: async () => {
      await contas.renovar();
      return contas.eu();
    },
    staleTime: 5 * 60_000,
  });

  const sair = useCallback(async () => {
    await contas.sair();
    cliente.clear();
    router.replace("/entrar");
  }, [cliente, router]);

  // Sessão que acaba no meio do uso (renovação recusada, sessão encerrada em outro lugar): volta ao login.
  useEffect(
    () =>
      aoPerderSessao(() => {
        cliente.clear();
        router.replace("/entrar");
      }),
    [cliente, router],
  );

  const semSessao = consulta.error instanceof ErroApi && consulta.error.status === 401;
  useEffect(() => {
    if (semSessao) router.replace("/entrar");
  }, [semSessao, router]);

  const valor = useMemo(() => (consulta.data ? { eu: consulta.data, sair } : null), [consulta.data, sair]);

  if (consulta.isError && !semSessao) {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <p role="alert" className="text-body text-ink-muted">
          Não foi possível carregar sua conta. Atualize a página.
        </p>
      </main>
    );
  }
  if (!valor) {
    return (
      <main className="grid min-h-screen place-items-center p-6" aria-busy="true">
        <p className="text-body text-ink-muted">Carregando…</p>
      </main>
    );
  }
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao(): Sessao {
  const v = useContext(Contexto);
  if (!v) throw new Error("useSessao fora do SessaoProvider");
  return v;
}

/** Grava o usuário que o login devolveu, para a casca não pedir de novo. */
export function useGuardarSessao() {
  const cliente = useQueryClient();
  return (usuario: Eu) => cliente.setQueryData(CHAVE, usuario);
}
