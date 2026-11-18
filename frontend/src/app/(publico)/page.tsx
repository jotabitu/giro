import type { Metadata, Viewport } from "next";
import { Landing } from "@/components/landing/Landing";

// "/" no domínio da plataforma (giro.ceo, www.giro.ceo, localhost). No subdomínio da empresa o
// middleware manda para /entrar antes de chegar aqui (src/lib/host-landing.ts).
export const metadata: Metadata = {
  title: "Giro locadoras",
  description: "Sistema de gestão white label para locadoras e revendas de motos e carros. Teste grátis por 14 dias, sem cartão.",
};
export const viewport: Viewport = { themeColor: "#111114" };

export default function Pagina() {
  return <Landing />;
}
