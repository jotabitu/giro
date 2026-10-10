// Devolução (T-022) contra docs/telas/html/Devolucao-Desktop.dc.html e Devolucao-Mobile.dc.html. O caso é o do DEV-03 (LOC-2836, R$ 183,00).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, vistorias } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes/2836/devolucao", useSearchParams: () => new URLSearchParams() }));

import { Devolucao } from "./Devolucao";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

async function pagina(locacaoId: number): Promise<{ html: string; t: string }> {
  const d = await vistorias.abrirDevolucao(locacaoId);
  const cache = new QueryClient();
  cache.setQueryData(["devolucao-da-locacao", locacaoId], d);
  cache.setQueryData(["devolucao", d.id], d);
  cache.setQueryData(["vistoria", d.vistoria.id], await vistorias.obter(d.vistoria.id));
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <Devolucao locacaoId={locacaoId} />
    </QueryClientProvider>,
  );
  return { html, t: html.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|") };
}

const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

describe("devolução da LOC-2836 (Juliana Rocha, Factor 150), gerente", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("vistoria, fotos e itens na ordem da referência, com o acerto do caso de referência ao lado", async () => {
    const { t, html } = await pagina(2836);
    ordem(t, ["Locações", "LOC-2836", "Devolução", "Juliana Rocha · Yamaha Factor 150 · PNB-7C04 · no horário", "1 · Vistoria", "2 · Acerto"]);
    ordem(t, ["Quilometragem e combustível", "Km na saída", "Km agora", "Rodou 1.228 km · plano com km livre", "Combustível agora · saiu com tanque cheio", "Reserva", "1/4", "1/2", "3/4", "Cheio"]);
    ordem(t, ["Fotos · saída × agora", "Tirar mais fotos", "Saída · 30 set", "Lateral esquerda", "Agora", "Painel e hodômetro"]);
    ordem(t, ["Itens conferidos", "Retrovisores", "Capacete extra", "Registrar avaria", "Observações"]);
    ordem(t, ["Acerto", "(faltou 1/4 tanque, 4 L × R$ 5,50 + R$ 10,00)", "R$ 32,00", "Retrovisor esquerdo", "R$ 85,00", "Atraso", "R$ 0,00", "Caução a devolver", "− R$ 300,00", "Devolver ao cliente", "R$ 183,00", "Desconta R$ 117,00 da caução de R$ 300,00"]);
    ordem(t, ["Concluir vistoria", "Salvar e continuar depois"]);
    expect(html).toContain('value="18.402"');
    expect(html).toContain('value="19.630"');
    expect(t).not.toContain("3 · Recibo");
  });

  it("a tela mostra o botão e o saldo que a API devolve, sem recalcular", async () => {
    const d = await vistorias.obterDevolucao(701);
    expect(d.acerto?.resultado).toMatchObject({ tipo: "devolver", valor_centavos: 18300, botao: "Encerrar e devolver R$ 183,00" });
    expect(d.acerto?.total_cobrancas_centavos).toBe(11700);
    expect(d.acerto?.saldo_centavos).toBe(18300);
  });

  it("vistoriador faz a vistoria e não vê o acerto nem valores", async () => {
    await entrarComo("joao@motorapida.com.br");
    const { t } = await pagina(2836);
    expect(t).toContain("Quilometragem e combustível");
    expect(t).not.toMatch(/R\$ \d/);
    expect(t).not.toContain("Acerto");
    expect(t).not.toContain("2 · Acerto");
  });
});
