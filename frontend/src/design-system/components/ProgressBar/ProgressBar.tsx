/** Barra de andamento: trilho surface-sunken e preenchimento solid. O valor vem pronto da API (0 a 100). */
export function ProgressBar({ valor, rotulo }: { valor: number; /** Nome lido pelo leitor de tela: "Primeiros passos". */ rotulo: string }) {
  const pct = Number.isFinite(valor) ? Math.min(100, Math.max(0, valor)) : 0;
  return (
    <div className="wl-progressbar" role="progressbar" aria-label={rotulo} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}>
      <div className="wl-progressbar__fill" style={{ width: `${pct}%` }} />
    </div>
  );
}
