// T-239 · Nova locação com "Todas as filiais": a locação nasce numa filial só (a API pede o X-Filial de uma).
// Antes, a simulação voltava 400 no campo `filial`, a tela escondia o erro e os dois botões ficavam desligados sem explicação.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { clientes, contas, locacoes, veiculos } from "@/lib/api";
import { corpoDaLocacao, valoresIniciais } from "@/lib/locacao-form";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes/nova", useSearchParams: () => new URLSearchParams() }));
const filial = vi.hoisted(() => ({ todas: false }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => ({ escolha: filial.todas ? "todas" : "1", nome: null, todas: filial.todas, filiais: [], podeEscolherTodas: true, trocar() {} }) }));

import { NovaLocacao } from "./NovaLocacao";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const botoes = (h: string) => h.match(/<button[^>]*>(Continuar para vistoria|Salvar como reserva)/g) ?? [];
const AGORA = new Date("2026-10-07T12:20:00Z");

async function pagina(): Promise<string> {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(AGORA);
  try {
    const planos = await locacoes.planosEspeciais();
    const corpo = corpoDaLocacao(valoresIniciais(1206, 504, AGORA), planos.resultados)!;
    const cache = new QueryClient();
    cache.setQueryData(["cliente", 1206], await clientes.obter(1206));
    cache.setQueryData(["veiculo", 504], await veiculos.obter(504));
    cache.setQueryData(["extras"], await locacoes.extras());
    cache.setQueryData(["planos-especiais"], planos);
    cache.setQueryData(["locacao-simulacao", JSON.stringify(corpo)], await locacoes.simular(corpo));
    return renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <NovaLocacao clienteInicial={1206} veiculoInicial={504} />
      </QueryClientProvider>,
    );
  } finally {
    vi.useRealTimers();
  }
}

describe("nova locação e a filial escolhida (T-239)", () => {
  beforeAll(async () => {
    const r = await contas.entrar({ email: "rodrigo@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") throw new Error("esperava pronto");
  });

  it("numa filial só, o resumo aparece e a tela não pede filial", async () => {
    filial.todas = false;
    const t = texto(await pagina());
    expect(t).toContain("Hoje, na retirada");
    expect(t).not.toContain("Escolha uma filial no menu");
  });

  it("em Todas as filiais, a tela diz para escolher uma filial e os dois botões ficam desligados", async () => {
    filial.todas = true;
    const html = await pagina();
    expect(texto(html)).toContain("Escolha uma filial no menu para criar a locação.");
    expect(texto(html)).not.toContain("Calculando…");
    const b = botoes(html);
    expect(b).toHaveLength(2);
    expect(b.every((x) => x.includes("disabled"))).toBe(true);
  });
});
