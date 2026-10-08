import { Check, Circle } from "lucide-react";
import { Icone } from "@/design-system";
import type { RegraDeSenha } from "@/lib/senha";

export function RegrasDeSenha({ regras }: { regras: RegraDeSenha[] }) {
  return (
    <ul className="flex flex-col gap-1" aria-label="Regras da senha">
      {regras.map((r) => (
        <li key={r.chave} className={`flex items-center gap-2 text-caption ${r.ok ? "text-success-ink" : "text-ink-muted"}`}>
          <Icone de={r.ok ? Check : Circle} />
          {r.texto}
          <span className="sr-only">{r.ok ? " (cumprida)" : " (pendente)"}</span>
        </li>
      ))}
    </ul>
  );
}
