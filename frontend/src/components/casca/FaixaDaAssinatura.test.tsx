// Faixa de assinatura suspensa ou pausada (T-412): PLT-02, PLT-06 e docs/api/plataforma.md, `faixa_aviso`.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { FaixaDaAssinatura, empresaComFaixa, textoDaFaixa } from "./FaixaDaAssinatura";

function eu(status: string, somenteLeitura: boolean, administracao: boolean): Eu {
  return { empresa: { nome_exibicao: "Moto Rápida", status, somente_leitura: somenteLeitura }, pode: { administracao } } as unknown as Eu;
}

function faixa(usuario: Eu, faixaAviso?: string): string {
  sessao.eu = usuario;
  const cliente = new QueryClient();
  if (faixaAviso) cliente.setQueryData(["assinatura"], { faixa_aviso: faixaAviso });
  return renderToStaticMarkup(
    <QueryClientProvider client={cliente}>
      <FaixaDaAssinatura />
    </QueryClientProvider>,
  );
}

describe("Faixa de assinatura suspensa ou pausada", () => {
  it("PLT-02: suspensa mostra o texto da API e o caminho para pagar a fatura (administrador)", () => {
    const h = faixa(eu("suspensa", true, true), "Assinatura suspensa por falta de pagamento. Pague a fatura para voltar a operar.");
    expect(h).toContain('data-faixa-assinatura="suspensa"');
    expect(h).toContain("Assinatura suspensa por falta de pagamento.");
    expect(h).toContain('href="/admin/assinatura"');
    expect(h).toContain("Pagar a fatura");
  });

  it("PLT-06: pausada mostra a faixa com o texto da API e leva à assinatura", () => {
    const h = faixa(eu("pausada", true, true), "Assinatura pausada até 21 jan. Você só consulta os dados.");
    expect(h).toContain("Assinatura pausada até 21 jan. Você só consulta os dados.");
    expect(h).toContain("Ver a assinatura");
    expect(h).not.toContain("Pagar a fatura");
  });

  it("quem não administra vê a faixa sem link e é mandado ao administrador", () => {
    const h = faixa(eu("suspensa", true, false));
    expect(h).toContain("Fale com o administrador da empresa.");
    expect(h).not.toContain("/admin/assinatura");
  });

  it("empresa ativa, em teste ou inadimplente não ganha esta faixa", () => {
    expect(faixa(eu("ativa", false, true))).toBe("");
    expect(faixa(eu("em_teste", false, true))).toBe("");
    expect(empresaComFaixa("inadimplente", false)).toBe(false);
    expect(empresaComFaixa("suspensa", true)).toBe(true);
    expect(empresaComFaixa("pausada", true)).toBe(true);
  });

  it("sem faixa_aviso da API usa o texto fixo do contrato, sem data nem valor", () => {
    expect(textoDaFaixa("suspensa", null)).toBe("Assinatura suspensa. Você só consulta os dados até pagar a fatura.");
    expect(textoDaFaixa("pausada", undefined)).toBe("Assinatura pausada. Você só consulta os dados.");
  });
});
