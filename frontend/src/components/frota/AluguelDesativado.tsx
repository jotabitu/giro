import { StatusBadge } from "@/design-system";

/** VEI-21 (T-507): selo neutro ao lado do status, que continua o dele. O estado vem da API (`aluguel_ligado`). */
export function AluguelDesativado({ v }: { v: { aluguel_ligado?: boolean } }) {
  if (v.aluguel_ligado !== false) return null;
  return (
    <StatusBadge tom="neutro" compacto>
      Aluguel desativado
    </StatusBadge>
  );
}
