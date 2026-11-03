// T-415 · CRLV-e: escolher a versão quando várias batem (VEI-08). O caso do Cruze: "CHEVROLET/CRUZE LT NB", 3 versões.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, veiculos } from "@/lib/api";
import { valoresDaLeitura } from "@/lib/veiculos";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/novo", useSearchParams: () => new URLSearchParams() }));

import { PreencherPeloCrlv } from "./PreencherPeloCrlv";

const pdf = (nome: string) => new File(["%PDF"], nome, { type: "application/pdf" });

function tela(lido: Parameters<typeof PreencherPeloCrlv>[0]["lido"]): string {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>
      <PreencherPeloCrlv lido={lido} aoLer={() => {}} aoRemover={() => {}} aoEscolherVersao={() => {}} />
    </QueryClientProvider>,
  );
}

describe("versões que batem com o CRLV-e (VEI-08)", () => {
  beforeAll(async () => {
    const r = await contas.entrar({ email: "rodrigo@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") throw new Error("esperava pronto");
  });

  it("Cruze: a marca vem preenchida, o modelo não, e a API manda as 3 versões", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-cruze.pdf"));
    expect(leitura.quantidade).toBe(8);
    expect(leitura.rotulo).toBe("CRLV-e lido · 8 campos preenchidos");
    expect(leitura.dicas.marca_modelo).toBe("CHEVROLET/CRUZE LT NB");
    expect(leitura.dicas.candidatos).toHaveLength(3);
    const { valores } = valoresDaLeitura(leitura);
    expect(valores.marca).toBe("GM - Chevrolet");
    expect(valores.modelo).toBeUndefined();
  });

  it("a tela mostra as 3 versões para escolher, como botões de 44 px", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-cruze.pdf"));
    const h = tela({ arquivo: pdf("crlv-cruze.pdf"), leitura });
    expect(h).toContain("CHEVROLET/CRUZE LT NB");
    expect(h).toContain("Escolha a versão:");
    for (const c of leitura.dicas.candidatos) expect(h).toContain(c.modelo);
    expect(h.match(/aria-pressed="false"/g)).toHaveLength(3);
    expect(h).toContain("min-h-[44px]");
    expect(h).toContain("CRLV-e lido · 8 campos preenchidos");
  });

  it("CA-247-05: sem versões a tela continua mandando escolher da lista", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-exemplo.pdf"));
    expect(leitura.dicas.candidatos).toEqual([]);
    const h = tela({ arquivo: pdf("crlv-exemplo.pdf"), leitura: { ...leitura, dicas: { marca_modelo: "SUZUKI/YES 125", candidatos: [] } } });
    expect(h).toContain("Escolha a marca e o modelo da lista abaixo.");
    expect(h).not.toContain("Versões que batem");
  });
});
