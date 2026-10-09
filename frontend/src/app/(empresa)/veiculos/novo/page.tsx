import type { Metadata } from "next";
import { NovoVeiculoForm } from "@/components/frota/NovoVeiculoForm";

export const metadata: Metadata = { title: "Cadastrar veículo" };

export default function NovoVeiculo() {
  return <NovoVeiculoForm />;
}
