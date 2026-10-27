import type { Metadata } from "next";
import { TelaDeModelosDeContrato } from "@/components/contratos/TelaDeModelosDeContrato";

export const metadata: Metadata = { title: "Modelos de contrato" };

export default function Contratos() {
  return <TelaDeModelosDeContrato />;
}
