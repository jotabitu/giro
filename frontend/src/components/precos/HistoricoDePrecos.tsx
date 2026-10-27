"use client";

import { useQuery } from "@tanstack/react-query";
import { Button, Dialogo } from "@/design-system";
import { precos as api } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, dinheiro } from "@/lib/formatos";

/** Todas as mudanças de preço da empresa (`GET /api/precos/historico/`, LOC-15). */
export function HistoricoDePrecos({ aoFechar }: { aoFechar: () => void }) {
  const consulta = useQuery({ queryKey: ["precos", "historico"], queryFn: () => api.historico() });
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo="Histórico de preços"
      descricao="Cada mudança de preço, da mais recente para a mais antiga."
      acoes={<Button variante="solido" onClick={aoFechar}>Fechar</Button>}
    >
      {consulta.isPending && (
        <p className="m-0 text-body text-ink-muted" aria-busy="true">
          Carregando…
        </p>
      )}
      {consulta.isError && (
        <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isSuccess && consulta.data.length === 0 && <p className="m-0 text-body text-ink-muted">Nenhuma mudança de preço ainda.</p>}
      {consulta.isSuccess && consulta.data.length > 0 && (
        <ol className="m-0 flex list-none flex-col p-0" aria-label="Mudanças de preço">
          {consulta.data.map((m, i) => (
            <li key={`${m.categoria.id}-${m.vigente_desde}-${m.campo}-${i}`} className="flex flex-col gap-0.5 border-b border-line py-3 last:border-b-0">
              <div className="flex flex-wrap justify-between gap-x-3">
                <span className="font-medium">
                  {m.categoria.nome} · {m.campo}
                </span>
                <span className="wl-mono">
                  {m.antes_centavos === null ? "—" : dinheiro(m.antes_centavos)} → {dinheiro(m.depois_centavos)}
                </span>
              </div>
              <span className="text-caption text-ink-muted">
                A partir de {dataCurta(m.vigente_desde)} · {m.alterado_por ?? "Sistema"}
              </span>
            </li>
          ))}
        </ol>
      )}
    </Dialogo>
  );
}
