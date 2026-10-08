import type { Metadata } from "next";
import { NovoClienteForm } from "@/components/clientes/NovoClienteForm";

export const metadata: Metadata = { title: "Novo cliente" };

export default function NovoCliente() {
  return <NovoClienteForm />;
}
