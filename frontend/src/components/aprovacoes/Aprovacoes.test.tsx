// Aprovações (T-175) contra docs/telas/html/Aprovacoes-*.dc.html, com o seed de 07 out (APR-01 a APR-11).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { aprovacoes, contas, financeiro, type Eu } from "@/lib/api";
import { efeitoDoTipo, haQuanto, linhaDaDecisao, linkDaOrigem, rotuloDoTipo } from "@/lib/aprovacoes";
import { reiniciarFinanceiroFalso } from "@/testes/falsos/falso-financeiro";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
const url = vi.hoisted(() => ({ aba: "" }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/aprovacoes", useSearchParams: () => new URLSearchParams(url.aba ? { aba: url.aba } : {}) }));

import { ListaAprovacoes } from "./ListaAprovacoes";

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

async function pagina(aba: "pendente" | "meus" = "pendente"): Promise<string> {
  url.aba = aba === "meus" ? "meus" : "";
  const cache = new QueryClient();
  const principal = aba === "meus" ? await aprovacoes.listar({ status: "pendente", minhas: true }) : await aprovacoes.listar({ status: "pendente" });
  cache.setQueryData(["aprovacoes", "lista", { aba, tipo: "" }], principal);
  cache.setQueryData(["aprovacoes", "esperando"], await aprovacoes.listar({ status: "pendente" }));
  cache.setQueryData(["aprovacoes", "decididas", "aprovado"], await aprovacoes.listar({ status: "aprovado" }));
  cache.setQueryData(["aprovacoes", "decididas", "recusado"], await aprovacoes.listar({ status: "recusado" }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaAprovacoes />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-07T15:00:00Z"));
  reiniciarFinanceiroFalso();
});
afterEach(() => vi.useRealTimers());

describe("pedidos esperando o gerente (Aprovacoes)", () => {
  it("cabeçalho, indicador e abas com a contagem da API", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(await pagina());
    for (const trecho of ["Aprovações", "Filial Centro · pedidos que dependem de você", "Esperando você", "3", "mais antigo há 2 h", "Pendentes", "Aprovadas", "Recusadas", "Meus pedidos", "Todos os tipos"]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("os três pedidos do seed, do mais antigo ao mais novo, com quem pediu, quando e o detalhe", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(await pagina());
    const ordem = ["Desconto de 8% na venda para Diego Martins", "Encerrar antes do fim a LOC-2812 · Patrícia Gomes", "Despesa de R$ 1.200,00"];
    let pos = -1;
    for (const o of ordem) {
      const i = t.indexOf(o, pos + 1);
      expect(i, o).toBeGreaterThan(pos);
      pos = i;
    }
    for (const trecho of ["Bruna Alves", "há 2 h", "VEN-0177", "há 1 h", "a cliente pediu pelo WhatsApp", "João Silva", "há 40 min", "Pneus (2 unidades) · PMZ-3E17", "APR-01", "APR-02", "APR-03", "Mais antigo", "R$ 1.200,00", "8%", "R$ 84,80"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).toContain("Acima de R$ 500 precisa da sua aprovação. Aprovada, vai para o financeiro pagar.");
  });

  it("cada pedido leva Ver ... para a origem, Recusar e Aprovar", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const html = await pagina();
    const t = texto(html);
    expect(t.match(/Aprovar/g)?.length).toBeGreaterThanOrEqual(3);
    expect(t.match(/Recusar/g)?.length).toBeGreaterThanOrEqual(3);
    expect(t).toContain("Ver locação");
    expect(t).toContain("Ver despesa");
    expect(html).toContain('href="/locacoes/2812"');
    expect(html).toContain('href="/financeiro/despesas/801"');
  });

  it("decididas recentemente com quem decidiu, o dia e o motivo da recusa", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(await pagina());
    expect(t).toContain("Decididas recentemente");
    expect(t).toContain("Diferença de caixa de R$ 3,50");
    expect(t).toContain("Rodrigo aprovou · 06 out");
    expect(t).toContain('Rodrigo recusou · 05 out · &quot;abaixo do preço mínimo&quot;');
    expect(t).toContain("Correção de km · RJD-5B38");
    expect(t).toContain("O que passa por aqui");
    expect(t).toContain("Você não aprova pedidos feitos por você mesmo.");
  });

  it("vendedora sem pedido para decidir vê a lista vazia, e os pedidos dela têm Cancelar pedido, sem Aprovar", async () => {
    await entrar("bruna@motorapida.com.br");
    expect(texto(await pagina())).toContain("Nenhum pedido esperando você.");
    const t = texto(await pagina("meus"));
    expect(t).toContain("Desconto de 8% na venda para Diego Martins");
    expect(t).toContain("Cancelar pedido");
    expect(t).not.toContain("Aprovar");
    expect(t).not.toContain("Despesa de R$ 1.200,00");
  });
});

describe("decisão na API falsa (aprovacoes.md)", () => {
  it("aprovar a despesa a leva para a pagar; sai da fila e entra nas decididas", async () => {
    await entrar("rodrigo@motorapida.com.br");
    await aprovacoes.aprovar(91);
    expect((await financeiro.obterDespesa(801)).status).toBe("a_pagar");
    expect((await aprovacoes.listar({ status: "pendente" })).contagens.pendente).toBe(2);
    expect((await aprovacoes.listar({ status: "aprovado" })).resultados[0]?.id).toBe(91);
  });

  it("recusar exige o motivo, que fica no pedido", async () => {
    await entrar("rodrigo@motorapida.com.br");
    await expect(aprovacoes.recusar(88, " ")).rejects.toMatchObject({ status: 400 });
    const r = await aprovacoes.recusar(88, "acima do limite");
    expect(r).toMatchObject({ status: "recusado", motivo_recusa: "acima do limite" });
    await expect(aprovacoes.aprovar(88)).rejects.toMatchObject({ codigo: "transicao_pedido" });
  });

  it("só quem pediu cancela, e o pedido cancelado não fica pendente", async () => {
    await entrar("rodrigo@motorapida.com.br");
    await expect(aprovacoes.cancelar(88)).rejects.toMatchObject({ codigo: "so_quem_pediu" });
    await entrar("bruna@motorapida.com.br");
    expect((await aprovacoes.cancelar(88)).status).toBe("cancelado");
    expect((await aprovacoes.listar({ status: "pendente", minhas: true })).contagens.pendente).toBe(1);
  });

  it("filtro por tipo", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect((await aprovacoes.listar({ status: "pendente", tipo: "APR-03" })).resultados.map((p) => p.id)).toEqual([91]);
  });
});

describe("apoio da tela", () => {
  it("há quanto tempo", () => {
    const agora = new Date("2026-10-07T15:00:00Z");
    expect(haQuanto("2026-10-07T14:20:00Z", agora)).toBe("há 40 min");
    expect(haQuanto("2026-10-07T13:00:00Z", agora)).toBe("há 2 h");
    expect(haQuanto("2026-10-06T14:00:00Z", agora)).toBe("há 1 dia");
    expect(haQuanto("2026-10-07T14:59:40Z", agora)).toBe("agora há pouco");
  });

  it("rótulo e efeito por tipo; link da origem", () => {
    expect(rotuloDoTipo("APR-04")).toBe("Diferença de caixa");
    expect(efeitoDoTipo("APR-06")).toContain("km");
    expect(linkDaOrigem({ tipo: "cliente", id: 12, codigo: null })).toEqual({ href: "/clientes/12", rotulo: "Ver cliente" });
    expect(linkDaOrigem({ tipo: "venda", id: 177, codigo: "VEN-0177" })).toBeNull();
  });

  it("linha da decisão", () => {
    expect(linhaDaDecisao({ status: "aprovado", decidido_por: { id: 2, nome: "Rodrigo Pinheiro" }, decidido_em: "2026-10-06T21:30:00Z", motivo_recusa: null, detalhe: "caixa fechado" })).toBe("Rodrigo aprovou · 06 out · caixa fechado");
  });
});
