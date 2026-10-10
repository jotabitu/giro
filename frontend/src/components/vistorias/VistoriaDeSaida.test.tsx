// Vistoria de saída (T-022) contra docs/telas/html/Vistoria-Desktop.dc.html e Vistoria-Mobile.dc.html.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, vistorias } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes/2856/vistoria", useSearchParams: () => new URLSearchParams() }));

import { VistoriaDeSaida } from "./VistoriaDeSaida";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

async function pagina(locacaoId: number): Promise<{ html: string; t: string }> {
  const v = await vistorias.iniciarSaida(locacaoId);
  const cache = new QueryClient();
  cache.setQueryData(["vistoria-saida", locacaoId], v);
  cache.setQueryData(["vistoria", v.id], v);
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <VistoriaDeSaida locacaoId={locacaoId} />
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

describe("vistoria de saída da LOC-2856 (Lucas Ferreira, CG 160 Fan)", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));

  it("painel, fotos, itens e resumo na ordem da referência", async () => {
    const { t, html } = await pagina(2856);
    ordem(t, ["Locações", "LOC-2856", "Check-out da Honda CG 160 Fan", "1 · Dados", "2 · Vistoria", "3 · Assinatura"]);
    ordem(t, ["Painel", "Quilometragem na saída", "Última leitura: 3.118 km em 05 out", "Combustível", "Reserva", "1/4", "1/2", "3/4", "Cheio"]);
    ordem(t, ["Fotos", "3 de 5 obrigatórias", "Frente", "09:41", "Traseira", "09:41", "Lateral esquerda", "09:42", "Lateral direita", "Painel e hodômetro", "Foto de avaria"]);
    ordem(t, ["Itens conferidos", "Retrovisores", "Faróis, setas e buzina", "Pneus e freios", "Riscos ou amassados", "1 avaria", "Capacete entregue", "Documento (CRLV) no veículo"]);
    ordem(t, ["Risco no tanque, lado esquerdo.", "Registrado na vistoria anterior; não será cobrado do cliente na devolução.", "Registrar avaria", "Observações"]);
    ordem(t, ["Honda CG 160 Fan", "SAK-1D39 · 2025", "Cliente", "Lucas Ferreira", "CNH", "Categoria A · válida", "Período", "07 out a 14 out · semanal", "Franquia", "Km livre", "Caução"]);
    ordem(t, ["Continuar para assinatura", "Faltam 2 fotos obrigatórias", "Salvar e continuar depois"]);
    expect(html).toContain('value="3.120"');
    expect(html).toMatch(/<button[^>]*disabled[^>]*>Continuar para assinatura/);
    // 3/4 marcado, como na referência.
    expect(html).toMatch(/aria-pressed="true"[^>]*>(<span[^>]*>3\/4<\/span>)/);
  });

  it("vistoriador não vê o valor da caução nem da diária", async () => {
    await entrarComo("joao@motorapida.com.br");
    const { t } = await pagina(2856);
    expect(t).not.toMatch(/R\$ \d/);
    expect(t).not.toContain("Caução");
  });
});
