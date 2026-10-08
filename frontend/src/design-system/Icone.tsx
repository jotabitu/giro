import type { LucideIcon } from "lucide-react";

/** Ícone de traço de 20px (Lucide), cor herdada do texto. Decorativo: o texto ao lado diz o que é. */
export function Icone({ de: Desenho, className }: { de: LucideIcon; className?: string }) {
  const Componente = Desenho;
  return <Componente className={className ? `wl-i ${className}` : "wl-i"} aria-hidden="true" />;
}
