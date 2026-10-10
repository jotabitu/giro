import { Check, Clock, TriangleAlert } from "lucide-react";
import { Icone, Panel } from "@/design-system";
import type { AnaliseCadastro } from "@/lib/api";

const ICONE = { ok: Check, pendente: Clock, problema: TriangleAlert } as const;
const COR = { ok: "bg-success-soft text-success-ink", pendente: "bg-warning-soft text-warning-ink", problema: "bg-critical-soft text-critical-ink" } as const;
const TEXTO = { ok: "conferido", pendente: "pendente", problema: "com problema" } as const;

/** Análise do cadastro (CLI-04): o resultado de cada item vem da API; aqui só se mostra. */
export function AnaliseDoCadastro({ analise, carregando, titulo = "Análise do cadastro" }: { analise?: AnaliseCadastro; carregando?: boolean; titulo?: string }) {
  return (
    <Panel titulo={titulo}>
      {!analise && (
        <p className="text-body text-ink-muted" aria-busy={carregando}>
          {carregando ? "Conferindo…" : "A análise aparece quando você preencher o documento."}
        </p>
      )}
      {analise && (
        <ul>
          {analise.itens.map((i) => (
            <li key={i.codigo} className="flex items-center gap-3 border-b border-line py-[11px] text-body last:border-b-0">
              <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-pill ${COR[i.situacao]}`}>
                <Icone de={ICONE[i.situacao]} className="!h-4 !w-4" />
              </span>
              <span>
                {i.rotulo}
                <span className="sr-only"> ({TEXTO[i.situacao]})</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
