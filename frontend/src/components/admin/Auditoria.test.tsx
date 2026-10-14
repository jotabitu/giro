// Administração › Auditoria e Exportar dados (T-171) contra docs/telas/html/Admin-Auditoria-*.dc.html e Admin-Exportar-*.dc.html (AUD-01 a AUD-04, AUD-07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { auditoria, contas, type Eu } from "@/lib/api";
import { auditoriaApi } from "@/lib/api/auditoria";
import { arquivoDaExportacao, esteAno, filtroDaPessoa, tomDoEvento, valorDaPessoa } from "@/lib/auditoria";
import { rotaPermitida } from "@/lib/menu";
import { reiniciarAuditoriaFalso } from "@/testes/falsos/falso-auditoria";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/admin/auditoria", useSearchParams: () => new URLSearchParams() }));

import { ExportarDados } from "./ExportarDados";
import { ListaAuditoria } from "./ListaAuditoria";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

async function paginaAuditoria(): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["auditoria", "eventos", { aba: "tudo", periodo: "7d", pessoa: null, cursor: undefined }], await auditoria.eventos({ periodo: "7d" }));
  cache.setQueryData(["auditoria", "pessoas", "7d"], await auditoria.pessoas("7d"));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaAuditoria />
    </QueryClientProvider>,
  );
}

async function paginaExportar(): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["auditoria", "exportacoes"], await auditoria.exportacoes());
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ExportarDados />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-07T18:00:00Z"));
  reiniciarAuditoriaFalso();
});
afterEach(() => vi.useRealTimers());

describe("auditoria (Admin-Auditoria)", () => {
  it("cabeçalho, aviso do suporte, filtros e colunas da referência", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await paginaAuditoria());
    for (const trecho of ["Administração", "Auditoria", "Tudo que cada pessoa fez no sistema · guardado por 5 anos · ninguém consegue apagar", "Exportar", "A equipe do Giro só entra na sua conta com um chamado aberto", "Tudo", "Financeiro", "Operação", "Configurações", "Segurança", "Suporte", "Pessoa: todas", "Últimos 7 dias", "Quando", "Quem", "O que", "Detalhe"]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("os dez eventos do seed, do suporte de Diego até a mudança de preço", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await paginaAuditoria());
    const ordem = ["Diego Santos saiu do modo suporte", "Diego Santos entrou como suporte", "Lançou despesa de R$ 48,00", "Fez sangria de R$ 500,00", "Criou a locação LOC-2856", "Pediu despesa de R$ 1.200,00", "Login bloqueado", "Abriu o caixa", "Convidou João Silva", "Mudou a tabela de preço"];
    let pos = -1;
    for (const o of ordem) {
      const i = t.indexOf(o, pos + 1);
      expect(i, o).toBeGreaterThan(pos);
      pos = i;
    }
    for (const trecho of ["07 out, 13:52", "07 out, 13:40", "07 out, 11:20", "Duração 12 min · só ver · nenhuma alteração", "Chamado #1042 · você foi avisada por e-mail", "Óleo · QXA-4B21 · pago no caixa", "Caixa da Filial Centro", "Lucas Ferreira · Honda CG 160 Fan", "5 senhas erradas para rodrigo@motorapida.com.br", "Troco de R$ 200,00", "Perfil vistoriador · Filial Centro", "Street 150–160 · semanal R$ 299,40 → R$ 329,00", "Suporte Giro", "Sistema", "Bruna Alves", "Mariana Costa", "João Silva"]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("linha de suporte destacada, bloqueio em crítico e mudanças em info (AUD-03)", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await paginaAuditoria();
    expect(html.match(/!bg-warning-soft/g)?.length).toBe(2);
    expect(html).toContain("wl-badge--warning");
    expect(html).toContain("wl-badge--critical");
    expect(html).toContain("wl-badge--info");
  });

  it("celular: chips Tudo, Financeiro, Segurança e Suporte, e cada evento com quem e quando", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await paginaAuditoria());
    expect(t).toContain("Bruna Alves · 07 out, 11:20");
    expect(t).toContain("Suporte Giro · 07 out, 13:52");
    expect(t).toContain("Sistema · 07 out, 08:02");
  });

  it("só o administrador consulta (AUD-02)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(await paginaAuditoria());
    expect(t).toContain("Só o administrador acessa a Auditoria.");
    expect(t).not.toContain("Fez sangria");
  });
});

describe("filtros na API falsa (CA-018-10)", () => {
  it("categoria, pessoa e período combinam", async () => {
    expect((await auditoria.eventos({ categoria: "financeiro" })).resultados).toHaveLength(4);
    expect((await auditoria.eventos({ categoria: "suporte" })).resultados).toHaveLength(2);
    expect((await auditoria.eventos({ ator: 4 })).resultados).toHaveLength(4);
    expect((await auditoria.eventos({ ator: 4, categoria: "operacao" })).resultados).toHaveLength(1);
    expect((await auditoria.eventos({ ator_tipo: "sistema" })).resultados).toHaveLength(1);
  });

  it("o detalhe traz antes, depois, IP e aparelho", async () => {
    const e = await auditoria.evento(50200);
    expect(e.antes).toEqual({ semanal_centavos: 29940 });
    expect(e.depois).toEqual({ semanal_centavos: 32900 });
    expect(e.ip).toBeTruthy();
  });
});

describe("exportar dados (Admin-Exportar)", () => {
  it("MVP: só a auditoria em CSV, o período e o botão, sem backup nem outros itens", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await paginaExportar());
    for (const trecho of ["Exportar dados", "Os dados são da sua empresa. Baixe quando quiser, inclusive se for cancelar.", "O que exportar", "Auditoria", "Período", "Tudo", "Este ano", "Escolher", "Gerar arquivo", "Fica pronto em alguns minutos. Avisamos por e-mail com um link válido por 7 dias."]) {
      expect(t, trecho).toContain(trecho);
    }
    for (const fora of ["Clientes", "Veículos", "Financeiro", "Vistorias e fotos", "Backup automático", "Backup completo", "Planilha (.xlsx)"]) expect(t, fora).not.toContain(fora);
  });

  it("exportações recentes com situação e baixar só quando pronta", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await paginaExportar());
    expect(t).toContain("Exportações recentes");
    expect(t).toContain("Quando|Quem|Conteúdo|Arquivo|Situação");
    expect(t).toContain("Auditoria · 01/09/2026 a 30/09/2026");
    expect(t).toContain("CSV · 184,3 KB");
    expect(t).toContain("Pronto");
    expect(t).toContain("Expirado");
    expect(t.match(/Baixar/g)?.length).toBe(2);
  });

  it("só o administrador exporta", async () => {
    await entrar("financeiro@motorapida.com.br");
    expect(texto(await paginaExportar())).toContain("Só o administrador exporta dados.");
  });

  it("pedir cria uma exportação na fila e outro item é recusado (exportacao_indisponivel)", async () => {
    const r = await auditoria.exportar({ itens: ["auditoria"], formato: "csv", periodo: { de: "2026-10-01", ate: "2026-10-07" } });
    expect(r.status).toBe("na_fila");
    expect((await auditoria.exportacoes())[0]).toMatchObject({ conteudo: "Auditoria · 01/10/2026 a 07/10/2026", status: "na_fila" });
    await expect(auditoria.exportar({ itens: ["auditoria", "clientes"], formato: "csv", periodo: null } as never)).rejects.toMatchObject({ codigo: "exportacao_indisponivel" });
  });

  it("baixar entrega o arquivo e o expirado responde 410", async () => {
    expect((await auditoria.baixar(16)).type).toBe("text/csv");
    await expect(auditoria.baixar(12)).rejects.toMatchObject({ status: 410 });
  });

  it("o cliente HTTP baixa com o login e devolve o conteúdo como arquivo", async () => {
    const fetchMock = vi.fn(async () => new Response("a,b\n", { status: 200, headers: { "content-type": "text/csv" } }));
    vi.stubGlobal("fetch", fetchMock);
    try {
      const blob = await auditoriaApi.baixar(16);
      expect(await blob.text()).toBe("a,b\n");
      const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
      expect(url).toBe("/api/exportacoes/16/baixar/");
      expect(init.method).toBe("GET");
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

describe("apoio e rotas", () => {
  it("o pedido manda sempre auditoria e csv", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 1, status: "na_fila" }), { status: 202, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    try {
      await auditoriaApi.exportar({ itens: ["auditoria"], formato: "csv", periodo: null });
      const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
      expect(JSON.parse(init.body as string)).toEqual({ itens: ["auditoria"], formato: "csv", periodo: null });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("filtro de pessoa vai e volta da URL; tom por evento", () => {
    expect(valorDaPessoa({ tipo: "usuario", id: 4 })).toBe("usuario:4");
    expect(valorDaPessoa({ tipo: "sistema", id: null })).toBe("sistema");
    expect(filtroDaPessoa("usuario:4")).toEqual({ ator: 4 });
    expect(filtroDaPessoa("suporte")).toEqual({ ator_tipo: "suporte" });
    expect(filtroDaPessoa(null)).toEqual({});
    expect(tomDoEvento({ categoria: "seguranca", suporte: null, regra: "USR-06" })).toBe("critico");
    expect(tomDoEvento({ categoria: "financeiro", suporte: null, regra: null })).toBeNull();
  });

  it("tamanho do arquivo e período de 'Este ano'", () => {
    expect(arquivoDaExportacao("csv", 184320)).toBe("CSV · 184,3 KB");
    expect(arquivoDaExportacao("zip", 1_800_000_000)).toBe("ZIP · 1,8 GB");
    expect(arquivoDaExportacao("csv", null)).toBe("CSV");
    expect(esteAno("2026-10-07")).toEqual({ de: "2026-01-01", ate: "2026-10-07" });
  });

  it("Exportar abre para quem tem a Auditoria no menu (administrador), não para os outros", async () => {
    await entrar("mariana@motorapida.com.br");
    expect(rotaPermitida(sessao.eu as Eu, "/admin/exportar")).toBe(true);
    await entrar("rodrigo@motorapida.com.br");
    expect(rotaPermitida(sessao.eu as Eu, "/admin/exportar")).toBe(false);
  });
});
