// Lista de locações (T-022) contra docs/telas/html/Locacoes-Desktop.dc.html e Locacoes-Mobile.dc.html.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, locacoes, type Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes", useSearchParams: () => new URLSearchParams() }));

import { ListaLocacoes } from "./ListaLocacoes";

async function pagina(email: string): Promise<string> {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
  sessao.eu = await contas.eu();
  const cache = new QueryClient();
  cache.setQueryData(["locacoes", { aba: "abertas", plano: "todos", busca: "", cursor: undefined }], await locacoes.listar({ aba: "abertas" }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaLocacoes />
    </QueryClientProvider>,
  );
}

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

describe("lista de locações, vendedora", () => {
  it("indicadores, filtros e linhas na ordem da referência", async () => {
    const t = texto(await pagina("bruna@motorapida.com.br"));
    ordem(t, ["Locações", "Filial Centro · 42 ativas", "Nova locação"]);
    ordem(t, ["Ativas", "42", "71% da frota alugada", "Devolução atrasada", "Rafael · 25 dias", "Locações com parcela atrasada", "R$ 1.646,40 em atraso"]);
    ordem(t, ["Todas", "42", "Precisam de ação", "4", "Devolvem hoje", "Encerradas", "310"]);
    ordem(t, ["Cliente", "Veículo", "Plano e período", "Situação", "Pagamento"]);
    ordem(t, ["Rafael Sousa", "LOC-2790", "Honda Pop 110i", "PQD-6E21", "Semanal", "05 set → 12 set", "Devolução atrasada 25 dias", "R$ 1.347,00 em aberto", "Cobrar"]);
    ordem(t, ["Carlos Menezes", "LOC-2841", "Parcela 2 atrasada", "R$ 299,40 em aberto"]);
    ordem(t, ["Juliana Rocha", "LOC-2836", "Ativa", "Pago", "Abrir"]);
    ordem(t, ["Marcos Viana", "Mensal", "Pix automático"]);
    ordem(t, ["Lucas Ferreira", "LOC-2856", "Aguardando assinatura", "R$ 329,00 pago"]);
    ordem(t, ["Patrícia Gomes", "Pedido de cancelamento", "Multa R$ 84,80"]);
    ordem(t, ["Diego Martins", "Diária", "Cartão", "Mostrando 7 de 42"]);
  });

  it("celular: cartões com veículo, placa e período numa linha", async () => {
    const t = texto(await pagina("bruna@motorapida.com.br"));
    expect(t).toContain("Honda Pop 110i · PQD-6E21 · 05 set → 12 set");
    expect(t).toContain("Parcela atrasada");
  });

  it("o vistoriador não tem a lista (a API responde 403)", async () => {
    await contas.entrar({ email: "joao@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    await expect(locacoes.listar({ aba: "abertas" })).rejects.toMatchObject({ status: 403 });
  });
});
