import type { Metadata, Viewport } from "next";
import { Landing } from "@/components/landing/Landing";

// "/" no domínio da plataforma (DOMINIO_BASE, www. e localhost). No subdomínio da empresa o
// middleware manda para /entrar antes de chegar aqui (src/lib/host-landing.ts).
export const metadata: Metadata = {
  title: "Giro locadoras",
  description: "Sistema de gestão white label para locadoras e revendas de motos e carros. Teste grátis por 14 dias, sem cartão.",
  // Só na landing: SVG oficial do kit. O resto do sistema usa src/app/icon.ico (favicon.test.ts).
  icons: { icon: { url: "/marca/giro-motos-app-icon.svg", type: "image/svg+xml" } },
};
export const viewport: Viewport = { themeColor: "#111114" };

export default function Pagina() {
  return <Landing />;
}
