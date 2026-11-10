// T-417: despesas do veículo na ficha (FIN-17, VEI-05), categorias em dois grupos (FIN-06) e filtro por veículo (FIN-16).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, financeiro, veiculos, type DespesasDoVeiculo as Dados, type Eu, type VeiculoDetalhe } from "@/lib/api";
import { financeiroApi } from "@/lib/api/financeiro";
import { reiniciarFinanceiroFalso } from "@/testes/falsos/falso-financeiro";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/financeiro/despesas", useSearchParams: () => new URLSearchParams() }));

import { ListaDespesas } from "@/components/financeiro/ListaDespesas";
import { NovaDespesa } from "@/components/financeiro/NovaDespesa";
import { DespesasDoVeiculo } from "./DespesasDoVeiculo";

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

const OLEO = {
  id: 802,
  data: "2026-10-07",
  descricao: "Óleo 1 litro",
  categoria: "manutencao",
  veiculo: { id: 501, placa: "QXA4B21" },
  filial: { id: 1, nome: "Filial Centro" },
  valor_centavos: 4800,
  vencimento: "2026-10-07",
  status: "paga",
  pago_em: "2026-10-07T14:20:00Z",
  forma: "dinheiro",
  lancada_por: { id: 4, nome: "Bruna Alves" },
  nota: null,
  comprovante: null,
  sem_nota: false,
  origem: null,
  pedido_aprovacao_id: null,
  rotulo_situacao: "Paga",
} as Dados["resultados"][number];

async function ficha(lancar: boolean): Promise<VeiculoDetalhe> {
  const v = await veiculos.obter(501);
  return { ...v, acoes: { ...v.acoes, lancar_despesa: lancar } };
}

function secao(v: VeiculoDetalhe, dados?: Dados, celular = false): string {
  const cache = new QueryClient();
  if (dados) cache.setQueryData(["despesas", "veiculo", v.id, { ano: 2026, cursor: null }], dados);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DespesasDoVeiculo v={v} celular={celular} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-07T15:00:00Z"));
  reiniciarFinanceiroFalso();
});
afterEach(() => vi.useRealTimers());

describe("ficha: despesas do veículo (FIN-17)", () => {
  const doAno: Dados = { ano: 2026, total_ano_centavos: 4800, resultados: [OLEO], proximo: null, anterior: null };

  it("test_fin_17_gerente_ve_a_lista_o_total_e_o_botao (CA-417-07)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const v = await ficha(true);
    for (const celular of [false, true]) {
      const t = texto(secao(v, doAno, celular));
      expect(t).toContain("Despesas do veículo");
      expect(t).toContain("Despesas no ano|R$ 48,00");
      expect(t).toContain("Óleo 1 litro|07 out · Manutenção|Paga|R$ 48,00");
      expect(t).toContain("Lançar despesa");
    }
  });

  it("test_fin_17_recusada_fica_na_lista_e_o_total_vem_da_api (CA-417-08)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const recusada = { ...OLEO, id: 801, descricao: "Pneus (2 unidades)", valor_centavos: 120000, status: "recusada", rotulo_situacao: "Recusada" } as typeof OLEO;
    const t = texto(secao(await ficha(true), { ...doAno, total_ano_centavos: 0, resultados: [recusada] }));
    expect(t).toContain("Pneus (2 unidades)");
    expect(t).toContain("Recusada");
    expect(t).toContain("Despesas no ano|R$ 0,00");
  });

  it("test_fin_17_despesa_de_outra_filial_diz_a_filial (CA-417-13)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const outra = { ...OLEO, filial: { id: 9, nome: "Filial Caucaia" } };
    expect(texto(secao(await ficha(true), { ...doAno, resultados: [outra] }))).toContain("07 out · Manutenção · Filial Caucaia");
  });

  it("test_fin_17_vendedor_ve_so_o_botao_sem_espaco_para_a_lista (CA-417-09, CA-417-12)", async () => {
    await entrar("bruna@motorapida.com.br");
    const v = await ficha(true);
    expect(v.indicadores_financeiros).toBeUndefined();
    const t = texto(secao(v));
    expect(t).toContain("Lançar despesa");
    expect(t).not.toContain("Despesas no ano");
    expect(t).not.toContain("Carregando as despesas");
    // Sem o botão e sem a lista, a seção some.
    expect(secao(await ficha(false))).toBe("");
  });

  it("test_fin_17_lancar_pela_ficha_trava_o_veiculo (CA-417-10)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <NovaDespesa eu={sessao.eu as Eu} veiculoFixo={{ id: 501, placa: "QXA4B21", modelo: "CG 160 Fan" }} aoLancar={() => {}} />
      </QueryClientProvider>,
    );
    const t = texto(html);
    expect(t).toContain("Veículo|QXA-4B21| · CG 160 Fan");
    expect(t).not.toContain("Tirar");
    expect(html).not.toContain('placeholder="Placa"');
  });

  it("test_fin_17_o_lancamento_vai_para_a_rota_do_veiculo_sem_veiculo_no_corpo", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(OLEO), { status: 201, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    try {
      const nota = new File(["x"], "nota.jpg", { type: "image/jpeg" });
      await financeiroApi.lancarDespesaDoVeiculo(501, { descricao: "IPVA 2026", valor_centavos: 21000, data: "2026-10-07", vencimento: "2026-10-07", categoria: "ipva", veiculo_id: 88, nota });
      const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
      expect(url).toBe("/api/financeiro/despesas/veiculo/501/");
      const corpo = init.body as FormData;
      expect(corpo.get("categoria")).toBe("ipva");
      expect(corpo.has("veiculo_id")).toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

describe("tela Despesas (FIN-06, FIN-16)", () => {
  async function pagina(): Promise<string> {
    const cache = new QueryClient();
    cache.setQueryData(["despesas", { aba: "todas", mes: "2026-10", cursor: undefined, busca: "" }], await financeiro.listarDespesas({ mes: "2026-10" }));
    return renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <ListaDespesas />
      </QueryClientProvider>,
    );
  }

  it("test_fin_06_categorias_em_dois_grupos_na_ordem (CA-417-01)", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await pagina();
    const grupos = [...html.matchAll(/<optgroup label="([^"]+)">(.*?)<\/optgroup>/g)].map((m) => [m[1], [...(m[2] ?? "").matchAll(/>([^<]+)<\/option>/g)].map((o) => o[1])]);
    expect(grupos).toEqual([
      ["Do veículo", ["IPVA e licenciamento", "Seguro", "Multa de trânsito", "Peças", "Combustível", "Manutenção", "Rastreamento"]],
      ["Da empresa", ["Fixas", "Impostos", "Pessoal", "Outros"]],
    ]);
  });

  it("test_fin_16_filtro_por_veiculo (CA-417-06)", async () => {
    await entrar("mariana@motorapida.com.br");
    expect(texto(await pagina())).toContain("|Veículo|");
    const pmz = await financeiro.listarDespesas({ mes: "2026-10", veiculo: 88 });
    expect(pmz.resultados.map((d) => d.descricao)).toEqual(["Pneus (2 unidades)"]);
  });
});
