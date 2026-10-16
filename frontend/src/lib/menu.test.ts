import { describe, expect, it } from "vitest";
import { contas, relatorios, type Eu } from "@/lib/api";
import { destinosDaBarra, gruposDaRota, hrefDoDestino, montarMenu, rotaPermitida } from "./menu";

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

  it("fora do início e das rotas dos itens dele vale o menu completo, não o do início", async () => {
    const eu = await euDe("rodrigo@motorapida.com.br");
    expect(rotulos(menuDe(eu, "/financeiro/despesas"))).toContain("Despesas");
    expect(rotulos(menuDe(eu, "/financeiro/despesas"))).not.toContain("Caixa da filial");
    expect(rotulos(menuDe(eu, "/inicio"))).toContain("Caixa da filial");
  });

  it("usr_05: nas rotas que os itens do menu do início abrem, vale o menu do início", async () => {
    const eu = await euDe("rodrigo@motorapida.com.br");
    const doInicio = rotulos(menuDe(eu, "/inicio"));
    expect(rotulos(menuDe(eu, "/clientes"))).toEqual(doInicio);
    expect(rotulos(menuDe(eu, "/veiculos/501"))).toEqual(doInicio);
  });

  it("usr_05: financeiro em /financeiro/receber mantém o menu do perfil e em /clientes vê o completo", async () => {
    const eu = await euDe("financeiro@motorapida.com.br");
    expect(rotulos(menuDe(eu, "/financeiro/receber"))).toEqual(rotulos(menuDe(eu, "/inicio")));
    const completo = rotulos(menuDe(eu, "/clientes"));
    expect(completo).toContain("Conciliação");
    expect(completo).toContain("Veículos");
    expect(completo).not.toContain("Locações");
  });

  it("usr_05: vistoriador vê o mesmo menu do início em /vistorias e em /vistorias/avarias, com Vistorias de hoje ativo", async () => {
    const eu = await euDe("joao@motorapida.com.br");
    const doInicio = rotulos(menuDe(eu, "/inicio"));
    expect(doInicio).toEqual(["Vistorias de hoje", "Consultar veículo", "Avarias abertas"]);
    for (const rota of ["/vistorias", "/vistorias/avarias"]) {
      expect(rotulos(menuDe(eu, rota))).toEqual(doInicio);
    }
    const agenda = menuDe(eu, "/vistorias/avarias").flatMap((g) => g.itens).find((i) => i.chave === "agenda");
    expect(agenda?.ativo).toBe(true);
    expect(rotulos(menuDe(eu, "/vistorias"))).not.toContain("Visão geral");
    expect(rotulos(menuDe(eu, "/vistorias"))).not.toContain("Locações");
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
  it("usr_09: vendedor com locação: Início, Veículos, +, Locações e Mais", async () => {
    const eu = await euDe("bruna@motorapida.com.br");
    expect(destinosDaBarra(eu.navegacao.barra_celular).map((d) => d.chave)).toEqual(["inicio", "veiculos", "nova_locacao", "locacoes", "mais"]);
  });

  it("usr_09: financeiro tem Início, Veículos e Mais, sem o + nem Locações", async () => {
    const eu = await euDe("financeiro@motorapida.com.br");
    expect(destinosDaBarra(eu.navegacao.barra_celular).map((d) => d.chave)).toEqual(["inicio", "veiculos", "mais"]);
  });

  it("usr_05: vistoriador tem Início, Veículos e Mais, sem o + nem Locações", async () => {
    const eu = await euDe("joao@motorapida.com.br");
    expect(destinosDaBarra(eu.navegacao.barra_celular).map((d) => d.chave)).toEqual(["inicio", "veiculos", "mais"]);
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

describe("guarda de rota: o que o menu do perfil não mostra (D-26, USR-09)", () => {
  it("usr_09: vistoriador não abre clientes, financeiro, locações nem cadastro de veículo", async () => {
    const eu = await euDe("joao@motorapida.com.br");
    for (const rota of ["/clientes", "/clientes/12", "/clientes/novo", "/financeiro/receber", "/financeiro/caixa", "/locacoes", "/locacoes/nova", "/veiculos/novo", "/admin/usuarios", "/relatorios"]) {
      expect(rotaPermitida(eu, rota), rota).toBe(false);
    }
  });

  it("usr_09: vistoriador abre início, frota, ficha do veículo, agenda, avarias, vistoria e devolução", async () => {
    const eu = await euDe("joao@motorapida.com.br");
    for (const rota of ["/inicio", "/mais", "/veiculos", "/veiculos/501", "/vistorias", "/vistorias/avarias", "/locacoes/2856/vistoria", "/locacoes/2856/devolucao", "/locacoes/2856"]) {
      expect(rotaPermitida(eu, rota), rota).toBe(true);
    }
  });

  it("usr_09: financeiro abre contas a receber, caixa, clientes e a ficha da locação; abre a frota só para ler e não abre vistoria", async () => {
    const eu = await euDe("financeiro@motorapida.com.br");
    for (const rota of ["/inicio", "/financeiro/receber", "/financeiro/caixa", "/financeiro/despesas", "/clientes", "/clientes/12", "/locacoes/2856", "/veiculos", "/veiculos/501"]) {
      expect(rotaPermitida(eu, rota), rota).toBe(true);
    }
    for (const rota of ["/veiculos/novo", "/veiculos/501/editar", "/locacoes", "/locacoes/nova", "/locacoes/2856/vistoria", "/clientes/novo", "/vistorias", "/admin/marca"]) {
      expect(rotaPermitida(eu, rota), rota).toBe(false);
    }
  });

  it("usr_05: administrador abre tudo que o menu tem, inclusive os cadastros", async () => {
    const eu = await euDe("mariana@motorapida.com.br");
    for (const rota of ["/veiculos/novo", "/clientes/novo", "/locacoes/nova", "/admin/marca", "/locacoes/2856/devolucao"]) {
      expect(rotaPermitida(eu, rota), rota).toBe(true);
    }
  });
});
