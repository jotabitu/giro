import { describe, expect, it } from "vitest";
import { contas } from "@/lib/api";
import { montarMenu } from "./menu";

async function podeDe(email: string, aparelho = "desktop" as const) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho });
  if (r.etapa === "pronto") return r.usuario.pode;
  const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  if (v.etapa !== "pronto") throw new Error("esperava pronto");
  return v.usuario.pode;
}

const rotulos = (g: ReturnType<typeof montarMenu>) => g.flatMap((x) => x.itens.map((i) => i.rotulo));

describe("montarMenu (USR-05)", () => {
  it("administrador vê Administração", async () => {
    const menu = montarMenu(await podeDe("mariana@motorapida.com.br"), "/inicio");
    expect(menu.map((g) => g.rotulo)).toEqual([undefined, "Operação", "Financeiro", "Administração"]);
    expect(rotulos(menu)).toContain("Usuários");
  });

  it("gerente não vê Administração nem itens sem permissão", async () => {
    const menu = montarMenu(await podeDe("rodrigo@motorapida.com.br"), "/inicio");
    expect(menu.some((g) => g.rotulo === "Administração")).toBe(false);
    expect(rotulos(menu)).not.toContain("Comissões");
    expect(rotulos(menu)).toContain("Locações");
  });

  it("financeiro não vê Veículos nem Locações", async () => {
    const itens = rotulos(montarMenu(await podeDe("financeiro@motorapida.com.br"), "/inicio"));
    expect(itens).not.toContain("Veículos");
    expect(itens).not.toContain("Locações");
    expect(itens).toContain("Conciliação");
  });

  it("marca o item ativo e leva o contador da API", async () => {
    const menu = montarMenu(await podeDe("mariana@motorapida.com.br"), "/veiculos", { veiculos: 86 });
    const v = menu.flatMap((g) => g.itens).find((i) => i.chave === "veiculos");
    expect(v?.ativo).toBe(true);
    expect(v?.total).toBe(86);
  });
});
