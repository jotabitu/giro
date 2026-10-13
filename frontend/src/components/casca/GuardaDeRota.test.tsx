// Guarda de rota (D-26, USR-09): a rota que o menu do perfil não mostra responde "Seu perfil não tem acesso".
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, type Eu } from "@/lib/api";

const estado = vi.hoisted(() => ({ eu: null as unknown, rota: "/inicio" }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: estado.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ usePathname: () => estado.rota }));

import { GuardaDeRota } from "./CascaDoApp";

// O falso limita as entradas por minuto: cada perfil entra uma vez.
const perfis = new Map<string, Eu>();

async function em(email: string, rota: string): Promise<string> {
  if (!perfis.has(email)) {
    const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    perfis.set(email, await contas.eu());
  }
  estado.eu = perfis.get(email);
  estado.rota = rota;
  return renderToStaticMarkup(
    <GuardaDeRota>
      <p>conteúdo da tela</p>
    </GuardaDeRota>,
  );
}

const SEM_ACESSO = "Seu perfil não tem acesso";

describe("guarda de rota por perfil", () => {
  it.each(["/clientes", "/clientes/1201", "/financeiro/receber", "/locacoes", "/locacoes/nova", "/veiculos/novo"])("usr_09: vistoriador em %s vê só o aviso", async (rota) => {
    const h = await em("joao@motorapida.com.br", rota);
    expect(h).toContain(SEM_ACESSO);
    expect(h).not.toContain("conteúdo da tela");
  });

  it.each(["/inicio", "/veiculos", "/veiculos/501", "/vistorias", "/vistorias/avarias", "/locacoes/2856/vistoria"])("usr_09: vistoriador em %s abre a tela", async (rota) => {
    const h = await em("joao@motorapida.com.br", rota);
    expect(h).toContain("conteúdo da tela");
  });

  it.each(["/veiculos", "/locacoes", "/vistorias"])("usr_09: financeiro em %s vê só o aviso", async (rota) => {
    expect(await em("financeiro@motorapida.com.br", rota)).toContain(SEM_ACESSO);
  });

  it.each(["/clientes/1203", "/financeiro/receber", "/locacoes/2790"])("usr_09: financeiro em %s abre a tela", async (rota) => {
    expect(await em("financeiro@motorapida.com.br", rota)).toContain("conteúdo da tela");
  });

  it("usr_05: administrador abre as telas do menu completo", async () => {
    expect(await em("mariana@motorapida.com.br", "/veiculos/novo")).toContain("conteúdo da tela");
  });
});
