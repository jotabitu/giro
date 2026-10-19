import { Check, Lock } from "lucide-react";
import { Icone } from "@/design-system";

// Opção marcável do ramo, igual na tela de Configurações e no passo do assistente (Admin-Ramo, Onboarding-Ramo).
export function OpcaoDoRamo({ titulo, descricao, aviso, marcado, travado, aoAlternar }: { titulo: string; descricao?: string; aviso?: string | null; marcado: boolean; travado: boolean; aoAlternar: () => void }) {
  return (
    <div>
      <button
        type="button"
        aria-pressed={marcado}
        aria-disabled={travado}
        onClick={() => !travado && aoAlternar()}
        className={`flex min-h-11 w-full items-start gap-3 rounded-lg border p-4 text-left text-ink ${marcado ? "border-ink bg-brand-soft" : "border-line bg-surface"} ${travado ? "opacity-70" : ""}`}
      >
        <span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-sm border ${marcado ? "border-ink bg-ink text-surface" : "border-line"}`} aria-hidden="true">
          {marcado && <Icone de={Check} />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[16px] font-semibold">{titulo}</span>
          {descricao && <span className="mt-0.5 block text-[14px] text-ink-muted">{descricao}</span>}
        </span>
        {travado && marcado && <Icone de={Lock} />}
      </button>
      {aviso && <p className="mt-1.5 mb-0 text-caption text-ink-muted">{aviso}</p>}
    </div>
  );
}
