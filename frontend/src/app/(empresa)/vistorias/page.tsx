import type { Metadata } from "next";
import { Suspense } from "react";
import { AgendaDoVistoriador } from "@/components/vistorias/AgendaDoVistoriador";

export const metadata: Metadata = { title: "Vistorias" };

export default function Vistorias() {
  return (
    <Suspense>
      <AgendaDoVistoriador />
    </Suspense>
  );
}
