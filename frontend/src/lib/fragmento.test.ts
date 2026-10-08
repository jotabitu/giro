import { describe, expect, it } from "vitest";
import { contas, ErroApi } from "@/lib/api";
import { consumirFragmento, tokenDoFragmento } from "./fragmento";

describe("token no fragmento da URL (T-072, P-09)", () => {
  it("lê o texto depois do #", () => {
    expect(tokenDoFragmento("#abc123")).toBe("abc123");
    expect(tokenDoFragmento("")).toBeNull();
    expect(tokenDoFragmento("#")).toBeNull();
  });

  it("devolve o token e apaga o fragmento do histórico, mantendo caminho e query", () => {
    const chamadas: unknown[][] = [];
    const historico = { replaceState: (...a: unknown[]) => void chamadas.push(a) };
    const token = consumirFragmento({ hash: "#link-valido", pathname: "/entrar/redefinir", search: "" }, historico);
    expect(token).toBe("link-valido");
    expect(chamadas).toEqual([[null, "", "/entrar/redefinir"]]);
  });

  it("sem fragmento não mexe no histórico", () => {
    const chamadas: unknown[][] = [];
    const token = consumirFragmento({ hash: "", pathname: "/convite", search: "" }, { replaceState: (...a: unknown[]) => void chamadas.push(a) });
    expect(token).toBeNull();
    expect(chamadas).toEqual([]);
  });
});

describe("dados falsos de convite e redefinição: token no corpo", () => {
  it("consulta o convite pelo corpo", async () => {
    expect((await contas.consultarConvite({ token: "convite-rodrigo" })).email).toBe("rodrigo@motorapida.com.br");
    await expect(contas.consultarConvite({ token: "nao-existe" })).rejects.toMatchObject({ status: 404 });
    await expect(contas.consultarConvite({ token: "convite-vencido" })).rejects.toMatchObject({ status: 410 });
  });

  it("aceita o convite com o token no corpo", async () => {
    const r = await contas.aceitarConvite({ token: "convite-rodrigo", nome: "Rodrigo Pinheiro", senha: "senhaforte123", aparelho: "desktop" });
    expect(r.etapa).toBe("pronto");
  });

  it("redefinir com token vencido responde 410 link_expirado", async () => {
    await expect(contas.redefinirSenha({ token: "outro", senha_nova: "senhaforte123" })).rejects.toBeInstanceOf(ErroApi);
    await expect(contas.redefinirSenha({ token: "link-valido", senha_nova: "senhaforte123" })).resolves.toBeUndefined();
  });
});
