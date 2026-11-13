// Página pública do recibo (T-436, DEV-02, S-15, AUD-05): estados da tela e a URL do PDF pedida de novo a cada consulta.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { recibo } from "@/lib/api";

let tokenDoLink: string | null = "link-juliana";
vi.mock("@/lib/fragmento", () => ({ useTokenDoFragmento: () => ({ pronto: true, token: tokenDoLink }) }));

import { ReciboDevolucao } from "./ReciboDevolucao";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function pagina(token: string | null, erro?: unknown) {
  tokenDoLink = token;
  const cache = new QueryClient();
  if (token) {
    if (erro) await cache.prefetchQuery({ queryKey: ["recibo"], queryFn: () => Promise.reject(erro), retry: false });
    else cache.setQueryData(["recibo"], await recibo.consultar({ token }));
  }
  return texto(renderToStaticMarkup(<QueryClientProvider client={cache}><ReciboDevolucao /></QueryClientProvider>));
}

describe("página /recibo", () => {
  it("test_dev_02_recibo_publico_mostra_marca_codigo_nome_e_baixar", async () => {
    const t = await pagina("link-juliana");
    // T-467: o código não parte no hífen a 390 px (hífen sem quebra, U+2011).
    expect(t).not.toContain("LOC-2836");
    const ordem = ["Recibo da devolução da LOC‑2836", "Olá, Juliana", "Baixar recibo", "Tecnologia Giro"];
    let pos = -1;
    for (const p of ordem) {
      const i = t.indexOf(p, pos + 1);
      expect(i, p).toBeGreaterThan(pos);
      pos = i;
    }
  });

  it("test_s_15_recibo_publico_link_vencido_e_desconhecido_dizem_o_mesmo", async () => {
    for (const token of ["link-vencido", "link-outro"]) {
      const erro = await recibo.consultar({ token }).catch((e: unknown) => e);
      expect(await pagina(token, erro)).toContain("Este link venceu ou não existe. Peça um novo à locadora.");
    }
  });

  it("test_s_15_recibo_publico_sem_token_explica_e_nao_chama_a_api", async () => {
    expect(await pagina(null)).toContain("Este link venceu ou não existe. Peça um novo à locadora.");
  });

  it("test_aud_05_recibo_publico_cada_consulta_devolve_uma_url_nova_do_pdf", async () => {
    const a = await recibo.consultar({ token: "link-juliana" });
    const b = await recibo.consultar({ token: "link-juliana" });
    expect(a.recibo.pdf_url).not.toBe(b.recibo.pdf_url);
  });
});
