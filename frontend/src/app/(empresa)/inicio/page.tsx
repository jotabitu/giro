import type { Metadata } from "next";
import { VisaoGeral } from "@/components/casca/VisaoGeral";

export const metadata: Metadata = { title: "Visão geral" };

export default function Inicio() {
  return <VisaoGeral />;
}
