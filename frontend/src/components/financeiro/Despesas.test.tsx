// Despesas (T-167) contra docs/telas/html/Despesas-*.dc.html, com os números do seed de 07 out (FIN-05, APR-03).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { aprovacoes, contas, financeiro, type Eu, type ListaDespesas as DadosDeDespesas } from "@/lib/api";
import { financeiroApi } from "@/lib/api/financeiro";
import { corpoDaDespesa, mesDe, nomeDoMes, pagoEmDoDia } from "@/lib/despesas";
import { origemDaDespesa, rotuloDaCategoria } from "@/lib/financeiro";
import { pedidosDeExportacao, reiniciarFinanceiroFalso } from "@/testes/falsos/falso-financeiro";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
const filialDaTela = vi.hoisted(() => ({ atual: null as null | { todas: boolean; nome: string } }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => filialDaTela.atual }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/financeiro/despesas", useSearchParams: () => new URLSearchParams() }));

import { DetalheDaDespesa } from "./DetalheDaDespesa";
import { ListaDespesas } from "./ListaDespesas";

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

async function pagina(aba: "todas" | "aguardando_aprovacao" = "todas", alterar?: (d: DadosDeDespesas) => DadosDeDespesas): Promise<string> {
  const cache = new QueryClient();
  const dados = await financeiro.listarDespesas({ mes: "2026-10", status: aba === "todas" ? undefined : aba });
  cache.setQueryData(["despesas", { aba, mes: "2026-10", cursor: undefined, busca: "" }], alterar ? alterar(dados) : dados);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaDespesas />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-07T15:00:00Z"));
  reiniciarFinanceiroFalso();
  filialDaTela.atual = null;
});
afterEach(() => vi.useRealTimers());

describe("lista de despesas (FIN-05, CA-017-19)", () => {
  it("mostra os indicadores do seed: outubro R$ 7.066,70 e aguardando aprovação 1 de R$ 1.200,00", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    expect(t).toContain("Despesas");
    expect(t).toContain("Outubro · Filial Centro");
    expect(t).toContain("Gasto em outubro");
    expect(t).toContain("R$ 7.066,70");
    expect(t).toContain("Aguardando aprovação|1|R$ 1.200,00");
    expect(t).toContain("A pagar esta semana");
    expect(t).toContain("R$ 412,30");
  });

  it("lista as seis despesas com a situação que a API mandou e quem lançou", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    for (const trecho of ["Pneus (2 unidades)", "Manutenção · PMZ-3E17 · Filial Centro", "Aguardando gerente", "João Silva", "Óleo 1 litro", "Pago · caixa", "Conta de luz", "Fixa · Filial Centro", "Vence 10 out", "Aluguel do ponto", "Pago · boleto", "IPVA ROE-2A88", "Impostos · ROE-2A88 · Filial Centro", "A pagar", "Rastreadores (86)", "Pago · cartão"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).toContain("R$ 3.500,00");
    expect(t).toContain("R$ 186,40");
  });

  it("o IPVA de R$ 186,40 nasce a pagar e não entra em aguardando (FIN-05)", async () => {
    await entrar("mariana@motorapida.com.br");
    const lista = await financeiro.listarDespesas({ mes: "2026-10" });
    expect(lista.resultados.find((x) => x.descricao.startsWith("IPVA"))?.status).toBe("a_pagar");
    expect(lista.indicadores.aguardando_aprovacao_centavos).toBe(120000);
  });

  it("filtros Todas, Aguardando 1, A pagar 2 e Pagas, e Por categoria com os valores da API", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await pagina();
    const t = texto(html);
    expect(t).toContain("Aguardando 1");
    expect(t).toContain("A pagar 2");
    expect(t).toContain("Pagas");
    expect(t).toContain("Por categoria");
    expect(t).toContain("R$ 3.912,30");
    expect(html).toContain('aria-label="Nova despesa"');
    expect(t).toContain("Acima de R$ 500 vai para o gerente aprovar antes de pagar.");
  });

  it("o formulário tem os campos da referência", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    for (const campo of ["Descrição", "Valor", "Data", "Categoria", "Veículo (opcional)", "Foto da nota", "Lançar despesa"]) expect(t, campo).toContain(campo);
  });

  it("CA-DES-01: a despesa por veículo de outubro é R$ 82,17, o valor que a API mandou", async () => {
    await entrar("financeiro@motorapida.com.br");
    expect((await financeiro.listarDespesas({ mes: "2026-10" })).indicadores.despesa_por_veiculo_centavos).toBe(8217);
    expect(texto(await pagina())).toContain("Despesa por veículo|R$ 82,17|no mês");
  });

  it("CA-DES-03: sem veículos a API manda null e a tela não mostra valor nem zero", async () => {
    await entrar("financeiro@motorapida.com.br");
    const t = texto(await pagina("todas", (d) => ({ ...d, indicadores: { ...d.indicadores, despesa_por_veiculo_centavos: null } })));
    expect(t).toContain("Despesa por veículo|—");
    expect(t).not.toContain("Despesa por veículo|R$");
  });

  it("CA-DES-04: a busca 'pneu' filtra a lista e as contagens, e os indicadores continuam os do mês", async () => {
    await entrar("financeiro@motorapida.com.br");
    const sem = await financeiro.listarDespesas({ mes: "2026-10" });
    const r = await financeiro.listarDespesas({ mes: "2026-10", busca: "pneu" });
    expect(r.resultados.map((x) => x.descricao)).toEqual(["Pneus (2 unidades)"]);
    expect(r.contagens).toEqual({ aguardando_aprovacao: 1, a_pagar: 0, paga: 0, recusada: 0 });
    expect(r.indicadores).toEqual(sem.indicadores);
    expect(r.indicadores.gasto_mes_centavos).toBe(706670);
    expect(r.indicadores.aguardando_aprovacao_centavos).toBe(120000);
  });

  it("a busca acha pela placa, com hífen, e sem acento", async () => {
    await entrar("financeiro@motorapida.com.br");
    const achou = async (busca: string) => (await financeiro.listarDespesas({ mes: "2026-10", busca })).resultados.map((x) => x.descricao);
    expect(await achou("pmz-3e17")).toEqual(["Pneus (2 unidades)"]);
    expect(await achou("ROE")).toEqual(["IPVA ROE-2A88"]);
    expect(await achou("oleo")).toEqual(["Óleo 1 litro"]);
  });

  it("o campo de busca e a nota obrigatória aparecem na tela", async () => {
    await entrar("financeiro@motorapida.com.br");
    const html = await pagina();
    expect(html).toContain('placeholder="Buscar despesa"');
    expect(html).toContain('aria-label="Buscar despesa"');
    expect(texto(html)).toContain("Foto da nota (obrigatória)");
    expect(html).toContain('aria-required="true"');
  });

  it("t_244_cabecalho_e_busca_como_a_referencia: o + é só do celular, Exportar fica à direita e a busca cabe no bloco da lista", async () => {
    await entrar("financeiro@motorapida.com.br");
    const html = await pagina();
    // O `.wl-icon-btn` define `display` e vence o `md:hidden` do próprio link: quem some no desktop é o wrapper.
    expect(html).toMatch(/<div class="ml-auto md:hidden"><a [^>]*aria-label="Nova despesa"/);
    expect(html).not.toMatch(/<a [^>]*aria-label="Nova despesa"[^>]*md:hidden/);
    expect(texto(html)).not.toContain("Avulso");
    // Exportar à direita do cabeçalho, no desktop.
    expect(html).toMatch(/<div class="ml-auto hidden md:block"><button[^>]*>(<svg.*?<\/svg>)?Exportar/);
    // A busca (360px no padrão do design system) ocupa só os 220px do bloco, dentro do painel da lista.
    const painel = html.slice(html.indexOf('aria-label="Despesas do mês"'));
    expect(painel).toContain('w-[220px] [&amp;_.wl-search]:!w-full');
    expect(painel.indexOf('aria-label="Buscar despesa"')).toBeGreaterThan(0);
  });

  it("CA-DES-06 e CA-DES-06b: administrador e financeiro veem Exportar, pela flag de pode", async () => {
    for (const email of ["mariana@motorapida.com.br", "financeiro@motorapida.com.br"]) {
      await entrar(email);
      expect((sessao.eu as Eu).pode.despesas_exportar, email).toBe(true);
      expect(texto(await pagina()), email).toContain("Exportar");
    }
  });

  it("CA-DES-08: gerente, vendedor e vistoriador não veem Exportar", async () => {
    for (const email of ["rodrigo@motorapida.com.br", "bruna@motorapida.com.br", "joao@motorapida.com.br"]) {
      await entrar(email);
      expect(texto(await pagina()), email).not.toContain("Exportar");
    }
  });

  it("CA-DES-06: o pedido leva só o mês e a filial, em /api/exportacoes/", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 17, status: "na_fila" }), { status: 202, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    try {
      await financeiroApi.exportarDespesas({ mes: "2026-10", filial_id: 1 });
      const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
      expect(url).toBe("/api/exportacoes/");
      expect(init.method).toBe("POST");
      expect(JSON.parse(String(init.body))).toEqual({ itens: ["despesas"], formato: "csv", mes: "2026-10", filial_id: 1 });
    } finally {
      vi.unstubAllGlobals();
    }
    await entrar("mariana@motorapida.com.br");
    expect(await financeiro.exportarDespesas({ mes: "2026-10", filial_id: null })).toEqual({ id: 17, status: "na_fila" });
    expect(pedidosDeExportacao).toEqual([{ mes: "2026-10", filial_id: null }]);
  });

  it("vistoriador não vê a lista e só lança manutenção (tabela de perfis)", async () => {
    await entrar("joao@motorapida.com.br");
    const html = await pagina();
    const t = texto(html);
    expect(t).not.toContain("Pneus (2 unidades)");
    expect(t).not.toContain("Gasto em outubro");
    expect(t).toContain("Lançar despesa");
    expect(t).toContain("Seu perfil lança só despesas de manutenção.");
    expect(html).not.toContain('value="fixas"');
    expect(html).toContain('value="manutencao"');
  });
});

describe("detalhe e decisão (APR-03, APR-09)", () => {
  const detalhe = async (email: string, id: number, decide?: boolean, jaEntrou = false) => {
    // Para trocar o `pode_decidir`, os pedidos vêm da lista da administradora, que decide todos.
    if (!jaEntrou) await entrar(decide !== undefined ? "mariana@motorapida.com.br" : email);
    const pendentes = await aprovacoes.listar({ status: "pendente" });
    if (!jaEntrou) await entrar(email);
    const d = await financeiro.obterDespesa(id);
    const cache = new QueryClient();
    // `decide` troca o `pode_decidir` que a API mandou, para provar que a tela só lê esse campo.
    cache.setQueryData(["aprovacoes", "esperando"], decide === undefined ? pendentes : { ...pendentes, resultados: pendentes.resultados.map((p) => ({ ...p, pode_decidir: decide })) });
    return texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <DetalheDaDespesa id={id} inicial={d} eu={sessao.eu as Eu} aoFechar={() => {}} aoConcluir={() => {}} />
        </QueryClientProvider>,
      ),
    );
  };

  it("o gerente aprova ou recusa os pneus, que outra pessoa lançou", async () => {
    const t = await detalhe("rodrigo@motorapida.com.br", 801);
    expect(t).toContain("Aprovar");
    expect(t).toContain("Recusar");
    expect(t).not.toContain("Pagar");
  });

  it("quem lançou não decide o próprio pedido (APR-09)", async () => {
    await entrar("joao@motorapida.com.br");
    const d = await financeiro.obterDespesa(801);
    expect(d.lancada_por.id).toBe((sessao.eu as Eu).id);
    const t = await detalhe("joao@motorapida.com.br", 801);
    expect(t).not.toContain("Aprovar");
  });

  it("CA-248-08: o botão Aprovar vem do pode_decidir da API, não do perfil nem de quem lançou", async () => {
    expect(await detalhe("bruna@motorapida.com.br", 801, true)).toContain("Aprovar");
    expect(await detalhe("rodrigo@motorapida.com.br", 801, false)).not.toContain("Aprovar");
  });

  it("CA-248-08: a administradora vê Aprovar no pedido que ela mesma lançou", async () => {
    await entrar("mariana@motorapida.com.br");
    const nova = await financeiro.lancarDespesa({ descricao: "Revisão do QXA-4B21", valor_centavos: 120000, data: "2026-10-08", vencimento: "2026-10-08", categoria: "manutencao" });
    expect(nova.status).toBe("aguardando_aprovacao");
    const t = await detalhe("mariana@motorapida.com.br", nova.id, undefined, true);
    expect(t).toContain("Aprovar");
    expect(t).toContain("Recusar");
  });

  it("o financeiro paga despesa a pagar e não aprova", async () => {
    const t = await detalhe("financeiro@motorapida.com.br", 803);
    expect(t).toContain("Pagar");
    expect(t).not.toContain("Aprovar");
    expect(t).toContain("R$ 412,30");
    expect(t).toContain("Vence 10 out");
  });

  it("vendedor só vê o detalhe", async () => {
    const t = await detalhe("bruna@motorapida.com.br", 803);
    expect(t).not.toContain("Pagar");
    expect(t).not.toContain("Aprovar");
  });
});

describe("API falsa e envio (contrato financeiro.md)", () => {
  it("acima de R$ 500 nasce aguardando aprovação e não pode ser paga no caixa", async () => {
    const nova = await financeiro.lancarDespesa({ descricao: "Bateria", valor_centavos: 50001, data: "2026-10-07", vencimento: "2026-10-07", categoria: "manutencao" });
    expect(nova.status).toBe("aguardando_aprovacao");
    await expect(financeiro.lancarDespesa({ descricao: "Bateria", valor_centavos: 60000, data: "2026-10-07", vencimento: "2026-10-07", categoria: "manutencao", pago_no_caixa: true })).rejects.toMatchObject({ codigo: "APR-03" });
  });

  it("até R$ 500 nasce a pagar; pagar muda para paga", async () => {
    const nova = await financeiro.lancarDespesa({ descricao: "Filtro", valor_centavos: 50000, data: "2026-10-07", vencimento: "2026-10-07", categoria: "manutencao" });
    expect(nova.status).toBe("a_pagar");
    const paga = await financeiro.pagarDespesa(nova.id, { forma: "pix", pago_em: "2026-10-07T15:00:00Z" });
    expect(paga.status).toBe("paga");
  });

  it("aprovar leva a despesa para a pagar e recusar exige o motivo", async () => {
    await aprovacoes.aprovar(91);
    expect((await financeiro.obterDespesa(801)).status).toBe("a_pagar");
    reiniciarFinanceiroFalso();
    await expect(aprovacoes.recusar(91, " ")).rejects.toMatchObject({ status: 400 });
    await aprovacoes.recusar(91, "Sem orçamento");
    expect((await financeiro.obterDespesa(801)).status).toBe("recusada");
  });

  it("o cliente HTTP manda multipart com a nota e deixa de fora o que não foi preenchido", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 1 }), { status: 201, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    try {
      const nota = new File(["x"], "nota.jpg", { type: "image/jpeg" });
      await financeiroApi.lancarDespesa({ descricao: "Pneus", valor_centavos: 120000, data: "2026-10-07", vencimento: "2026-10-07", categoria: "manutencao", veiculo_id: null, nota, pago_no_caixa: false });
      const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit & { headers: Record<string, string> }];
      expect(url).toBe("/api/financeiro/despesas/");
      expect(init.method).toBe("POST");
      expect(init.headers["Content-Type"]).toBeUndefined();
      const f = init.body as FormData;
      expect(f.get("valor_centavos")).toBe("120000");
      expect(f.get("categoria")).toBe("manutencao");
      expect(f.get("pago_no_caixa")).toBe("false");
      expect(f.has("veiculo_id")).toBe(false);
      expect((f.get("nota") as File).name).toBe("nota.jpg");
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

describe("apoio da tela", () => {
  it("mês e nome do mês em America/Sao_Paulo", () => {
    expect(mesDe(new Date("2026-11-01T01:00:00Z"))).toBe("2026-10");
    expect(nomeDoMes("2026-10")).toBe("Outubro");
  });

  it("origem: categoria, placa e a filial da API; sem veículo, categoria e filial (FIN-06, FIL-05)", () => {
    const centro = { id: 1, nome: "Filial Centro" };
    expect(origemDaDespesa({ categoria: "manutencao", veiculo: { id: 1, placa: "PMZ3E17" }, filial: centro })).toBe("Manutenção · PMZ-3E17 · Filial Centro");
    expect(origemDaDespesa({ categoria: "manutencao", veiculo: { id: 1, placa: "PMZ3E17" }, filial: { id: 2, nome: "Filial Aldeota" } })).toBe("Manutenção · PMZ-3E17 · Filial Aldeota");
    expect(origemDaDespesa({ categoria: "fixas", veiculo: null, filial: centro })).toBe("Fixa · Filial Centro");
    expect(rotuloDaCategoria("rastreamento")).toBe("Rastreamento");
  });

  it("corpo: vencimento igual à data quando não informado; valor, descrição ou nota vazios não enviam (CA-DES-15)", () => {
    const nota = new File(["x"], "nota.jpg", { type: "image/jpeg" });
    const base = { descricao: " Troca de pneu ", valor: "150,00", data: "2026-10-07", vencimento: "", categoria: "manutencao" as const, veiculoId: null, nota, pagoNoCaixa: false };
    expect(corpoDaDespesa({ ...base, nota: null })).toBeNull();
    expect(corpoDaDespesa(base)).toMatchObject({ descricao: "Troca de pneu", valor_centavos: 15000, vencimento: "2026-10-07" });
    expect(corpoDaDespesa({ ...base, valor: "abc" })).toBeNull();
    expect(corpoDaDespesa({ ...base, descricao: " " })).toBeNull();
  });

  it("pagar em outro dia vale meio-dia de Brasília; hoje vale agora", () => {
    const agora = new Date("2026-10-07T15:00:00Z");
    expect(pagoEmDoDia("2026-10-07", agora)).toBe(agora.toISOString());
    expect(pagoEmDoDia("2026-10-05", agora)).toBe("2026-10-05T15:00:00.000Z");
  });
});
