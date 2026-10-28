// Faixa do modo suporte (T-372) contra docs/telas/html/Modo-Suporte-*.dc.html e docs/api/contas.md, "Modo suporte" (PLT-07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, type Eu } from "@/lib/api";
import { ROTA_DEPOIS_DE_SAIR, rotulosDaFaixa } from "@/lib/suporte";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: () => {} }) }));

import { FaixaDoSuporte } from "./FaixaDoSuporte";

function faixa(): string {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>
      <FaixaDoSuporte />
    </QueryClientProvider>,
  );
}

describe("Faixa do modo suporte", () => {
  it("com eu.suporte mostra nome, Equipe Giro, motivo, permissão, fim e Sair do suporte", async () => {
    sessao.eu = await contas.entrarComoSuporte("suporte-valido");
    const h = faixa();
    expect(h).toContain("Modo suporte");
    expect(h).toContain("Diego Santos");
    expect(h).toContain("Equipe Giro");
    expect(h).toContain("Motivo: Chamado #1042");
    expect(h).toContain("Só ver");
    expect(h).toContain("Expira às 15:30");
    expect(h).toContain("Sair do suporte");
    expect(h).not.toMatch(/restam/i);
  });

  it("sem suporte (pessoa da empresa) não há faixa", async () => {
    await contas.sairDoSuporte();
    const r = await contas.entrar({ email: "mariana@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa === "verificar_2fa") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    sessao.eu = await contas.eu();
    expect(faixa()).toBe("");
  });

  it("rótulos prontos da API; sem eles, só o rótulo fixo da permissão e nenhum horário", async () => {
    const eu = await contas.entrarComoSuporte("suporte-valido");
    const s = eu.suporte!;
    expect(rotulosDaFaixa(s)).toEqual({ permissao: "Só ver", fim: "Expira às 15:30" });
    expect(rotulosDaFaixa({ ...s, permissao: "ver_editar", permissao_rotulo: undefined, fim_rotulo: undefined })).toEqual({ permissao: "Ver e editar", fim: null });
  });

  it("depois de sair, a página de entrada avisa que a saída foi pedida", () => {
    expect(ROTA_DEPOIS_DE_SAIR).toBe("/suporte/entrar?saiu=1");
  });

  it("token inválido ou de outra empresa responde 401 PLT-07 e não deixa sessão", async () => {
    await expect(contas.entrarComoSuporte("de-outra-empresa")).rejects.toMatchObject({ status: 401, codigo: "PLT-07" });
  });
});
