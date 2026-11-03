// T-410 · Reserva na confirmação (LOC-12, MOV-03): rótulo e bloco `reserva` do veículo, impedimento e 409 da Nova locação. Tudo vem da API.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, locacoes, veiculos, type Eu } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { corpoDaLocacao, valoresIniciais } from "@/lib/locacao-form";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/506", useSearchParams: () => new URLSearchParams() }));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { FichaVeiculo } from "./FichaVeiculo";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
  sessao.eu = await contas.eu();
}

describe("veículo reservado (LOC-12, MOV-03)", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));

  it("a API manda o rótulo pronto e o bloco reserva", async () => {
    const v = await veiculos.obter(506);
    expect(v.situacao.rotulo).toBe("Reservado na LOC-2850");
    expect(v.reserva).toEqual({ locacao_id: 5060, codigo: "LOC-2850", motivo: "locacao" });
    expect((await veiculos.obter(501)).reserva).toBeNull();
  });

  it("a ficha mostra o rótulo como vem, no desktop e no celular, com o link para a locação", async () => {
    const cliente = new QueryClient();
    const id = 506;
    cliente.setQueryData(["veiculo", id], await veiculos.obter(id));
    cliente.setQueryData(["veiculo", id, "documentos"], await veiculos.documentos(id));
    cliente.setQueryData(["veiculo", id, "locacoes"], await veiculos.locacoes(id));
    cliente.setQueryData(["veiculo", id, "manutencoes"], await veiculos.manutencoes(id));
    const h = renderToStaticMarkup(
      <QueryClientProvider client={cliente}>
        <FichaVeiculo id={id} />
      </QueryClientProvider>,
    );
    expect(h.match(/Reservado na LOC-2850/g)?.length).toBeGreaterThanOrEqual(2);
    expect(h).not.toContain("loc-2850");
    expect(h).toContain('href="/locacoes/5060"');
    expect(h).toContain("Ver LOC-2850");
  });

  it("a lista mostra o rótulo da API no veículo reservado", async () => {
    const lista = await veiculos.listar({ status: "reservado" });
    expect(lista.resultados.length).toBeGreaterThan(0);
    expect(lista.resultados.every((v) => v.situacao.rotulo.startsWith("Reservado na LOC-"))).toBe(true);
  });
});

describe("Nova locação com veículo reservado ou início vencido (LOC-12)", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));
  const AGORA = new Date("2026-10-07T12:20:00Z");

  it("o reservado não passa: impedimento LOC-03 na simulação e 409 ao confirmar", async () => {
    const corpo = corpoDaLocacao(valoresIniciais(1201, 506, AGORA), [])!;
    expect((await locacoes.simular(corpo)).impedimentos.map((i) => i.codigo)).toContain("LOC-03");
    const rascunho = await locacoes.criar(corpo);
    await expect(locacoes.confirmar(rascunho.id)).rejects.toMatchObject({ status: 409, codigo: "LOC-03" });
  });

  it("início com mais de 3 dias: impedimento inicio_vencido e 409 com a mensagem e as datas da API", async () => {
    const corpo = { ...corpoDaLocacao(valoresIniciais(1201, 509, AGORA), [])!, inicio: "2026-10-01T12:00:00.000Z" };
    const sim = await locacoes.simular(corpo);
    expect(sim.impedimentos.map((i) => i.codigo)).toContain("inicio_vencido");
    const rascunho = await locacoes.criar(corpo);
    const erro = await locacoes.confirmar(rascunho.id).catch((e: unknown) => e);
    expect(erro).toMatchObject({ status: 409, codigo: "inicio_vencido", detalhes: { inicio: "2026-10-01", ultimo_dia_retirada: "2026-10-04" } });
    expect(mensagemDoErro(erro)).toContain("prazo de retirada");
  });

  it("início de hoje com veículo disponível não tem impedimento de início", async () => {
    const corpo = corpoDaLocacao(valoresIniciais(1201, 509, AGORA), [])!;
    expect((await locacoes.simular(corpo)).impedimentos.map((i) => i.codigo)).not.toContain("inicio_vencido");
  });
});
