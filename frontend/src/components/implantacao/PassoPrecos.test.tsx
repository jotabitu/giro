// T-403 · Depois de salvar a categoria, o passo relê o andamento para liberar o Continuar sem recarregar (IMP-07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

const painel = vi.hoisted(() => ({ aoAvisar: null as null | ((aviso: string) => void) }));
vi.mock("@/components/precos/CategoriasDePreco", () => ({
  CategoriasDePreco: (props: { aoAvisar: (aviso: string) => void }) => {
    painel.aoAvisar = props.aoAvisar;
    return null;
  },
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {}, replace: () => {} }) }));

import { PassoPrecos } from "./PassoPrecos";

describe("Tabela de preços (T-403)", () => {
  it("imp_07_precos_invalida_andamento: o aviso de categoria salva invalida o andamento do assistente", () => {
    const cache = new QueryClient();
    const invalidar = vi.spyOn(cache, "invalidateQueries");
    renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <PassoPrecos feito={false} voltarPara="/implantacao/filial" pularPara="/implantacao/contrato" aoContinuar={() => {}} />
      </QueryClientProvider>,
    );
    expect(painel.aoAvisar).not.toBeNull();
    painel.aoAvisar!("Categoria criada.");
    expect(invalidar).toHaveBeenCalledWith({ queryKey: ["implantacao"] });
  });
});
