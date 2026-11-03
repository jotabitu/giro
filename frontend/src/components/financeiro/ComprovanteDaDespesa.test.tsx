// T-416 · Ver comprovante na despesa paga (FIN-05, AUD-05, AUD-09). Contrato: docs/api/financeiro.md, `comprovante`.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, financeiro, type Despesa, type Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/financeiro/despesas", useSearchParams: () => new URLSearchParams() }));

import { DetalheDaDespesa } from "./DetalheDaDespesa";

function html(d: Despesa): string {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>
      <DetalheDaDespesa id={d.id} inicial={d} eu={sessao.eu as Eu} aoFechar={() => {}} aoConcluir={() => {}} />
    </QueryClientProvider>,
  );
}

describe("comprovante da despesa paga", () => {
  beforeAll(async () => {
    const r = await contas.entrar({ email: "mariana@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    sessao.eu = await contas.eu();
  });

  it("FIN-05, AUD-05: paga com comprovante mostra Ver comprovante pela URL assinada e não esconde a nota", async () => {
    const d = await financeiro.obterDespesa(804);
    const h = html({ ...d, nota: { url: "/notas/804.jpg", url_expira_em: "2026-10-05T12:15:00Z" } });
    expect(h).toContain("Ver comprovante");
    expect(h).toContain('href="/comprovantes/804.pdf"');
    expect(h).toContain('target="_blank"');
    expect(h).toContain("Ver a nota");
  });

  it("FIN-05: paga sem comprovante, ou ainda a pagar, não tem o botão", async () => {
    expect(html(await financeiro.obterDespesa(802))).not.toContain("Ver comprovante");
    expect(html(await financeiro.obterDespesa(803))).not.toContain("Ver comprovante");
  });

  it("AUD-09: com o token de suporte a API manda comprovante null; a tela não mostra o botão e a nota continua", async () => {
    const d = await financeiro.obterDespesa(804);
    const h = html({ ...d, comprovante: null, nota: { url: "/notas/804.jpg", url_expira_em: "2026-10-05T12:15:00Z" } });
    expect(h).not.toContain("Ver comprovante");
    expect(h).toContain("Ver a nota");
  });

  it("pagar com comprovante devolve a despesa já com o comprovante assinado", async () => {
    const paga = await financeiro.pagarDespesa(803, { forma: "pix", pago_em: "2026-10-07T12:00:00Z", comprovante: new File(["x"], "comp.pdf") });
    expect(paga.comprovante?.url).toContain("/comprovantes/803");
  });
});
