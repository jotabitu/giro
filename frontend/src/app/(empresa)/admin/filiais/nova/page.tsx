import type { Metadata } from "next";
import { FormularioDaFilial } from "@/components/admin/FormularioDaFilial";

export const metadata: Metadata = { title: "Nova filial" };

export default function NovaFilial() {
  return <FormularioDaFilial />;
}
