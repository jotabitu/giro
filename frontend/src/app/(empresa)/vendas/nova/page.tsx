import type { Metadata } from "next";
import { Suspense } from "react";
import { TelaDaVenda } from "@/components/vendas/TelaDaVenda";

export const metadata: Metadata = { title: "Nova venda" };

const numero = (v: string | string[] | undefined) => {
  const n = Number(Array.isArray(v) ? v[0] : v);
  return Number.isInteger(n) && n > 0 ? n : undefined;
};

/** Nova venda (VEN-13): nasce em interessado, em proposta ou esperando o gerente. `?veiculo=` já traz o veículo escolhido. */
export default async function NovaVenda({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const q = await searchParams;
  return (
    <Suspense>
      <TelaDaVenda veiculoInicial={numero(q.veiculo)} />
    </Suspense>
  );
}
