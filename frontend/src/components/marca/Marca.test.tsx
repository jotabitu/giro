// Empresa e marca (T-154) contra docs/telas/html/Admin-Marca-*.dc.html, Onboarding-Marca-*.dc.html e docs/api/empresas.md.
// A prévia usa só o que a API devolve (a fixture de src/testes/falsos/falso.ts repete a tabela das seis cores do contrato).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, ErroApi, marca, type Eu } from "@/lib/api";
import { ACEITA_LOGO, AJUDA_DO_LOGO, corCompleta, corpoDaSimulacao, corpoDoSalvar, CORES_DO_ASSISTENTE, edicaoInicial, logoVisivel, mudou, normalizarCor } from "@/lib/marca-edicao";
import { rotaPermitida } from "@/lib/menu";
import { MARCA_FALSA } from "@/testes/falsos/falso";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { AdminMarca } from "../admin/AdminMarca";
import { PassoMarca } from "../implantacao/PassoMarca";
import { EscolhaDaCor } from "./EscolhaDaCor";
import { EscolhaDoLogo } from "./EscolhaDoLogo";
import { PreviaDaMarca } from "./PreviaDaMarca";

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

function comCache(tela: React.ReactNode): string {
  const cache = new QueryClient();
  cache.setQueryData(["marca"], MARCA_FALSA);
  return renderToStaticMarkup(<QueryClientProvider client={cache}>{tela}</QueryClientProvider>);
}

describe("PreviaDaMarca", () => {
  it("#2F6FED: o texto sobre a cor e a cor suave vêm da API, sem conta no frontend", async () => {
    const simulada = await marca.simular({ cor: "#2f6fed" });
    expect(simulada.cor).toBe("#2F6FED");
    expect(simulada.cor_sobre).toBe("#FFFFFF");
    expect(simulada.cor_suave).toBe("#DBF3FF");
    const h = renderToStaticMarkup(<PreviaDaMarca marca={simulada} logoUrl={null} />);
    expect(h).toContain("--brand:#2F6FED");
    expect(h).toContain("--on-brand:#FFFFFF");
    expect(h).toContain("--brand-soft:#DBF3FF");
    expect(h).toContain(">Entrar<");
  });

  it("o logo ainda não salvo aparece por <img> (URL local), nunca inline", () => {
    const h = renderToStaticMarkup(<PreviaDaMarca marca={{ ...MARCA_FALSA }} logoUrl="blob:http://motorapida.localhost:3000/abc" />);
    expect(h).toContain('<img src="blob:http://motorapida.localhost:3000/abc"');
    expect(h).not.toContain("<svg");
    expect(h).not.toContain(">MR<");
  });

  it("sem logo mostra as iniciais que a API entregou", () => {
    const h = renderToStaticMarkup(<PreviaDaMarca marca={MARCA_FALSA} logoUrl={null} />);
    expect(h).toContain(">MR<");
    expect(h).not.toContain("<img");
  });

  it("valor que não é #RRGGBB não vira variável de CSS", () => {
    const h = renderToStaticMarkup(<PreviaDaMarca marca={{ ...MARCA_FALSA, cor: "red; background: url(x)" }} logoUrl={null} />);
    expect(h).not.toContain("--brand");
  });
});

describe("EscolhaDoLogo", () => {
  const base = { iniciais: "MR", aoEscolher: () => {}, aoRemover: () => {} };

  it("Admin: Trocar logo, a ajuda e o seletor só de PNG e SVG; Remover só com logo", () => {
    const com = renderToStaticMarkup(<EscolhaDoLogo {...base} variante="admin" logoUrl="/api/marca/logo/?v=5c1e9a2b" />);
    expect(com).toContain("Trocar logo");
    expect(com).toContain("Remover");
    expect(com).toContain(AJUDA_DO_LOGO);
    expect(com).toContain('accept="image/png,image/svg+xml,.png,.svg"');
    expect(ACEITA_LOGO).toBe("image/png,image/svg+xml,.png,.svg");
    expect(com).toContain('<img src="/api/marca/logo/?v=5c1e9a2b"');
  });

  it("depois de Remover (sem logo visível) volta às iniciais e o botão some", () => {
    const e = { ...edicaoInicial(MARCA_FALSA), logo: { tipo: "removido" as const } };
    expect(logoVisivel({ logo: { url: "/api/marca/logo/?v=1", largura: 1, altura: 1 } }, e.logo, null)).toBeNull();
    const h = renderToStaticMarkup(<EscolhaDoLogo {...base} variante="admin" logoUrl={null} />);
    expect(h).not.toContain("Remover");
    expect(h).toContain(">MR<");
    expect(h).not.toContain("<img");
  });

  it("assistente: Enviar logo e a frase das iniciais; a mensagem da API troca a dica", () => {
    const h = renderToStaticMarkup(<EscolhaDoLogo {...base} variante="assistente" logoUrl={null} erro="O logo passa de 2 MB." />);
    expect(h).toContain("Enviar logo");
    expect(h).toContain("O logo passa de 2 MB.");
    expect(h).not.toContain("Sem logo, usamos as iniciais");
    expect(renderToStaticMarkup(<EscolhaDoLogo {...base} variante="assistente" logoUrl={null} />)).toContain("Sem logo, usamos as iniciais.");
  });
});

describe("EscolhaDaCor", () => {
  it("marca a cor escolhida e mostra a mensagem 400 da API no campo", () => {
    const h = renderToStaticMarkup(<EscolhaDaCor rotulo="Cor principal" cores={CORES_DO_ASSISTENTE} atual="#2f6fed" digitavel aoEscolher={() => {}} aoDigitar={() => {}} erro="Use uma cor no formato #RRGGBB." dica="Dica" />);
    expect(h).toMatch(/aria-label="Azul"[^>]*aria-pressed="true"|aria-pressed="true"[^>]*aria-label="Azul"/);
    expect(h.match(/aria-pressed="true"/g)).toHaveLength(1);
    expect(h).toContain("Use uma cor no formato #RRGGBB.");
    expect(h).toContain("#2F6FED");
  });

  it("o erro da simulação é o que a API respondeu", async () => {
    const erro = await marca.simular({ cor: "azul" }).catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect((erro as ErroApi).status).toBe(400);
    expect((erro as ErroApi).campos?.cor).toBe("Use uma cor no formato #RRGGBB.");
  });
});

describe("edição da marca", () => {
  it("o PATCH leva só o que mudou", () => {
    const e = edicaoInicial(MARCA_FALSA);
    expect(corpoDoSalvar(MARCA_FALSA, e)).toEqual({});
    expect(mudou(MARCA_FALSA, e)).toBe(false);
    expect(corpoDoSalvar(MARCA_FALSA, { ...e, cor: "2f6fed" })).toEqual({ cor: "#2f6fed" });
    expect(corpoDoSalvar(MARCA_FALSA, { ...e, cor: "#c8f04a" })).toEqual({});
    expect(corpoDoSalvar(MARCA_FALSA, { ...e, nome: "  Moto Veloz " })).toEqual({ nome_exibicao: "Moto Veloz" });
    expect(corpoDoSalvar(MARCA_FALSA, { ...e, logo: { tipo: "removido" } })).toEqual({ remover_logo: true });
    const arquivo = new Blob(["<svg/>"], { type: "image/svg+xml" }) as File;
    expect(corpoDoSalvar(MARCA_FALSA, { ...e, logo: { tipo: "novo", arquivo } })).toEqual({ logo: arquivo });
    expect(mudou(MARCA_FALSA, { ...e, logo: { tipo: "removido" } })).toBe(true);
  });

  it("a simulação só sai com a cor inteira (vazio volta à padrão)", () => {
    expect(corpoDaSimulacao({ nome: "Moto Rápida", cor: "#2F6F" })).toBeNull();
    expect(corpoDaSimulacao({ nome: "Moto Rápida", cor: "2F6FED" })).toEqual({ cor: "#2F6FED", nome_exibicao: "Moto Rápida" });
    expect(corpoDaSimulacao({ nome: "", cor: "" })).toEqual({ cor: "", nome_exibicao: "" });
    expect(corCompleta("#12345G")).toBe(false);
    expect(normalizarCor(" 2f6fed ")).toBe("#2f6fed");
  });

  it("salvar devolve o corpo de GET /api/marca/ com a versão nova", async () => {
    const nova = await marca.salvar({ cor: "#2F6FED" });
    expect(nova.cor).toBe("#2F6FED");
    expect(nova.cor_sobre).toBe("#FFFFFF");
    expect(nova.versao).not.toBe(MARCA_FALSA.versao);
    expect(nova.personalizada).toBe(true);
  });
});

describe("Empresa e marca", () => {
  it("bloco Marca e Prévia, sem Dados da empresa nem Endereço do sistema", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<AdminMarca />);
    expect(h).toContain("Empresa e marca");
    expect(h).toContain("Logo");
    expect(h).toContain("Cor principal");
    expect(h).toContain("Nome que aparece para clientes");
    expect(h).toContain("Prévia");
    expect(h).toContain("Usada nos botões e destaques.");
    expect(h).not.toContain("Dados da empresa");
    expect(h).not.toContain("Endereço do sistema");
    expect(h).not.toContain("Marca salva.");
    expect(h).toMatch(/<button[^>]*disabled=""[^>]*>Salvar<\/button>/);
  });

  it("a rota /admin/marca é só do administrador", async () => {
    await entrar("mariana@motorapida.com.br");
    expect(rotaPermitida(sessao.eu as Eu, "/admin/marca")).toBe(true);
    await entrar("rodrigo@motorapida.com.br");
    expect(rotaPermitida(sessao.eu as Eu, "/admin/marca")).toBe(false);
    expect(comCache(<AdminMarca />)).toContain("Só o administrador muda a marca.");
  });
});

describe("Passo Marca do assistente", () => {
  it("só Logo e Cor de destaque, com as seis cores, Pular por agora e Continuar", () => {
    const h = comCache(<PassoMarca guardada={MARCA_FALSA} aoContinuar={() => {}} aoPular={() => {}} />);
    expect(h).toContain("Sua empresa e sua marca");
    expect(h).toContain("Cor de destaque");
    for (const c of CORES_DO_ASSISTENTE) expect(h).toContain(`aria-label="${c.rotulo}"`);
    expect(h.match(/aria-pressed=/g)).toHaveLength(6);
    expect(h).toContain("Enviar logo");
    expect(h).toContain("Pular por agora");
    expect(h).toContain(">Continuar<");
    expect(h).toContain("Pré-visualização");
    expect(h).not.toContain("CNPJ");
    expect(h).not.toContain("Razão social");
  });
});
