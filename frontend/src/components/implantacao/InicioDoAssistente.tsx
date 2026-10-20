"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { implantacao } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { rotaDoPasso } from "@/lib/implantacao";
import { useSessao } from "@/lib/sessao";

/** Rota /implantacao: leva ao passo atual que a API mandou (`proximo`), ou ao primeiro quando tudo está feito. Só o administrador. */
export function InicioDoAssistente() {
  const { eu } = useSessao();
  const router = useRouter();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["implantacao"], queryFn: () => implantacao.obter(), enabled: podeVer });
  const destino = consulta.data ? (consulta.data.proximo ?? consulta.data.passos[0]?.passo ?? null) : null;

  useEffect(() => {
    if (destino) router.replace(rotaDoPasso(destino));
  }, [destino, router]);

  if (!podeVer)
    return (
      <p role="alert" className="m-4 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador faz a configuração inicial.
      </p>
    );
  if (consulta.isError)
    return (
      <p role="alert" className="m-4 rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  return (
    <p className="m-4 text-body text-ink-muted" aria-busy="true">
      Abrindo a configuração inicial…
    </p>
  );
}
