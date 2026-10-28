import type { Metadata } from "next";
import { ControleDoSuporte } from "@/components/admin/ControleDoSuporte";

export const metadata: Metadata = { title: "Controle do suporte" };

export default function Suporte() {
  return <ControleDoSuporte />;
}
