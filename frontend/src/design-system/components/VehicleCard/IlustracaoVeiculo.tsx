export type TipoVeiculo = "moto" | "carro";

/**
 * Desenho neutro do veículo, para o card sem foto. A moto é o SVG de
 * docs/design-system/components/VehicleCard/preview.html; o carro segue o mesmo traço.
 * Cor herdada (currentColor); decorativo.
 */
export function IlustracaoVeiculo({ tipo = "moto" }: { tipo?: TipoVeiculo }) {
  return (
    <svg viewBox="0 0 120 64" width="168" height="90" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {tipo === "moto" ? (
        <>
          <circle cx="24" cy="44" r="14" />
          <circle cx="96" cy="44" r="14" />
          <path d="M24 44 44 20h26l16 24M44 20l-8-10H24M70 20l6-12h14" />
          <path d="M52 44h22" />
        </>
      ) : (
        <>
          <circle cx="32" cy="46" r="9" />
          <circle cx="88" cy="46" r="9" />
          <path d="M8 46v-9l12-3 14-16h38l16 16 12 3v9h-10M23 46h56M41 46h-0" />
          <path d="M38 34h46M60 18v16" />
        </>
      )}
    </svg>
  );
}
