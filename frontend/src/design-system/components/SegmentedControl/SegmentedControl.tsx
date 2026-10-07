"use client";

export type OpcaoSegmento<V extends string> = { valor: V; rotulo: string };

/** Troca de visão entre duas a quatro opções curtas. Para mais de quatro, use um menu suspenso. */
export function SegmentedControl<V extends string>({
  opcoes,
  valor,
  aoMudar,
  rotulo,
}: {
  opcoes: ReadonlyArray<OpcaoSegmento<V>>;
  valor: V;
  aoMudar: (valor: V) => void;
  /** Nome do grupo para leitores de tela ("Período"). */
  rotulo: string;
}) {
  return (
    <div className="wl-seg" role="group" aria-label={rotulo}>
      {opcoes.map((o) => (
        <button key={o.valor} type="button" aria-pressed={o.valor === valor} onClick={() => aoMudar(o.valor)}>
          {o.rotulo}
        </button>
      ))}
    </div>
  );
}
