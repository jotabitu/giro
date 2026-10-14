import type { Metadata } from "next";
import { Suspense } from "react";
import { ListaDespesas } from "@/components/financeiro/ListaDespesas";

export const metadata: Metadata = { title: "Despesas" };

export default function Despesas() {
  return (
    <Suspense>
      <ListaDespesas />
    </Suspense>
  );
}
