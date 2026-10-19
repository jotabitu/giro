// Administração › O que a empresa faz (T-262) contra docs/telas/html/Admin-Ramo-*.dc.html e docs/api/empresas.md (PLT-12).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, ErroApi, type Eu, type Ramo } from "@/lib/api";
import { podeAlternar, corpoDoRamo, marcasDoRamo, ramoMudou, recusaDoRamo } from "@/lib/ramo";
import { RAMO_ESSENCIAL, RAMO_PROFISSIONAL } from "@/testes/falsos/falso-ramo";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { rotaPermitida } from "@/lib/menu";
import { AdminRamo } from "./AdminRamo";

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

function tela(ramo: Ramo): string {
  const cache = new QueryClient();
  cache.setQueryData(["ramo"], ramo);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <AdminRamo />
    </QueryClientProvider>,
  );
}

describe("AdminRamo", () => {
  it("Profissional: as duas atividades marcadas, os módulos da API e o aviso dos dados", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = tela(RAMO_PROFISSIONAL);
    expect(h).toContain("O que a empresa faz");
    expect(h).toContain("Locação");
    expect(h).toContain("Venda de veículos");
    expect(h.match(/aria-pressed="true"/g)).toHaveLength(3); // Locação, Venda e Motos
    expect(h).toContain("6 módulos no seu plano");
    expect(h).toContain("Vendas e comissões");
    expect(h).toContain("Nada é apagado.");
    expect(h).not.toContain("Vendas faz parte do plano Profissional.");
    expect(h).not.toContain("Ramo salvo.");
  });

  it("Essencial: o aviso e a lista de módulos são os da API, e Locação fica travada", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = tela(RAMO_ESSENCIAL);
    expect(h).toContain("Vendas faz parte do plano Profissional.");
    expect(h).toContain("3 módulos no seu plano");
    expect(h).not.toContain("Vendas e comissões");
    expect(h).toMatch(/aria-pressed="true"[^>]*aria-disabled="true"/);
  });

  it("sem alteração o Salvar fica desligado", async () => {
    await entrar("mariana@motorapida.com.br");
    expect(tela(RAMO_PROFISSIONAL)).toMatch(/<button[^>]*disabled=""[^>]*>Salvar<\/button>/);
  });

  it("a rota /admin/ramo é só do administrador", async () => {
    await entrar("mariana@motorapida.com.br");
    expect(rotaPermitida(sessao.eu as Eu, "/admin/ramo")).toBe(true);
    await entrar("rodrigo@motorapida.com.br");
    expect(rotaPermitida(sessao.eu as Eu, "/admin/ramo")).toBe(false);
  });

  it("quem não é administrador vê o aviso e nenhuma opção", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const h = tela(RAMO_PROFISSIONAL);
    expect(h).toContain("Só o administrador troca o ramo.");
    expect(h).not.toContain("aria-pressed");
  });
});

describe("regras de interface do ramo", () => {
  it("transforma as marcas no corpo do PUT e só aceita ao menos uma de cada grupo", () => {
    expect(corpoDoRamo(marcasDoRamo({ atividade: "ambos", trabalha_com: "motos" }))).toEqual({ atividade: "ambos", trabalha_com: "motos" });
    expect(corpoDoRamo({ locacao: false, venda: false, motos: true, carros: false })).toBeNull();
    expect(corpoDoRamo({ locacao: true, venda: false, motos: true, carros: true })).toEqual({ atividade: "aluga", trabalha_com: "ambos" });
  });

  it("ramoMudou compara com o guardado", () => {
    const g = { atividade: "ambos", trabalha_com: "motos" } as const;
    expect(ramoMudou(g, marcasDoRamo(g))).toBe(false);
    expect(ramoMudou(g, { ...marcasDoRamo(g), carros: true })).toBe(true);
  });

  it("podeAlternar segue atividades_aceitas e mantém uma opção de cada grupo (PLT-12)", () => {
    const essencial = marcasDoRamo({ atividade: "aluga", trabalha_com: "motos" });
    expect(podeAlternar(RAMO_ESSENCIAL, essencial, "locacao")).toBe(false); // sobraria só vende, que o plano não aceita
    expect(podeAlternar(RAMO_ESSENCIAL, essencial, "venda")).toBe(true); // vira ambos
    expect(podeAlternar(RAMO_ESSENCIAL, essencial, "motos")).toBe(false); // sobraria nenhum tipo
    const pro = marcasDoRamo({ atividade: "ambos", trabalha_com: "motos" });
    expect(podeAlternar(RAMO_PROFISSIONAL, pro, "locacao")).toBe(true);
  });

  it("recusaDoRamo mostra a mensagem da API e leva à lista do módulo que a API apontou", () => {
    const abertos = new ErroApi(422, "PLT-12", "Para deixar de alugar, resolva o que está aberto: 51 locações abertas.", { motivo: "abertos", recurso: "locacoes_vistoria" });
    expect(recusaDoRamo(abertos)).toEqual({ mensagem: abertos.message, motivo: "abertos", link: { href: "/locacoes", rotulo: "Ver locações abertas" } });
    const plano = new ErroApi(422, "PLT-12", "O plano Essencial não inclui vendas. Escolha locação, ou locação e venda.", { motivo: "plano" });
    expect(recusaDoRamo(plano)?.link).toBeNull();
    expect(recusaDoRamo(new ErroApi(403, "permissao", "Sem permissão."))).toBeNull();
    expect(recusaDoRamo(new Error("x"))).toBeNull();
  });
});
