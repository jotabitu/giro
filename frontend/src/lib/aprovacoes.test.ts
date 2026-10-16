// Contador de Aprovações no menu muda na hora (T-241, APR-12, FIN-15).
import { QueryClient, QueryObserver } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { atualizarAposDecisao } from "./aprovacoes";

describe("atualizarAposDecisao", () => {
  it("lê os contadores de novo logo após aprovar, sem esperar o intervalo de 60 s", async () => {
    const cliente = new QueryClient();
    let pendentes = 2;
    let leituras = 0;
    const contadores = new QueryObserver(cliente, {
      queryKey: ["contadores"],
      queryFn: async () => (leituras++, { aprovacoes: pendentes }),
      staleTime: 60_000,
      refetchInterval: 60_000,
    });
    const parar = contadores.subscribe(() => {});
    await contadores.refetch();
    expect(contadores.getCurrentResult().data).toEqual({ aprovacoes: 2 });
    const antes = leituras;

    pendentes = 1; // a API já descontou o pedido aprovado
    await atualizarAposDecisao(cliente);

    expect(leituras).toBe(antes + 1);
    expect(contadores.getCurrentResult().data).toEqual({ aprovacoes: 1 });
    parar();
  });

  it("também lê de novo as aprovações e as despesas", async () => {
    const cliente = new QueryClient();
    const lidas: string[] = [];
    const observadores = ["aprovacoes", "despesas"].map((k) => new QueryObserver(cliente, { queryKey: [k], queryFn: async () => (lidas.push(k), 1), staleTime: 60_000 }));
    const paradas = observadores.map((o) => o.subscribe(() => {}));
    await Promise.all(observadores.map((o) => o.refetch()));
    lidas.length = 0;
    await atualizarAposDecisao(cliente);
    expect(lidas.sort()).toEqual(["aprovacoes", "despesas"]);
    paradas.forEach((p) => p());
  });
});
