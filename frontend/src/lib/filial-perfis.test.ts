// Seletor de filial por perfil (USR-07, CA-023-05): Mariana e Lúcia escolhem "Todas as filiais"; Rodrigo e Bruna ficam na Filial Centro.
import { describe, expect, it } from "vitest";
import { contas, filiais } from "@/lib/api";
import { deveMostrar, montarItens } from "@/design-system/components/SeletorDeFilial/logica";
import { escolhaValida, TODAS } from "./filial";

async function seletorDe(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "verificar_2fa") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  else if (r.etapa === "configurar_2fa") {
    await contas.configurar2fa(r.token_pre_2fa);
    await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  }
  const minhas = await filiais.minhas();
  const opcoes = minhas.resultados.map((f) => ({ id: String(f.id), nome: f.nome_curto, cidade: f.cidade }));
  return { minhas, itens: montarItens(opcoes, minhas.pode_escolher_todas), mostra: deveMostrar(opcoes, minhas.pode_escolher_todas) };
}

describe("seletor de filial por perfil (USR-07)", () => {
  it.each(["mariana@motorapida.com.br", "financeiro@motorapida.com.br"])("%s vê as duas filiais e Todas as filiais", async (email) => {
    const s = await seletorDe(email);
    expect(s.mostra).toBe(true);
    expect(s.itens.map((i) => i.nome)).toEqual(["Todas as filiais", "Centro", "Filial Aldeota"]);
    expect(escolhaValida(s.minhas, TODAS)).toBe(TODAS);
    expect(escolhaValida(s.minhas, null)).toBe("1");
  });

  it.each(["rodrigo@motorapida.com.br", "bruna@motorapida.com.br"])("%s fica na Filial Centro, sem seletor e sem Todas", async (email) => {
    const s = await seletorDe(email);
    expect(s.mostra).toBe(false);
    expect(s.itens.map((i) => i.nome)).toEqual(["Centro"]);
    expect(escolhaValida(s.minhas, TODAS)).toBe("1");
  });
});
