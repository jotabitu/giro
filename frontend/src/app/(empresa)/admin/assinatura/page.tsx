import type { Metadata } from "next";
import { AssinaturaDaEmpresa } from "@/components/admin/AssinaturaDaEmpresa";

export const metadata: Metadata = { title: "Assinatura" };

export default function Assinatura() {
  return <AssinaturaDaEmpresa />;
}
