import type { Metadata } from "next";
import { Configuracoes } from "@/components/admin/Configuracoes";

export const metadata: Metadata = { title: "Configurações" };

export default function PaginaConfiguracoes() {
  return <Configuracoes />;
}
