import { describe, expect, it } from "vitest";
import { contas, relatorios, type Eu } from "@/lib/api";
import { destinosDaBarra, gruposDaRota, hrefDoDestino, montarMenu } from "./menu";

async function euDe(email: string): Promise<Eu> {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "pronto") return r.usuario;
  const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  if (v.etapa !== "pronto") throw new Error("esperava pronto");
  return v.usuario;
}

const rotulos = (g: ReturnType<typeof montarMenu>) => g.flatMap((x) => x.itens.map((i) => i.rotulo));
const menuDe = (eu: Eu, rota: string, contadores?: Record<string, number | null>) => montarMenu(gruposDaRota(eu.navegacao, rota), rota, contadores);

describe("menu vindo de eu.navegacao (USR-05)", () => {
  it("administrador vê Administração no menu completo", async () => {
    const eu = await euDe("mariana@motorapida.com.br");
    const menu = menuDe(eu, "/veiculos");
    expect(menu.map((g) => g.rotulo)).toEqual([undefined, "Operação", "Financeiro", "Administração"]);
    expect(rotulos(menu)).toContain("Usuários");
  });

  it("gerente: menu do início com os itens dele e sem Administração", async () => {
    const eu = await euDe("rodrigo@motorapida.com.br");
    const menu = menuDe(eu, "/inicio");
    expect(rotulos(menu)).toContain("Visão da filial");
    expect(rotulos(menu)).toContain("Aprovações");
    expect(menu.some((g) => g.rotulo === "Administração")).toBe(false);
    expect(rotulos(menu)).not.toContain("Comissões");
  });

  it("fora do início vale o menu completo, não o do início", async () => {
    const eu = await euDe("rodrigo@motorapida.com.br");
    expect(rotulos(menuDe(eu, "/clientes"))).toContain("Visão geral");
    expect(rotulos(menuDe(eu, "/clientes"))).not.toContain("Visão da filial");
  });

  it("financeiro não vê Veículos nem Locações", async () => {
    const itens = rotulos(menuDe(await euDe("financeiro@motorapida.com.br"), "/financeiro/receber"));
    expect(itens).not.toContain("Veículos");
    expect(itens).not.toContain("Locações");
    expect(itens).toContain("Conciliação");
  });

  it("vistoriador: menu do início só com agenda, consulta e avarias", async () => {
    const itens = rotulos(menuDe(await euDe("joao@motorapida.com.br"), "/inicio"));
    expect(itens).toEqual(["Vistorias de hoje", "Consultar veículo", "Avarias abertas"]);
  });

  it("marca o item ativo e leva o contador da API; contador nulo ou zero não aparece", async () => {
    const eu = await euDe("mariana@motorapida.com.br");
    const itens = menuDe(eu, "/veiculos", { veiculos: 86, manutencoes: null, despesas: 0 }).flatMap((g) => g.itens);
    const v = itens.find((i) => i.chave === "veiculos");
    expect(v?.ativo).toBe(true);
    expect(v?.total).toBe(86);
    expect(itens.find((i) => i.chave === "manutencoes")?.total).toBeUndefined();
    expect(itens.find((i) => i.chave === "despesas")?.total).toBeUndefined();
  });

  it("chave que a tela não conhece fica de fora em vez de virar link quebrado", () => {
    const menu = montarMenu([{ grupo: null, itens: [{ chave: "inexistente", rotulo: "X", contador: null }] }], "/inicio");
    expect(menu).toEqual([]);
  });
});

describe("barra do celular vinda de eu.navegacao.barra_celular", () => {
  it("vendedor com locação: Início, +, Locações e Mais, sem Veículos", async () => {
    const eu = await euDe("bruna@motorapida.com.br");
    expect(destinosDaBarra(eu.navegacao.barra_celular).map((d) => d.chave)).toEqual(["inicio", "nova_locacao", "locacoes", "mais"]);
  });

  it("vistoriador não tem o +", async () => {
    const eu = await euDe("joao@motorapida.com.br");
    const chaves = destinosDaBarra(eu.navegacao.barra_celular).map((d) => d.chave);
    expect(chaves).not.toContain("nova_locacao");
    expect(chaves).toContain("mais");
  });

  it("administrador tem os cinco destinos, com as rotas", async () => {
    const eu = await euDe("mariana@motorapida.com.br");
    expect(destinosDaBarra(eu.navegacao.barra_celular).map((d) => d.href)).toEqual(["/inicio", "/veiculos", "/locacoes/nova", "/locacoes", "/mais"]);
  });
});

describe("destino de pendência do painel", () => {
  it("monta rota com filtro e id", () => {
    expect(hrefDoDestino("locacoes", "aba=precisam_acao")).toBe("/locacoes?aba=precisam_acao");
    expect(hrefDoDestino("contas_a_pagar", undefined, 803)).toBe("/financeiro/despesas/803");
    expect(hrefDoDestino("nova_locacao")).toBe("/locacoes/nova");
    expect(hrefDoDestino("desconhecido")).toBeUndefined();
  });
});

describe("rotas do menu (T-055, docs/telas/README.md)", () => {
  const grupo = (...chaves: string[]) => [{ grupo: null, itens: chaves.map((chave) => ({ chave, rotulo: chave, contador: null })) }];

  it("itens do menu do início usam as rotas corrigidas", () => {
    const itens = montarMenu(
      grupo("agenda", "avarias", "consultar_veiculo", "contas_a_pagar", "caixa_e_bancos", "propostas", "minhas_vendas", "veiculos_a_venda", "minhas_comissoes"),
      "/inicio",
    )[0]!.itens;
    expect(Object.fromEntries(itens.map((i) => [i.chave, i.href]))).toEqual({
      agenda: "/vistorias",
      avarias: "/vistorias/avarias",
      consultar_veiculo: "/veiculos",
      contas_a_pagar: "/financeiro/despesas",
      caixa_e_bancos: "/financeiro/caixa",
      propostas: "/vendas?aba=propostas",
      minhas_vendas: "/vendas",
      veiculos_a_venda: "/veiculos?status=a_venda",
      minhas_comissoes: "/financeiro/comissoes",
    });
  });

  it("rota ativa compara só o caminho, sem a query, e marca um item por vez", () => {
    const itens = montarMenu(grupo("minhas_vendas", "propostas", "veiculos_a_venda"), "/vendas")[0]!.itens;
    expect(itens.map((i) => i.ativo)).toEqual([true, false, false]);
    expect(montarMenu(grupo("veiculos_a_venda"), "/veiculos/501")[0]!.itens[0]!.ativo).toBe(true);
  });

  it("destino com query na rota junta o filtro", () => {
    expect(hrefDoDestino("propostas", "situacao=abertas")).toBe("/vendas?aba=propostas&situacao=abertas");
  });
});

describe("variante do início (USR-08)", () => {
  it.each([
    ["mariana@motorapida.com.br", "geral"],
    ["novo@motorapida.com.br", "implantacao"],
    ["rodrigo@motorapida.com.br", "gerente"],
    ["bruna@motorapida.com.br", "vendedor"],
    ["joao@motorapida.com.br", "vistoriador"],
    ["financeiro@motorapida.com.br", "financeiro"],
  ] as const)("%s abre a variante %s e o painel devolve o corpo dela", async (email, variante) => {
    const eu = await euDe(email);
    expect(eu.navegacao.inicio).toEqual({ rota: "/inicio", variante });
    const inicio = await relatorios.inicio();
    expect(inicio.variante).toBe(variante);
    const { contadores } = await relatorios.contadores();
    const pedidos = eu.navegacao.menu_inicio.concat(eu.navegacao.menu_completo).flatMap((g) => g.itens.map((i) => i.contador).filter((c): c is string => c !== null));
    for (const chave of pedidos) expect(chave in contadores, `contador ${chave}`).toBe(true);
  });
});
