// Agenda do vistoriador (T-022) contra docs/telas/html/Vistoriador-Desktop.dc.html e Vistoriador-Mobile.dc.html.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { contas, vistorias } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/vistorias", useSearchParams: () => new URLSearchParams() }));

import { AgendaDoVistoriador, rotaDoItemDaAgenda } from "./AgendaDoVistoriador";
import { AvariasAbertas } from "./AvariasAbertas";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

describe("agenda do vistoriador (João, Filial Centro)", () => {
  beforeAll(async () => {
    const r = await contas.entrar({ email: "joao@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") throw new Error("esperava pronto");
  });

  afterEach(() => vi.useRealTimers());

  it("tabela, próxima vistoria e abas na ordem da referência", async () => {
    // Hoje, no mundo do seed, é 07 out 2026 (a hora da agenda sai sem a data só no dia de hoje).
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-07T12:00:00Z"));
    const cache = new QueryClient();
    cache.setQueryData(["agenda", "hoje"], await vistorias.agenda("hoje"));
    cache.setQueryData(["agenda", "amanha"], await vistorias.agenda("amanha"));
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <AgendaDoVistoriador />
      </QueryClientProvider>,
    );
    const t = texto(html);
    ordem(t, ["Vistorias de hoje", "Quarta, 07 out · 1 saída e 1 devolução", "Hoje", "Amanhã", "Semana"]);
    ordem(t, ["Horário", "Tipo", "Veículo", "Cliente", "Situação", "12 set 09:00", "Devolução", "PQD-6E21", "Honda Pop 110i", "Rafael Sousa", "Atrasada", "Abrir", "09:30", "Saída", "SAK-1D39", "Honda CG 160 Fan", "Lucas Ferreira", "Em andamento", "Continuar"]);
    ordem(t, ["Próxima vistoria", "em 20 min", "Check-out às", "09:30", "Honda CG 160 Fan", "SAK-1D39", "Lucas Ferreira", "Continuar vistoria"]);
    ordem(t, ["Dica: a vistoria é mais rápida no celular, com as fotos tiradas direto pela câmera."]);
    // Celular: grupos de saídas e devoluções, com as contagens do dia na aba.
    ordem(t, ["Hoje · 2", "Amanhã · 0", "Saídas", "1 saída", "Devoluções", "1 devolução"]);
    expect(t).not.toMatch(/R\$ \d/);
  });

  it("cada item leva para a vistoria de saída ou para a devolução", () => {
    expect(rotaDoItemDaAgenda({ tipo: "saida", locacao: { id: 2856, codigo: "LOC-2856" } })).toBe("/locacoes/2856/vistoria");
    expect(rotaDoItemDaAgenda({ tipo: "devolucao", locacao: { id: 2790, codigo: "LOC-2790" } })).toBe("/locacoes/2790/devolucao");
  });

  it("avarias abertas: descrição, veículo, locação e oficina, sem valores", async () => {
    const cache = new QueryClient();
    cache.setQueryData(["avarias-abertas"], await vistorias.avarias());
    const t = texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <AvariasAbertas />
        </QueryClientProvider>,
      ),
    );
    ordem(t, ["Avarias abertas", "2 avarias ainda não reparadas", "Risco no tanque, lado esquerdo", "SAK-1D39", "LOC-2856", "registrada em 18 set", "Amassado no paralama dianteiro", "QXA-4B21", "Vai para a oficina"]);
    expect(t).not.toMatch(/R\$ \d/);
  });
});
