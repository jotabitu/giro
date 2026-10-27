// T-370 · Estornar movimento do caixa e renegociar conta (FIN-01, FIN-07, CA-017-10, CA-017-17; docs/api/financeiro.md).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, financeiro, ErroApi, type Eu } from "@/lib/api";
import { reiniciarFinanceiroFalso } from "@/testes/falsos/falso-financeiro";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));

import { CaixaDoDia } from "./CaixaDoDia";
import { DetalheDaConta } from "./DetalheDaConta";
import { DialogoEstornarMovimento } from "./DialogoEstornarMovimento";
import { DialogoRenegociarConta } from "./DialogoRenegociarConta";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

async function paginaCaixa(): Promise<string> {
  const cache = new QueryClient();
  const hoje = await financeiro.caixaDeHoje();
  cache.setQueryData(["caixa", "hoje"], hoje);
  if ("id" in hoje) cache.setQueryData(["caixa", "movimentos", hoje.id], await financeiro.movimentos(hoje.id));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <CaixaDoDia />
    </QueryClientProvider>,
  );
}

const falha = async (p: Promise<unknown>) => {
  try {
    await p;
  } catch (e) {
    if (e instanceof ErroApi) return e;
  }
  throw new Error("esperava ErroApi");
};

beforeEach(() => reiniciarFinanceiroFalso());

describe("Caixa: estornar movimento (CA-017-17)", () => {
  it("fin_07_botao: quem estorna (administrador, gerente, financeiro) vê Estornar em cada movimento; o vendedor não", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const html = await paginaCaixa();
    expect(html.match(/aria-label="Estornar /g)?.length).toBeGreaterThanOrEqual(7);
    await entrar("bruna@motorapida.com.br");
    expect(await paginaCaixa()).not.toContain("Estornar");
  });

  it("fin_07_estorno: nasce um movimento com estorno_de, o original continua e a lista marca os dois", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const caixa = await financeiro.caixaDeHoje();
    if (!("id" in caixa)) throw new Error("esperava caixa aberto");
    const antes = await financeiro.movimentos(caixa.id);
    const oleo = antes.resultados.find((m) => m.descricao.startsWith("Óleo"))!;
    const estorno = await financeiro.estornarMovimento(caixa.id, oleo.id, "Lançado por engano");
    expect(estorno).toMatchObject({ estorno_de: oleo.id, tipo: oleo.tipo, forma: oleo.forma, valor_centavos: oleo.valor_centavos });
    const depois = await financeiro.movimentos(caixa.id);
    expect(depois.resultados.length).toBe(antes.resultados.length + 1);
    expect(depois.resultados.find((m) => m.id === oleo.id)?.estorno_de).toBeNull();
    const t = texto(await paginaCaixa());
    expect(t).toContain("Estornado");
    expect(t).toContain("Estorno");
    // O saldo da gaveta acompanha: a saída de R$ 48,00 em dinheiro foi desfeita.
    const novo = await financeiro.caixaDeHoje();
    if ("id" in novo) expect(novo.resumo.gaveta.esperado_centavos).toBe(28100 + 4800);
  });

  it("fin_07_estorno_uma_vez: estornar de novo o mesmo movimento ou um estorno volta 409; sem motivo, 400 no campo", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const caixa = await financeiro.caixaDeHoje();
    if (!("id" in caixa)) throw new Error("esperava caixa aberto");
    const e = await falha(financeiro.estornarMovimento(caixa.id, 500, "  "));
    expect([e.status, e.campos?.motivo]).toEqual([400, "Informe o motivo."]);
    const estorno = await financeiro.estornarMovimento(caixa.id, 500, "Pix errado");
    expect((await falha(financeiro.estornarMovimento(caixa.id, 500, "de novo"))).codigo).toBe("movimento_ja_estornado");
    expect((await falha(financeiro.estornarMovimento(caixa.id, estorno.id, "estorno do estorno"))).codigo).toBe("movimento_ja_estornado");
  });

  it("fin_07_dialogo: o estorno não se desfaz, pede o motivo e confirma na própria tela", async () => {
    const caixa = await financeiro.caixaDeHoje();
    if (!("id" in caixa)) throw new Error("esperava caixa aberto");
    const mov = (await financeiro.movimentos(caixa.id)).resultados[0]!;
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <DialogoEstornarMovimento caixaId={caixa.id} movimento={mov} aoFechar={() => {}} aoConcluir={() => {}} />
      </QueryClientProvider>,
    );
    ordem(texto(html), ["Estornar movimento", "O estorno não se desfaz.", "Motivo do estorno", "Voltar", "Estornar movimento"]);
    expect(html).toMatch(/<button[^>]*disabled[^>]*>Estornar movimento<\/button>/);
  });
});

describe("Contas a receber: renegociar (FIN-01, CA-017-10)", () => {
  it("fin_01_renegociar: a original vira renegociada e nascem as novas, com a soma igual ao devido hoje", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const original = await financeiro.obterConta(9010);
    expect(original.acoes.renegociar).toBe(true);
    const total = original.valor_hoje.total_centavos;
    const novas = await financeiro.renegociar({
      contas: [9010],
      novas: [
        { vencimento: "2026-10-15", valor_centavos: 15000 },
        { vencimento: "2026-10-22", valor_centavos: total - 15000 },
      ],
      motivo: "Cliente pediu mais prazo",
    });
    expect(novas.map((n) => [n.vencimento, n.status])).toEqual([
      ["2026-10-15", "aberta"],
      ["2026-10-22", "aberta"],
    ]);
    expect((await financeiro.obterConta(9010)).status).toBe("renegociada");
    expect((await financeiro.obterConta(9010)).acoes.renegociar).toBe(false);
  });

  it("fin_01_renegociar_soma: soma diferente volta 422 FIN-01; sem motivo, 400; conta já renegociada, 409", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const nova = { vencimento: "2026-10-15", valor_centavos: 10000 };
    expect((await falha(financeiro.renegociar({ contas: [9010], novas: [nova], motivo: "x" }))).codigo).toBe("FIN-01");
    expect((await falha(financeiro.renegociar({ contas: [9010], novas: [nova], motivo: " " }))).campos?.motivo).toBe("Informe o motivo.");
    const total = (await financeiro.obterConta(9010)).valor_hoje.total_centavos;
    await financeiro.renegociar({ contas: [9010], novas: [{ vencimento: "2026-10-15", valor_centavos: total }], motivo: "Prazo" });
    expect((await falha(financeiro.renegociar({ contas: [9010], novas: [{ vencimento: "2026-10-22", valor_centavos: total }], motivo: "Prazo" }))).status).toBe(409);
  });

  it("fin_01_dialogo: mostra o devido hoje da API, as contas novas e o aviso de que não se desfaz", async () => {
    const conta = await financeiro.obterConta(9010);
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <DialogoRenegociarConta conta={conta} aoFechar={() => {}} aoConcluir={() => {}} />
      </QueryClientProvider>,
    );
    ordem(texto(html), ["Renegociar conta", "Valor devido hoje: R$ 306,09.", "Isso não se desfaz.", "Contas novas", "Vencimento 1", "Valor 1 (R$)", "Adicionar conta nova", "Motivo da renegociação", "Voltar", "Renegociar conta"]);
    expect(html).toContain('value="306,09"');
  });

  it("o detalhe da conta oferece Renegociar conta só quando a API libera (acoes.renegociar)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const render = async (id: number) => {
      const cache = new QueryClient();
      cache.setQueryData(["contas-receber", "detalhe", id], await financeiro.obterConta(id));
      return texto(
        renderToStaticMarkup(
          <QueryClientProvider client={cache}>
            <DetalheDaConta id={id} aoFechar={() => {}} aoDarBaixa={() => {}} aoConcluir={() => {}} />
          </QueryClientProvider>,
        ),
      );
    };
    expect(await render(9010)).toContain("Renegociar conta");
    const total = (await financeiro.obterConta(9010)).valor_hoje.total_centavos;
    await financeiro.renegociar({ contas: [9010], novas: [{ vencimento: "2026-10-15", valor_centavos: total }], motivo: "Prazo" });
    expect(await render(9010)).not.toContain("Renegociar conta");
  });
});
