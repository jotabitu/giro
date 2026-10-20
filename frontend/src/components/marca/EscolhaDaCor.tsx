import { TextField } from "@/design-system";
import type { CorDaEscolha } from "@/lib/marca-edicao";

/**
 * Cores de destaque. As bolinhas simulam na hora; com `digitavel` há também o campo `#RRGGBB` (Admin-Marca),
 * que simula 300 ms depois da última tecla. A cor do texto sobre ela volta da API.
 */
export function EscolhaDaCor({
  rotulo,
  cores,
  atual,
  digitavel,
  erro,
  dica,
  aoEscolher,
  aoDigitar,
}: {
  rotulo: string;
  cores: CorDaEscolha[];
  /** A cor escolhida agora (`#RRGGBB` ou o que está sendo digitado). */
  atual: string;
  digitavel?: boolean;
  erro?: string;
  dica: string;
  aoEscolher: (hex: string) => void;
  aoDigitar?: (texto: string) => void;
}) {
  const marcada = atual.trim().toUpperCase();
  const comCampo = digitavel && aoDigitar;
  return (
    <div className="flex flex-col gap-2.5">
      <div className="wl-field__label" id="rotulo-cor">
        {rotulo}
      </div>
      <div role="group" aria-labelledby="rotulo-cor" className="flex flex-wrap items-center gap-3.5">
        {cores.map((c) => {
          const ativa = c.hex.toUpperCase() === marcada;
          return (
            <button
              key={c.hex}
              type="button"
              aria-label={c.rotulo}
              aria-pressed={ativa}
              onClick={() => aoEscolher(c.hex)}
              className={`size-11 shrink-0 cursor-pointer rounded-full border-0 md:size-10 ${ativa ? "outline outline-2 outline-offset-2 outline-ink" : ""}`}
              style={{ background: c.hex }}
            />
          );
        })}
        <span className="wl-badge">
          <span className="size-3.5 rounded-full bg-brand" aria-hidden="true" />
          <span className="wl-mono">{marcada || "Cor padrão"}</span>
        </span>
      </div>
      {comCampo ? (
        <TextField rotulo="Outra cor (#RRGGBB)" mono value={atual} maxLength={7} placeholder="#C8F04A" autoComplete="off" spellCheck={false} onChange={(e) => aoDigitar(e.target.value)} erro={erro} dica={dica} />
      ) : (
        <span className={erro ? "wl-field__hint text-critical-ink" : "wl-field__hint"}>{erro ?? dica}</span>
      )}
    </div>
  );
}
