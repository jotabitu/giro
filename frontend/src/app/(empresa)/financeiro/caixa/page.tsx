import type { Metadata } from "next";
import { CaixaDoDia } from "@/components/financeiro/CaixaDoDia";

export const metadata: Metadata = { title: "Caixa do dia" };

export default function Caixa() {
  return <CaixaDoDia />;
}
