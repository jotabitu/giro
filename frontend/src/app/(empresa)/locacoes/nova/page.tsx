import type { Metadata } from "next";
import { Suspense } from "react";
import { NovaLocacao } from "@/components/locacoes/NovaLocacao";

export const metadata: Metadata = { title: "Nova locação" };

const numero = (v: string | string[] | undefined) => {
  const n = Number(Array.isArray(v) ? v[0] : v);
  return Number.isInteger(n) && n > 0 ? n : undefined;
};

export default async function NovaLocacaoPagina({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const q = await searchParams;
  return (
    <Suspense>
      <NovaLocacao clienteInicial={numero(q.cliente)} veiculoInicial={numero(q.veiculo)} rascunhoInicial={numero(q.rascunho)} />
    </Suspense>
  );
}
