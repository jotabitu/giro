// Ficha do veículo (T-102) contra docs/telas/html/Veiculo-Desktop.dc.html e Veiculo-Mobile.dc.html.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { contas, veiculos, type Eu, type VeiculoDetalhe } from "@/lib/api";
import { FichaVeiculo } from "./FichaVeiculo";

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
  const [, desktop = "", celular = ""] = html.replace(/^(<link[^>]*>)+/, "").match(/^<div class="hidden md:block">(.*)<\/div><div class="md:hidden">(.*)<\/div>$/s) ?? [];
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
    // O "—" da VEI-09 (campo vazio no bloco "Dados do documento") é legítimo; o que não existe é cartão de indicador vazio.
    for (const h of [desktop, celular]) expect(texto(h)).not.toMatch(/Rendeu no ano|Custo de manutenção/);
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

describe("ficha do veículo, dados do documento, rastreador e anotações (VEI-09, T-421)", () => {
  it("test_vei_09_ficha_do_qxa4b21_para_o_gerente_nos_dois_tamanhos (CA-421-11)", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = await pagina(501);
    for (const h of [desktop, celular]) {
      const t = texto(h);
      ordem(t, ["Dados do documento", "Combustível|Flex", "Potência|15 cv", "Cilindrada|162 cc", "Espécie e tipo|Passageiro · Motocicleta", "Carroceria|—", "Lotação|2 pessoas", "Peso bruto total|290 kg", "Número do motor|KC22E1P004401", "Observações do CRLV-e|ALIENACAO FIDUCIARIA", "Rastreador|356938035643809| · Rastreia Fácil", "Anotações|Risco no tanque, lado esquerdo"]);
    }
  });

  it("test_vei_09_motor_e_observacoes_so_para_administrador_e_gerente_sem_espaco (CA-421-12)", async () => {
    for (const email of ["bruna@motorapida.com.br", "financeiro@motorapida.com.br"]) {
      await entrarComo(email);
      const ficha = await veiculos.obter(501);
      expect("numero_motor" in ficha.documento).toBe(false);
      expect("observacoes" in ficha.documento).toBe(false);
      const { desktop, celular } = await pagina(501);
      for (const h of [desktop, celular]) {
        const t = texto(h);
        expect(t).not.toContain("Número do motor");
        expect(t).not.toContain("KC22E1P004401");
        expect(t).not.toContain("Observações do CRLV-e");
        expect(t).not.toContain("ALIENACAO");
        // O resto do CA-421-11 segue na ficha, sem linha vazia no lugar das duas.
        ordem(t, ["Peso bruto total|290 kg", "Rastreador|356938035643809", "Anotações|Risco no tanque"]);
      }
    }
  });

  it("test_vei_09_veiculo_antigo_mostra_traco_sem_erro (CA-421-14)", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = await pagina(502);
    for (const h of [desktop, celular]) {
      const t = texto(h);
      for (const rotulo of ["Combustível", "Potência", "Cilindrada", "Espécie e tipo", "Carroceria", "Lotação", "Peso bruto total", "Número do motor", "Observações do CRLV-e", "Rastreador", "Anotações"]) expect(t, rotulo).toContain(`${rotulo}|—`);
    }
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

});

describe("ficha do veículo e a chave pode.locacoes_ver (T-458)", () => {
  /** Monta a ficha 501 sem nada de locações no cache e devolve o HTML e a consulta de locações que a ficha registrou. */
  async function fichaSemLocacoesNoCache() {
    const cliente = new QueryClient();
    cliente.setQueryData(["veiculo", 501], await veiculos.obter(501));
    cliente.setQueryData(["veiculo", 501, "documentos"], await veiculos.documentos(501));
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cliente}>
        <FichaVeiculo id={501} />
      </QueryClientProvider>,
    );
    const consulta = cliente.getQueryCache().find({ queryKey: ["veiculo", 501, "locacoes"], exact: true });
    return { html: texto(html), opcoes: consulta?.options as { enabled?: unknown } | undefined };
  }

  afterEach(() => vi.restoreAllMocks());

  it("test_usr_05_usr_09_sem_a_chave_a_ficha_nao_pede_locacoes_e_o_painel_nao_aparece", async () => {
    await entrarComo("joao@motorapida.com.br");
    expect((sessao.eu as Eu).pode.locacoes_ver).toBe(false);
    const chamada = vi.spyOn(veiculos, "locacoes");
    const { html, opcoes } = await fichaSemLocacoesNoCache();
    expect(chamada).not.toHaveBeenCalled();
    expect(opcoes?.enabled).toBe(false);
    expect(html).not.toContain("Locações");
    expect(html).toContain("Ocupação");
  });

  it("test_usr_05_usr_09_a_tela_segue_a_chave_e_nao_o_perfil", async () => {
    // Gerente com a chave desligada (como o modo suporte "só ver"): some igual ao vistoriador.
    await entrarComo("rodrigo@motorapida.com.br");
    const eu = sessao.eu as Eu;
    sessao.eu = { ...eu, pode: { ...eu.pode, locacoes_ver: false } };
    const chamada = vi.spyOn(veiculos, "locacoes");
    const { html, opcoes } = await fichaSemLocacoesNoCache();
    expect(chamada).not.toHaveBeenCalled();
    expect(opcoes?.enabled).toBe(false);
    expect(html).not.toContain("Locações");
  });

  it("test_usr_05_com_a_chave_a_ficha_pede_as_locacoes_e_mostra_o_painel", async () => {
    for (const email of ["rodrigo@motorapida.com.br", "financeiro@motorapida.com.br"]) {
      await entrarComo(email);
      expect((sessao.eu as Eu).pode.locacoes_ver, email).toBe(true);
      expect((await fichaSemLocacoesNoCache()).opcoes?.enabled, email).toBe(true);
      const { desktop } = await pagina(501);
      const t = texto(desktop);
      expect(t, email).toContain("Locações");
      expect(t, email).toContain("14 no total");
      expect(t, email).toContain("LOC-2841");
    }
  });

  it("test_usr_09_modo_suporte_so_ver_vem_sem_a_chave", async () => {
    const eu = await contas.entrarComoSuporte("suporte-valido");
    expect(eu.pode.locacoes_ver).toBe(false);
    await contas.sairDoSuporte();
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

describe("ficha do veículo vendido (VEN-11, LOC-16, T-420)", () => {
  beforeAll(async () => {
    await entrarComo("financeiro@motorapida.com.br");
  });
  async function comVendas(vendas: VeiculoDetalhe["vendas"]) {
    const ficha = { ...(await veiculos.obter(501)), vendas };
    const cliente = new QueryClient();
    cliente.setQueryData(["veiculo", 501], ficha);
    cliente.setQueryData(["veiculo", 501, "documentos"], []);
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cliente}>
        <FichaVeiculo id={501} />
      </QueryClientProvider>,
    );
    return texto(html);
  }
  const venda = {
    id: 1,
    codigo: "VEN-0001",
    status: "vendida",
    origem: "quitacao_locacao",
    origem_rotulo: "Quitação de locação",
    descricao: "Quitação da LOC-2876",
    cliente: { id: 9, nome: "Paula Tavares" },
    vendida_em: "2026-11-13T12:37:00Z",
    transferencia: { feita_em: "2026-11-13", registrada_por: { id: 2, nome: "Rodrigo Pinheiro" }, pendente: false },
    transferencia_texto: "Transferência no Detran feita em 13/11/2026 · Rodrigo Pinheiro",
  };

  it("test_ven_11_mostra_a_venda_e_a_linha_da_transferencia_como_a_api_manda", async () => {
    const t = await comVendas({ itens: [venda] });
    expect(t).toContain("Venda");
    expect(t).toContain("VEN-0001");
    expect(t).toContain("Quitação de locação");
    expect(t).toContain("Transferência no Detran feita em 13/11/2026 · Rodrigo Pinheiro");
  });

  it("test_ven_11_transferencia_pendente_mostra_o_selo_e_sem_venda_o_bloco_some", async () => {
    const pendente = await comVendas({ itens: [{ ...venda, transferencia: { feita_em: null, registrada_por: null, pendente: true }, transferencia_texto: null }] });
    expect(pendente).toContain("Falta a transferência no Detran");
    const sem = await comVendas(null);
    expect(sem).not.toContain("VEN-0001");
  });
});
