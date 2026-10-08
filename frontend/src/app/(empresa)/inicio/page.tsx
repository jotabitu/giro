import type { Metadata } from "next";
import { InicioPorPerfil } from "@/components/inicio/InicioPorPerfil";

export const metadata: Metadata = { title: "Início" };

export default function Inicio() {
  return <InicioPorPerfil />;
}
