import type { Metadata } from "next";
import { FluxoEntrar } from "@/components/acesso/FluxoEntrar";

export const metadata: Metadata = { title: "Entrar" };

export default function Entrar() {
  return <FluxoEntrar />;
}
