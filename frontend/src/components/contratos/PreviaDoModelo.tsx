"use client";

import { useQuery } from "@tanstack/react-query";
import { modelosContrato as api } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";

/**
 * "Ver com dados reais": o HTML já vem renderizado e sanitizado pela API (lista branca de tags, sem atributos, S-09),
 * então só é posto na página como veio. Sem `locacaoId`, a API usa os dados de exemplo.
 */
export function PreviaDoModelo({ modeloId, locacaoId, titulo }: { modeloId: number; locacaoId?: number; titulo: string }) {
  const consulta = useQuery({ queryKey: ["contratos", "previa", modeloId, locacaoId ?? "exemplo"], queryFn: () => api.previa(modeloId, locacaoId) });
  return (
    <section className="flex flex-col gap-2" aria-label={`Prévia · ${titulo}`}>
      {consulta.isPending && (
        <p className="m-0 text-body text-ink-muted" aria-busy="true">
          Montando a prévia…
        </p>
      )}
      {consulta.isError && (
        <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isSuccess && (
        <div
          className="max-h-[420px] overflow-y-auto rounded-[20px] bg-surface-sunken p-5 text-body [&_h1]:mb-3 [&_h1]:text-heading [&_h2]:mb-2 [&_h2]:text-heading [&_p]:my-2 [&_table]:w-full [&_td]:border [&_td]:border-line [&_td]:p-1.5 [&_th]:border [&_th]:border-line [&_th]:p-1.5"
          dangerouslySetInnerHTML={{ __html: consulta.data }}
        />
      )}
    </section>
  );
}
