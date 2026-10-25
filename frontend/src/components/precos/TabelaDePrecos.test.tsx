// T-359 · Tabelas de preço (LOC-01, LOC-02, LOC-15, FIL-04): seed de 07 out e regras do contrato.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, precos, ErroApi, type Eu } from "@/lib/api";
import { definirPrecosFalsos } from "@/testes/falsos/falso-precos";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { TabelaDePrecos } from "./TabelaDePrecos";

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

async function pagina(): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["precos", "categorias", "todas"], await precos.categorias());
  cache.setQueryData(["precos", "planos", false], await precos.planosEspeciais({ ativo: true }));
  cache.setQueryData(["precos", "extras", false], await precos.extras({ ativo: true }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <TabelaDePrecos />
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

const PRECO = { diaria_centavos: 1, semanal_centavos: 1, mensal_centavos: 1, caucao_centavos: 1 };

beforeEach(() => definirPrecosFalsos(null));

describe("Tabelas de preço (/admin/precos)", () => {
  it("loc_01_seed: o administrador vê as 4 categorias do seed com os preços vigentes, planos e extras", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    ordem(t, ["Administração", "Tabelas de preço", "Valores usados ao criar uma locação.", "Histórico de preços", "Nova categoria", "Por categoria"]);
    ordem(t, ["Urbana 110–125", "R$ 44,90", "R$ 299,40", "R$ 1.090", "R$ 300", "Editar"]);
    ordem(t, ["Street 150–160", "R$ 54,90", "R$ 329", "R$ 1.190", "R$ 300"]);
    ordem(t, ["Scooter premium", "R$ 79,90", "R$ 449", "R$ 1.590", "R$ 500"]);
    ordem(t, ["Carro compacto", "R$ 109", "R$ 649", "R$ 2.290", "R$ 800"]);
    ordem(t, ["Planos especiais", "Entregador", "R$ 279,00/sem", "18 contratos", "Mensal fidelidade", "−10%", "7 contratos", "Extras", "Capacete extra", "R$ 15,00"]);
  });

  it("quem não é administrador não vê a tela", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await pagina())).toContain("Só o administrador mexe nas tabelas de preço.");
  });
});

describe("Contrato de categorias e preços (LOC-15, CA-013-22 a 25)", () => {
  it("loc_15_historico_da_street: 32900 desde 01 out e 29940 antes, do mais novo ao mais velho", async () => {
    const h = await precos.historicoDaCategoria(2);
    expect(h.map((p) => [p.vigente_desde, p.semanal_centavos])).toEqual([
      ["2026-10-01", 32900],
      ["2026-01-01", 29940],
    ]);
  });

  it("loc_15_preco_novo_nao_reescreve_o_passado: passado 400, data repetida 409, futuro em proximo_preco", async () => {
    const preco = { diaria_centavos: 4990, semanal_centavos: 29940, mensal_centavos: 109000, caucao_centavos: 30000 };
    expect((await falha(precos.definirPreco(1, { ...preco, vigente_desde: "2026-10-06" }))).status).toBe(400);
    expect((await falha(precos.definirPreco(1, { ...preco, vigente_desde: "2026-10-01" }))).codigo).toBe("preco_ja_definido");
    const r = await precos.definirPreco(1, { ...preco, vigente_desde: "2026-11-01" });
    expect(r.locacoes_em_andamento_mantidas).toBeGreaterThan(0);
    const urbana = (await precos.categorias()).find((c) => c.id === 1)!;
    expect(urbana.preco_vigente?.diaria_centavos).toBe(4490);
    expect(urbana.proximo_preco?.diaria_centavos).toBe(4990);
    // O preço agendado se troca até a data chegar; o vigente não.
    await precos.trocarPrecoAgendado(1, "2026-11-01", { ...preco, diaria_centavos: 5090 });
    expect((await falha(precos.trocarPrecoAgendado(1, "2026-10-01", preco))).codigo).toBe("preco_ja_vigente");
  });

  it("loc_01_categoria: nome em uso 409, tipo e desativação com veículos 422", async () => {
    expect((await falha(precos.criarCategoria({ nome: "Street 150–160", tipo_veiculo: "moto", preco: PRECO }))).codigo).toBe("categoria_nome_em_uso");
    expect((await falha(precos.alterarCategoria(2, { tipo_veiculo: "carro" }))).codigo).toBe("categoria_com_veiculos");
    expect((await falha(precos.desativarCategoria(2))).codigo).toBe("categoria_com_veiculos");
  });

  it("fil_04_filial: a filial traz as categorias da empresa mais as dela", async () => {
    await precos.criarCategoria({ nome: "Só da filial", tipo_veiculo: "moto", filial_id: 2, preco: PRECO });
    expect((await precos.categorias({ filial: 1 })).map((c) => c.nome)).not.toContain("Só da filial");
    expect((await precos.categorias({ filial: 2 })).map((c) => c.nome)).toContain("Só da filial");
  });

  it("loc_01_categoria_sem_veiculos: desativa e reativa", async () => {
    const c = await precos.criarCategoria({ nome: "Nova", tipo_veiculo: "moto", preco: PRECO });
    expect((await precos.desativarCategoria(c.id)).ativo).toBe(false);
    expect((await precos.categorias({ ativo: true })).map((x) => x.id)).not.toContain(c.id);
    expect((await precos.reativarCategoria(c.id)).ativo).toBe(true);
  });

  it("loc_15_historico_da_empresa: lista a mudança da Street de 29940 para 32900", async () => {
    const h = await precos.historico();
    expect(h).toContainEqual(
      expect.objectContaining({ categoria: { id: 2, nome: "Street 150–160" }, campo: "semanal", antes_centavos: 29940, depois_centavos: 32900, vigente_desde: "2026-10-01" }),
    );
  });
});

describe("Extras e planos especiais (LOC-02, LOC-15, CA-013-25)", () => {
  it("loc_02_extra: cria, muda o valor e desativa; desativado sai da escolha", async () => {
    const e = await precos.criarExtra({ nome: "Baú", valor_centavos: 2000, cobranca: "por_periodo" });
    expect((await precos.alterarExtra(e.id, { valor_centavos: 1800 })).valor_centavos).toBe(1800);
    await precos.desativarExtra(e.id);
    expect((await precos.extras({ ativo: true })).map((x) => x.id)).not.toContain(e.id);
    expect((await precos.extras()).map((x) => x.id)).toContain(e.id);
  });

  it("loc_01_plano_especial: cria, altera e desativa; ativo todos traz os desativados", async () => {
    const p = await precos.criarPlanoEspecial({ nome: "Aplicativo", periodicidade: "semanal", regra: "preco_fixo", preco_centavos: 25000, condicoes: "" });
    expect((await precos.alterarPlanoEspecial(p.id, { preco_centavos: 26000 })).preco_centavos).toBe(26000);
    await precos.desativarPlanoEspecial(p.id);
    expect((await precos.planosEspeciais({ ativo: true })).map((x) => x.id)).not.toContain(p.id);
    expect((await precos.planosEspeciais({ ativo: "todos" })).map((x) => x.id)).toContain(p.id);
  });
});
