// Ficha do veículo (T-102) contra docs/telas/html/Veiculo-Desktop.dc.html e Veiculo-Mobile.dc.html.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, ErroApi, veiculos, type Eu, type VeiculoDetalhe } from "@/lib/api";
import { FichaVeiculo, semAcesso } from "./FichaVeiculo";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

async function pagina(id: number): Promise<{ desktop: string; celular: string }> {
  const [ficha, docs, locacoes, manutencoes] = await Promise.all([veiculos.obter(id), veiculos.documentos(id), veiculos.locacoes(id), veiculos.manutencoes(id)]);
  const cliente = new QueryClient();
  cliente.setQueryData(["veiculo", id], ficha);
  cliente.setQueryData(["veiculo", id, "documentos"], docs);
  cliente.setQueryData(["veiculo", id, "locacoes"], locacoes);
  cliente.setQueryData(["veiculo", id, "manutencoes"], manutencoes);
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cliente}>
      <FichaVeiculo id={id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = html.match(/^<div class="hidden md:block">(.*)<\/div><div class="md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop, celular };
}

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

describe("ficha do veículo, gerente", () => {
  let desktop = "";
  let celular = "";
  beforeAll(async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    ({ desktop, celular } = await pagina(501));
  });

  it("desktop e celular são duas árvores; hidden e md:hidden ficam em div comum, nunca em elemento wl-", () => {
    expect(desktop).not.toBe("");
    expect(celular).not.toBe("");
    for (const m of (desktop + celular).matchAll(/class="([^"]*)"/g)) {
      const classes = m[1] ?? "";
      if (/\bwl-/.test(classes)) expect(classes, "wl- com hidden").not.toMatch(/(^|\s)(md:)?hidden(\s|$)/);
    }
  });

  it("desktop: seções e rótulos na ordem da referência", () => {
    const t = texto(desktop);
    ordem(t, ["Veículos", "QXA-4B21", "Honda CG 160 Fan", "Editar", "Movimentar", "Mandar para oficina", "Colocar à venda", "Rendeu no ano", "Ocupação", "Custo de manutenção", "Km atual", "Agora", "Locações", "Manutenções", "Dados", "Documentos"]);
    ordem(t, ["· 2023 · vermelha · Filial Centro", "R$ 9.870", "locações − custos", "86%", "últimos 90 dias", "R$ 353", "no ano", "18.950", "atualizado 23 set"]);
    // "Agora": o que a API manda (T-242). Período, plano, pagamentos e "faltam X km" ficam como pedido ao arquiteto.
    ordem(t, ["Agora", "Alugado desde 23 set", "Carlos Menezes", "LOC-2841", "Período", "23 set → 28 out", "Ver locação", "Próxima manutenção", "Troca de óleo", "aos 19.900 km"]);
    expect(t).not.toContain("faltam");
    expect(t).not.toContain("Cobrar");
    expect(t).not.toContain("Movimentações");
    expect(t).not.toContain("Fotos e avarias");
    expect(desktop).not.toContain("Foto do veículo");
    expect(t).toContain("14 no total");
    expect(t).toContain("próxima: troca de óleo aos 19.900 km");
    ordem(t, ["Contrato", "Cliente", "Período", "Situação", "LOC-2841", "Carlos Menezes", "23 set → 28 out", "Em andamento", "LOC-2702", "LOC-2640"]);
    ordem(t, ["Serviço", "Data", "Km", "Custo", "Troca de óleo", "12 set", "18.900 km", "R$ 48,00", "Pastilha de freio", "R$ 95,00", "Revisão 15 mil", "R$ 210,00"]);
    ordem(t, ["Chassi", "9C2KC2210PR004401", "Renavam", "01289934410", "Compra", "mar 2023 · R$ 13.900", "Valor de venda (FIPE)", "R$ 12.400", "Categoria", "Street 150–160", "Preço de hoje", "Semanal R$ 329,00"]);
    ordem(t, ["CRLV 2026", "Em dia", "IPVA 2026", "Pago", "Seguro", "Vence em 18 dias", "Rastreador", "Online"]);
  });

  it("desktop: o botão sólido é Colocar à venda e Editar abre a edição e as outras três ficam desativadas (sem tela ou endpoint)", () => {
    expect(desktop).toMatch(/<a class="wl-btn" href="\/veiculos\/501\/editar">Editar<\/a>/);
    for (const nome of ["Movimentar", "Mandar para oficina", "Colocar à venda"]) expect(desktop).toMatch(new RegExp(`<button[^>]*disabled[^>]*>(<svg.*?</svg>)?${nome}</button>`));
    expect(desktop).toMatch(/wl-btn wl-btn--solid"[^>]*disabled/);
  });

  it("celular: cabeçalho, KPIs, Agora, Documentos, Manutenções e botões, nessa ordem", () => {
    ordem(celular, ['aria-label="Voltar"', "Honda CG 160 Fan", "QXA-4B21 · 2023 · alugado", 'aria-label="Mais ações"', "Rendeu no ano", "Ocupação", "90 dias", "Agora", "Próxima manutenção", "Documentos", "Manutenções", "Oficina", "Colocar à venda"]);
    const t = texto(celular);
    ordem(t, ["Cliente", "Carlos Menezes", "Contrato", "LOC-2841", "Devolve", "28 out"]);
    ordem(t, ["Troca de óleo · 12 set", "R$ 48,00", "Pastilha de freio · 20 jul", "R$ 95,00", "Revisão 15 mil · 02 jul", "R$ 210,00"]);
    expect(t).not.toContain("Custo de manutenção");
    expect(t).not.toContain("Chassi");
    expect(celular).not.toContain("<table");
    expect(celular).not.toContain("Foto do veículo");
    expect(t).not.toContain("Fotos e avarias");
  });

  it("celular: alvos de toque de 44px no voltar e em Mais ações", () => {
    expect(celular.match(/width:44px;height:44px/g)).toHaveLength(2);
  });
});

describe("ficha do veículo, perfis sem financeiro nem edição", () => {
  it("vendedor não vê rendimento, custo, compra nem as ações", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const { desktop, celular } = await pagina(501);
    for (const h of [desktop, celular]) {
      expect(h).not.toContain("Rendeu no ano");
      expect(h).not.toContain("Colocar à venda");
    }
    expect(desktop).not.toContain("Custo de manutenção");
    expect(desktop).not.toContain("Compra");
    expect(desktop).toContain("Ocupação");
  });

  it("usr_09: financeiro lê a ficha com rendimento e custo da API e sem compra nem botões de escrita", async () => {
    await entrarComo("financeiro@motorapida.com.br");
    const ficha = await veiculos.obter(501);
    expect(Object.values(ficha.acoes).filter(Boolean)).toEqual([]);
    expect(ficha.indicadores_financeiros).toBeDefined();
    const { desktop, celular } = await pagina(501);
    expect(texto(desktop)).toContain("Rendeu no ano");
    expect(texto(desktop)).toContain("Custo de manutenção");
    expect(texto(celular)).toContain("Rendeu no ano");
    for (const h of [desktop, celular]) {
      expect(h).not.toMatch(/Editar|Colocar à venda|Bloquear|Transferir|Baixar|Registrar km|Corrigir km/);
      expect(h).not.toContain("/editar");
    }
    expect(desktop).not.toContain("Compra");
  });

  it("t_156_vendedor_fileira_de_indicadores_sem_cartao_vazio_nem_lugar_reservado", async () => {
    await entrarComo("bruna@motorapida.com.br");
    expect("indicadores_financeiros" in (await veiculos.obter(501))).toBe(false);
    const { desktop, celular } = await pagina(501);
    // Desktop: só Ocupação e Km atual, em duas colunas; celular: só Ocupação, numa coluna.
    expect(desktop.match(/class="wl-kpi[ "]/g)).toHaveLength(2);
    expect(desktop).toContain("grid-template-columns:repeat(2, minmax(0, 1fr))");
    expect(celular.match(/class="wl-kpi[ "]/g)).toHaveLength(1);
    expect(celular).toContain("grid-cols-1");
    expect(celular).not.toContain("grid-cols-2 gap-2 [&_.wl-kpi]");
    for (const h of [desktop, celular]) expect(texto(h)).not.toMatch(/Rendeu no ano|Custo de manutenção|—/);
  });

  it("t_156_gerente_com_a_chave_mostra_os_quatro_cartoes_no_desktop_e_dois_no_celular", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    expect("indicadores_financeiros" in (await veiculos.obter(501))).toBe(true);
    const { desktop, celular } = await pagina(501);
    expect(desktop.match(/class="wl-kpi[ "]/g)).toHaveLength(4);
    expect(desktop).not.toContain("style=\"grid-template-columns");
    expect(celular.match(/class="wl-kpi[ "]/g)).toHaveLength(2);
  });
});

describe("ficha do veículo sem histórico", () => {
  it("mostra os estados vazios", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = await pagina(504);
    expect(desktop).toContain("Este veículo ainda não foi alugado.");
    expect(desktop).toContain("Nenhuma manutenção registrada.");
    expect(celular).not.toContain("Agora");
  });
});

it("o tipo de veículo vem do contrato", async () => {
  const v: VeiculoDetalhe = await veiculos.obter(503);
  expect(v.tipo_veiculo).toBe("carro");
});

describe("ficha do veículo sem o módulo de manutenção no menu", () => {
  it("esconde a seção Manutenções em vez de mostrá-la vazia (T-128)", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const eu = sessao.eu as Eu;
    sessao.eu = { ...eu, navegacao: { ...eu.navegacao, menu_completo: eu.navegacao.menu_completo.map((g) => ({ ...g, itens: g.itens.filter((i) => i.chave !== "manutencoes") })) } };
    const { desktop, celular } = await pagina(504);
    for (const h of [desktop, celular]) {
      expect(h).not.toContain("Manutenções");
      expect(h).not.toContain("Nenhuma manutenção registrada.");
      expect(h).toContain("Documentos");
    }
  });
});

describe("ficha do veículo, vistoriador (D-25, USR-09)", () => {
  it("usr_09: a ficha vem sem valores e a tela não mostra compra, venda, plano padrão, rendimento nem custo", async () => {
    await entrarComo("joao@motorapida.com.br");
    const ficha = await veiculos.obter(501);
    for (const chave of ["preco_vigente", "valor_venda_centavos", "referencia_fipe_centavos", "valor_compra_centavos", "data_compra", "indicadores_financeiros"]) expect(chave in ficha, chave).toBe(false);
    const { desktop, celular } = await pagina(501);
    for (const h of [desktop, celular]) {
      const t = texto(h);
      for (const fora of ["Compra", "Valor de venda", "À venda por", "Preço de hoje", "Rendeu no ano", "Custo de manutenção", "Manutenções"]) expect(t, fora).not.toContain(fora);
      expect(t).not.toMatch(/R\$ \d/);
      expect(t).toContain("Ocupação");
    }
  });

  it("T-278: sem os dados de locações (403 da API) o painel Locações some, sem decidir pelo perfil", async () => {
    await entrarComo("joao@motorapida.com.br");
    const cliente = new QueryClient({ defaultOptions: { queries: { retryOnMount: false } } });
    cliente.setQueryData(["veiculo", 501], await veiculos.obter(501));
    cliente.setQueryData(["veiculo", 501, "documentos"], await veiculos.documentos(501));
    await cliente.fetchQuery({ queryKey: ["veiculo", 501, "locacoes"], queryFn: () => Promise.reject(new ErroApi(403, "sem_permissao", "Seu perfil não tem acesso a esta ação")), retry: false }).catch(() => {});
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cliente}>
        <FichaVeiculo id={501} />
      </QueryClientProvider>,
    );
    expect(texto(html)).not.toContain("Seu perfil não tem acesso a esta ação");
    expect(texto(html)).not.toContain("Locações");
    expect(texto(html)).toContain("Ocupação");
  });

  it("T-278: outro erro de locações continua aparecendo no painel", () => {
    expect(semAcesso({ isError: true, error: new ErroApi(500, "erro", "Falha") })).toBe(false);
    expect(semAcesso({ isError: true, error: new ErroApi(403, "sem_permissao", "x") })).toBe(true);
    expect(semAcesso({ isError: false, error: null })).toBe(false);
  });
});

describe("Movimentar e Transferir na ficha (MOV-02, MOV-06, T-289)", () => {
  it("veículo disponível: Movimentar e Transferir abrem a Nova movimentação com o veículo", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop } = await pagina(504);
    expect(desktop).toContain('href="/veiculos/movimentacoes/nova?veiculo=504"');
    expect(desktop).toContain('href="/veiculos/movimentacoes/nova?veiculo=504&amp;transferir=1"');
    expect(texto(desktop)).toContain("Movimentar");
    expect(texto(desktop)).toContain("Transferir");
  });

  it("veículo alugado: Movimentar desativado com o motivo da API e sem Transferir", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop } = await pagina(501);
    expect(desktop).toMatch(/<button[^>]*disabled[^>]*title="Veículo alugado não se movimenta\. O botão volta quando a LOC-2841 for devolvida\."[^>]*>/);
    expect(desktop).not.toContain("transferir=1");
  });

  it("quem só lê a frota (vendedor) não vê Movimentar nem Transferir", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const { desktop } = await pagina(504);
    expect(texto(desktop)).not.toMatch(/Movimentar|Transferir/);
  });
});
