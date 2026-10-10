"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Panel, StatusBadge } from "@/design-system";
import { vistorias } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, placa } from "@/lib/formatos";

/** Avarias ainda não reparadas (GET /api/vistorias/avarias/). Uma avaria fecha quando a OS ligada a ela é concluída. Sem valores. */
export function AvariasAbertas() {
  const consulta = useQuery({ queryKey: ["avarias-abertas"], queryFn: () => vistorias.avarias() });
  const lista = consulta.data?.resultados ?? [];
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-title md:text-display">Avarias abertas</h1>
        {consulta.data && <p className="mt-1 text-body text-ink-muted">{lista.length === 1 ? "1 avaria ainda não reparada" : `${lista.length} avarias ainda não reparadas`}</p>}
      </header>
      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando as avarias…
        </p>
      )}
      {consulta.data && lista.length === 0 && (
        <Panel>
          <p className="py-6 text-center text-body text-ink-muted">Nenhuma avaria aberta.</p>
        </Panel>
      )}
      <ul className="grid gap-4 md:grid-cols-2">
        {lista.map((a) => (
          <li key={a.id} className="flex gap-4 rounded-lg bg-surface p-4">
            {a.foto && (
              // eslint-disable-next-line @next/next/no-img-element -- URL assinada de 15 minutos da API, sem otimização do Next
              <img src={a.foto.url} alt={`Foto da avaria: ${a.descricao}`} className="h-[84px] w-[110px] shrink-0 rounded-md object-cover" />
            )}
            <div className="min-w-0 flex-1">
              <div className="text-body font-medium">{a.descricao}</div>
              <div className="text-caption text-ink-muted">
                <span className="wl-mono">{placa(a.veiculo.placa)}</span> · {a.veiculo.modelo}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-caption text-ink-muted">
                <Link href={`/locacoes/${a.locacao.id}`} className="wl-mono text-ink-muted">
                  {a.locacao.codigo}
                </Link>
                {a.registrada_em && <span>registrada em {dataCurta(a.registrada_em)}</span>}
                {a.vai_para_oficina && (
                  <StatusBadge tom="alerta" compacto>
                    Vai para a oficina
                  </StatusBadge>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
