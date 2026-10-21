// Administração › Configurações (T-182) contra docs/telas/html/Config-*.dc.html e docs/api/configuracoes.md (USR-05, IMP-01).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { configuracoes, contas, type Configuracoes as Resumo, type Eu } from "@/lib/api";
import { destinoDaAcao } from "@/lib/configuracoes";
import { IMPLANTANDO } from "@/testes/falsos/falso-configuracoes";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { Configuracoes } from "./Configuracoes";

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

async function tela(resumo?: Resumo): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["configuracoes"], resumo ?? (await configuracoes.resumo()));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <Configuracoes />
    </QueryClientProvider>,
  );
}

describe("Configurações", () => {
  it("seed: 9 cartões na ordem da API, com título, resumo e link, e sem faixa de implantação", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = await tela();
    expect(h.match(/<li/g)).toHaveLength(9);
    const ordem = ["Empresa e marca", "O que a empresa faz", "Filiais", "Usuários e perfis", "Tabelas de preço", "Modelos de contrato", "Assinatura", "Auditoria", "Exportar dados"].map((t) => h.indexOf(t));
    expect([...ordem].sort((a, b) => a - b)).toEqual(ordem);
    expect(h).toContain("5 de 10 usuários");
    expect(h).toContain("1 filial · Centro, Fortaleza");
    expect(h).toContain("Locação e venda · motos");
    expect(h).toContain("Profissional · teste até 21 out");
    for (const href of ["/admin/marca", "/admin/ramo", "/admin/filiais", "/admin/usuarios", "/admin/precos", "/admin/contratos", "/admin/assinatura", "/admin/auditoria", "/admin/exportar"]) expect(h).toContain(`href="${href}"`);
    expect(h).not.toContain("Implantação concluída");
    expect(h).not.toContain("Integrações");
  });

  it("cartão que a API não manda não aparece", async () => {
    await entrar("mariana@motorapida.com.br");
    const base = await configuracoes.resumo();
    const h = await tela({ ...base, cartoes: base.cartoes.filter((c) => c.chave !== "auditoria" && c.chave !== "exportar") });
    expect(h.match(/<li/g)).toHaveLength(7);
    expect(h).not.toContain("Quem fez o quê");
  });

  it("faixa com 6 de 10 passos, só no desktop e sem botão quando acao é null", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = await tela({ ...(await configuracoes.resumo()), implantacao: IMPLANTANDO });
    expect(h).toContain("Implantação concluída em 6 de 10 passos");
    expect(h).toContain("Faltam contrato, recebimentos, importar dados e a 1ª locação.");
    expect(h).toMatch(/<section[^>]*class="[^"]*\bhidden\b[^"]*\bmd:flex\b/);
    expect(h).not.toContain("Continuar implantação");
    expect(h).not.toContain("Fazer uma locação de teste");
  });

  it("acao nova_locacao mostra o botão e leva a /locacoes/nova", async () => {
    await entrar("mariana@motorapida.com.br");
    const acao = { rotulo: "Fazer uma locação de teste", destino: "nova_locacao" } as const;
    const h = await tela({ ...(await configuracoes.resumo()), implantacao: { ...IMPLANTANDO, concluidos: 9, titulo: "Implantação concluída em 9 de 10 passos", faltam: "Falta a 1ª locação.", acao } });
    expect(h).toContain("Fazer uma locação de teste");
    expect(h).toContain('href="/locacoes/nova"');
    expect(destinoDaAcao(acao)).toBe("/locacoes/nova");
  });

  it("quem não é administrador vê o aviso e nenhum cartão", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const h = await tela();
    expect(h).toContain("Só o administrador acessa Configurações.");
    expect(h).not.toContain("<li");
  });
});
