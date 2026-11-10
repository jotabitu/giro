// T-444 · O alerta do bloco da ficha vem da API como { codigo, rotulo, tom } (ADR 0015, veiculos.md): a ficha mostra o rótulo com o tom da API.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, veiculos, type Eu, type VeiculoDetalhe } from "@/lib/api";
import { FichaVeiculo } from "./FichaVeiculo";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

beforeAll(async () => {
  const r = await contas.entrar({ email: "rodrigo@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
});

async function pagina(ficha: VeiculoDetalhe) {
  const cliente = new QueryClient();
  cliente.setQueryData(["veiculo", ficha.id], ficha);
  cliente.setQueryData(["veiculo", ficha.id, "documentos"], await veiculos.documentos(ficha.id));
  cliente.setQueryData(["veiculo", ficha.id, "locacoes"], await veiculos.locacoes(ficha.id));
  cliente.setQueryData(["veiculo", ficha.id, "manutencoes"], await veiculos.manutencoes(ficha.id));
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cliente}>
      <FichaVeiculo id={ficha.id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = html.replace(/^(<link[^>]*>)+/, "").match(/^<div class="hidden md:block">(.*)<\/div><div class="md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop, celular };
}

describe("alerta da locação atual na ficha (T-444)", () => {
  it("LOC-10: devolução atrasada mostra o rótulo do alerta, nos dois tamanhos, sem quebrar", async () => {
    const base = await veiculos.obter(501);
    const atual = base.locacao_atual as NonNullable<VeiculoDetalhe["locacao_atual"]>;
    const ficha: VeiculoDetalhe = { ...base, locacao_atual: { ...atual, status: "devolucao_atrasada", alerta: { codigo: "atrasado", rotulo: "Atrasado", tom: "perigo" } } };
    const { desktop, celular } = await pagina(ficha);
    expect(desktop).toContain("Atrasado");
    expect(celular).toContain("Atrasado");
    expect(desktop).not.toContain("[object Object]");
    expect(celular).not.toContain("[object Object]");
  });

  it("o falso manda o alerta como objeto, como a API", async () => {
    const ficha = await veiculos.obter(501);
    expect(typeof ficha.locacao_atual?.alerta === "object" || ficha.locacao_atual?.alerta === undefined).toBe(true);
  });
});
