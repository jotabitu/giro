import type { Metadata } from "next";
import { TabelaDePrecos } from "@/components/precos/TabelaDePrecos";

export const metadata: Metadata = { title: "Tabelas de preço" };

export default function Precos() {
  return <TabelaDePrecos />;
}
