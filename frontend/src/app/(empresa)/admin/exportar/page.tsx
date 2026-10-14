import type { Metadata } from "next";
import { ExportarDados } from "@/components/admin/ExportarDados";

export const metadata: Metadata = { title: "Exportar dados" };

export default function Exportar() {
  return <ExportarDados />;
}
