// T-415, T-521 · CRLV-e: marca e modelo sempre preenchidos (VEI-08). O caso do Cruze: "CHEVROLET/CRUZE LT NB", 3 versões;
// a API preenche a mais parecida (`dicas.escolhido`) e a tela mostra as outras abaixo do modelo para trocar.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import type { ReactElement } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, veiculos, type LeituraCrlv } from "@/lib/api";
import { valoresDaLeitura } from "@/lib/veiculos";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/novo", useSearchParams: () => new URLSearchParams() }));

import { CampoDoModelo } from "./CampoDoModelo";
import { PreencherPeloCrlv } from "./PreencherPeloCrlv";

const pdf = (nome: string) => new File(["%PDF"], nome, { type: "application/pdf" });
const html = (el: ReactElement) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);
const registro = { name: "modelo" as const, onChange: async () => {}, onBlur: async () => {}, ref: () => {} };

/** O campo Modelo como o cadastro o monta depois da leitura, com o valor que está no formulário. */
function campoDoModelo(leitura: LeituraCrlv, marca: string, modelo: string, lido: boolean) {
  return html(<CampoDoModelo tipo="carro" marca={marca} modelo={modelo} registro={registro} dica={(padrao) => (lido ? "Lido do documento" : padrao)} versoes={leitura.dicas.candidatos} aoEscolher={() => {}} />);
}

describe("marca e modelo pelo CRLV-e (VEI-08)", () => {
  beforeAll(async () => {
    const r = await contas.entrar({ email: "rodrigo@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") throw new Error("esperava pronto");
  });

  it("test_vei_08_ca_521_01: várias versões, a leitura preenche marca e modelo com a escolhida pela API e conta os dois", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-cruze.pdf"));
    expect(leitura.dicas.escolhido?.modelo).toBe("CRUZE LT 1.4 16V Turbo Flex 4p Aut.");
    expect(leitura.lidos).toContain("modelo");
    expect(leitura.rotulo).toBe("CRLV-e lido · 9 campos preenchidos");
    const { valores, lidos } = valoresDaLeitura(leitura);
    expect(valores.marca).toBe("GM - Chevrolet");
    expect(valores.modelo).toBe("CRUZE LT 1.4 16V Turbo Flex 4p Aut.");
    expect(lidos).toEqual(expect.arrayContaining(["marca", "modelo"]));
  });

  it("test_vei_08_ca_521_01: as versões aparecem abaixo do modelo, com a escolhida marcada, e o campo diz Lido do documento", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-cruze.pdf"));
    const h = campoDoModelo(leitura, "GM - Chevrolet", leitura.dicas.escolhido!.modelo, true);
    const campo = h.indexOf('role="combobox"');
    const versoes = h.indexOf('aria-label="Versões que batem com o documento"');
    expect(campo).toBeGreaterThan(-1);
    expect(versoes).toBeGreaterThan(campo);
    for (const c of leitura.dicas.candidatos) expect(h).toContain(c.modelo);
    expect(h.match(/aria-pressed="true"/g)).toHaveLength(1);
    expect(h.match(/aria-pressed="false"/g)).toHaveLength(2);
    expect(h).toMatch(/aria-pressed="true"[^>]*>CRUZE LT 1\.4 16V Turbo Flex 4p Aut\./);
    expect(h).toContain("min-h-[44px]");
    expect(h).toContain("Lido do documento");
  });

  it("test_vei_08_ca_521_01: trocar a versão move a marca para a nova, e o rótulo da API não muda", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-cruze.pdf"));
    const outra = leitura.dicas.candidatos[2]!;
    const h = campoDoModelo(leitura, outra.marca, outra.modelo, true);
    expect(h.match(/aria-pressed="true"/g)).toHaveLength(1);
    expect(h).toMatch(/aria-pressed="true"[^>]*>CRUZE LT 1\.8 16V FlexPower 4p Mec\./);
    const painel = html(<PreencherPeloCrlv lido={{ arquivo: pdf("crlv-cruze.pdf"), leitura }} aoLer={() => {}} aoRemover={() => {}} />);
    expect(painel).toContain("CRLV-e lido · 9 campos preenchidos");
    expect(painel).toContain("CHEVROLET/CRUZE LT NB");
    // As versões saíram do painel: ficam só abaixo do modelo.
    expect(painel).not.toContain("Versões que batem");
  });

  it("test_vei_08_ca_521_02: sem versão no catálogo, marca e modelo vêm do texto lido e não há versões para trocar", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-yes125.pdf"));
    const { valores } = valoresDaLeitura(leitura);
    expect([valores.marca, valores.modelo]).toEqual(["Suzuki", "YES 125"]);
    expect(leitura.dicas).toEqual({ marca_modelo: "SUZUKI/YES 125", candidatos: [], escolhido: null });
    const h = campoDoModelo(leitura, "Suzuki", "YES 125", true);
    expect(h).not.toContain("Versões que batem");
    expect(h).toContain("Lido do documento");
  });

  it("test_vei_08_ca_521_03: uma versão só preenche como antes, sem versões nem texto do documento", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-tbc5h21.pdf"));
    expect(leitura.dicas).toEqual({ marca_modelo: null, candidatos: [], escolhido: null });
    expect(leitura.rotulo).toBe("CRLV-e lido · 16 campos preenchidos");
    const h = campoDoModelo(leitura, "Honda", "Pop 110i ES", true);
    expect(h).not.toContain("Versões que batem");
  });

  it("depois que a pessoa muda o modelo, volta a dica da lista FIPE", async () => {
    const leitura = await veiculos.lerCrlv(pdf("crlv-cruze.pdf"));
    const h = campoDoModelo(leitura, "GM - Chevrolet", "CRUZE", false);
    expect(h).toContain("Escolha da lista ou digite");
    expect(h).not.toMatch(/aria-pressed="true"/);
  });
});
