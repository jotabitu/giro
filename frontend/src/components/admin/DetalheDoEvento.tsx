"use client";

import { useQuery } from "@tanstack/react-query";
import { auditoria } from "@/lib/api";
import { tomDoEvento } from "@/lib/auditoria";
import { mensagemDoErro } from "@/lib/erros";
import { dataHoraCompleta } from "@/lib/formatos";
import { StatusBadge } from "@/design-system";

const vazio = (o: Record<string, unknown>) => Object.keys(o).length === 0;

/** Valor de um campo do evento. Campo omitido pela classificação da ADR 0014 vem como `{ alterado: true }`; mascarado vem como "***". */
function texto(v: unknown): string {
  if (v && typeof v === "object" && "alterado" in v) return "alterado (valor não exibido)";
  if (v === null || v === undefined) return "—";
  return typeof v === "object" ? JSON.stringify(v) : String(v);
}

function Campos({ titulo, dados }: { titulo: string; dados: Record<string, unknown> }) {
  if (vazio(dados)) return null;
  return (
    <section aria-label={titulo}>
      <h3 className="mb-1 text-body font-medium">{titulo}</h3>
      <dl className="rounded-md bg-surface-sunken px-4 py-1">
        {Object.entries(dados).map(([campo, valor]) => (
          <div key={campo} className="flex justify-between gap-3 border-b border-line py-2 text-caption last:border-b-0">
            <dt className="text-ink-muted">{campo}</dt>
            <dd className="wl-mono text-right">{texto(valor)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** Um evento da auditoria por inteiro: quem, quando, o que mudou (antes e depois) e de onde veio. */
export function DetalheDoEvento({ id }: { id: number }) {
  const consulta = useQuery({ queryKey: ["auditoria", "evento", id], queryFn: () => auditoria.evento(id) });
  if (consulta.isPending)
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Carregando o evento…
      </p>
    );
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  const e = consulta.data;
  const tom = tomDoEvento(e);
  return (
    <div className="flex flex-col gap-4">
      <div>
        {tom ? (
          <StatusBadge tom={tom} compacto>
            {e.resumo}
          </StatusBadge>
        ) : (
          <span className="text-body font-medium">{e.resumo}</span>
        )}
        <p className="mt-1 mb-0 text-caption text-ink-muted">{e.detalhe}</p>
      </div>
      <dl className="rounded-md bg-surface-sunken px-4 py-1">
        {[
          ["Quando", dataHoraCompleta(e.ocorrido_em)],
          ["Quem", e.ator.nome],
          ...(e.suporte ? [["Suporte", `${e.suporte.atendente} · ${e.suporte.motivo}`]] : []),
          ...(e.objeto?.filial ? [["Filial", e.objeto.filial]] : []),
          ...(e.ip ? [["IP", e.ip]] : []),
          ...(e.aparelho ? [["Aparelho", e.aparelho]] : []),
        ].map(([rotulo, valor]) => (
          <div key={rotulo} className="flex justify-between gap-3 border-b border-line py-2 text-caption last:border-b-0">
            <dt className="text-ink-muted">{rotulo}</dt>
            <dd className="text-right font-medium">{valor}</dd>
          </div>
        ))}
      </dl>
      <Campos titulo="Antes" dados={e.antes} />
      <Campos titulo="Depois" dados={e.depois} />
    </div>
  );
}
