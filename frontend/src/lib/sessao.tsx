"use client";

import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { contas, ErroApi, type Eu } from "@/lib/api";
import { accessAtual, aoPerderSessao } from "@/lib/api/http";
import { useEnderecoSemEmpresa } from "@/lib/endereco";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";

const CHAVE = ["eu"] as const;
const VALIDADE = 5 * 60_000;

/** Renova só quando não há access na memória (recarga da página); com access vencido, o cliente HTTP renova no 401. */
async function buscarEu(): Promise<Eu> {
  if (!accessAtual()) await contas.renovar();
  return contas.eu();
}

/**
 * O login grava o usuário com `setQueryData` antes de a casca montar a consulta. Sem `queryFn` registrada,
 * qualquer nova leitura dessa chave falhava com "No queryFn was passed" e a casca mostrava "Não foi possível carregar sua conta".
 */
export function registrarConsulta(cliente: QueryClient) {
  cliente.setQueryDefaults(CHAVE, { queryFn: buscarEu, staleTime: VALIDADE });
}

type Sessao = { eu: Eu; sair: () => Promise<void> };
const Contexto = createContext<Sessao | null>(null);

/** Quem está logado: renova o access (cookie de refresh) e lê /auth/eu/. Sem sessão, vai para o login. */
export function SessaoProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const cliente = useQueryClient();
  useMarcaDaEmpresa();

  const semEmpresa = useEnderecoSemEmpresa();
  registrarConsulta(cliente);
  const consulta = useQuery({ queryKey: CHAVE, queryFn: buscarEu, staleTime: VALIDADE, enabled: !semEmpresa });

  const sair = useCallback(async () => {
    await contas.sair();
    // Consultas da área da empresa ainda em voo ou esperando nova tentativa não podem sobreviver ao login seguinte.
    await cliente.cancelQueries();
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

  const semSessao = semEmpresa || consulta.error instanceof ErroApi && consulta.error.status === 401;
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
  return (usuario: Eu) => {
    registrarConsulta(cliente);
    cliente.setQueryData(CHAVE, usuario);
  };
}
