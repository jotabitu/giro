// Página pública de assinatura (T-208, S-15): estados da tela e as regras da API falsa (nome conferido, link vencido, uso único).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { assinar, ErroApi } from "@/lib/api";

let tokenDoLink: string | null = "link-lucas";
vi.mock("@/lib/fragmento", () => ({ useTokenDoFragmento: () => ({ pronto: true, token: tokenDoLink }) }));

import { AssinarContrato } from "./AssinarContrato";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function pagina(token: string | null, erro?: unknown) {
  tokenDoLink = token;
  const cache = new QueryClient();
  if (token) {
    if (erro) await cache.prefetchQuery({ queryKey: ["assinar"], queryFn: () => Promise.reject(erro), retry: false });
    else cache.setQueryData(["assinar"], await assinar.consultar({ token }));
  }
  return texto(renderToStaticMarkup(<QueryClientProvider client={cache}><AssinarContrato /></QueryClientProvider>));
}

describe("página /assinar", () => {
  it("mostra o contrato, o PDF, o nome completo e o aceite, nessa ordem", async () => {
    const t = await pagina("link-lucas");
    const ordem = ["Contrato de locação semanal", "LOC-2856", "Para Lucas Ferreira", "Ler o contrato (PDF)", "Nome completo", "Li o contrato e concordo com os termos.", "Assinar contrato", "Tecnologia Giro"];
    let pos = -1;
    for (const p of ordem) {
      const i = t.indexOf(p, pos + 1);
      expect(i, p).toBeGreaterThan(pos);
      pos = i;
    }
  });

  it("link sem token explica e não chama a API", async () => {
    expect(await pagina(null)).toContain("Este link não tem o contrato");
  });

  it("link vencido e contrato já assinado têm título e texto próprios", async () => {
    const vencido = await assinar.consultar({ token: "link-vencido" }).catch((e: unknown) => e);
    expect(await pagina("link-vencido", vencido)).toContain("Link vencido");
    const feito = await assinar.consultar({ token: "link-assinado" }).catch((e: unknown) => e);
    const t = await pagina("link-assinado", feito);
    expect(t).toContain("Contrato já assinado");
  });
});

describe("assinar pelo link: regras da API", () => {
  it("nome que não confere é recusado no campo; aceite é obrigatório", async () => {
    await expect(assinar.assinar({ token: "link-lucas", aceite: true, nome_completo: "Lucas Silva" })).rejects.toMatchObject({ status: 400, codigo: "nome_nao_confere", campos: { nome_completo: expect.any(String) } });
    await expect(assinar.assinar({ token: "link-lucas", aceite: false, nome_completo: "Lucas Ferreira" })).rejects.toMatchObject({ status: 400, campos: { aceite: expect.any(String) } });
  });

  it("assina sem diferenciar maiúsculas e acentos, e o link não vale uma segunda vez (uso único)", async () => {
    const r = await assinar.assinar({ token: "link-lucas", aceite: true, nome_completo: "  LUCAS  ferreira " });
    expect(r.status).toBe("assinado");
    const de_novo = await assinar.consultar({ token: "link-lucas" }).catch((e: unknown) => e);
    expect(de_novo).toBeInstanceOf(ErroApi);
    expect(de_novo).toMatchObject({ status: 410, codigo: "contrato_ja_assinado" });
  });
});
