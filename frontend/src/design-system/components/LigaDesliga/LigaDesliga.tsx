"use client";

export type LigaDesligaProps = {
  ligado: boolean;
  /** Recebe o valor pedido (o contrário do atual). Quem usa decide se muda na hora ou depois de confirmar. */
  aoMudar: (ligado: boolean) => void;
  /** Nome acessível: diz o que liga ("Oferecer plano semanal"). */
  rotulo: string;
  desabilitado?: boolean;
};

/** Interruptor de uma opção que vale já: ligar ou desligar um plano de preço. Controlado. */
export function LigaDesliga({ ligado, aoMudar, rotulo, desabilitado = false }: LigaDesligaProps) {
  return (
    <button
      type="button"
      role="switch"
      className="wl-toggle"
      aria-checked={ligado}
      aria-label={rotulo}
      disabled={desabilitado}
      onClick={() => aoMudar(!ligado)}
    />
  );
}
