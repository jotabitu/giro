// Espelha tests/aceitacao/test_t011_contas.py (T-071): o falso tem que devolver o mesmo que o backend (USR-05, USR-08).
import { describe, expect, it } from "vitest";
import { contas, type Eu, type GrupoNavegacao } from "@/lib/api";
import { navegacaoFalsa, TODOS_OS_MODULOS, TODOS_OS_RECURSOS } from "./falso-navegacao";

async function euDe(email: string): Promise<Eu> {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "pronto") return r.usuario;
  const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  if (v.etapa !== "pronto") throw new Error("esperava pronto");
  return v.usuario;
}

const chaves = (menu: GrupoNavegacao[]) => menu.map((g) => [g.grupo, g.itens.map((i) => i.chave)]);
const ADMINISTRACAO = ["config", "marca", "filiais", "usuarios", "assinatura", "auditoria"];

describe("navegação do falso por perfil (USR-05, USR-08)", () => {
  it("administrador antes da 1ª locação: implantação, menu do início igual ao completo", async () => {
    const { navegacao: n } = await euDe("novo@motorapida.com.br");
    expect(n.inicio).toEqual({ rota: "/inicio", variante: "implantacao" });
    expect(chaves(n.menu_completo)).toEqual([
      [null, ["inicio", "aprovacoes", "veiculos"]],
      ["Operação", ["locacoes", "vendas", "clientes", "manutencoes"]],
      ["Financeiro", ["caixa", "receber", "despesas", "comissoes", "conciliacao", "relatorios"]],
      ["Administração", ADMINISTRACAO],
    ]);
    expect(n.menu_inicio).toEqual(n.menu_completo);
    expect(n.menu_completo[0]!.itens[0]).toEqual({ chave: "inicio", rotulo: "Visão geral", contador: null });
    expect(n.barra_celular).toEqual(["inicio", "veiculos", "nova_locacao", "locacoes", "mais"]);
  });

  it("gerente: tem Vendas no início, aprova despesas e não paga contas", async () => {
    const { navegacao: n } = await euDe("rodrigo@motorapida.com.br");
    expect(n.inicio.variante).toBe("gerente");
    expect(chaves(n.menu_inicio)).toEqual([
      [null, ["inicio", "aprovacoes", "veiculos"]],
      ["Operação", ["locacoes", "vendas", "clientes", "manutencoes"]],
      ["Filial", ["caixa", "relatorios"]],
    ]);
    expect(n.menu_inicio[0]!.itens[0]!.rotulo).toBe("Visão da filial");
    expect(n.menu_inicio[2]!.itens[0]!.rotulo).toBe("Caixa da filial");
    expect(chaves(n.menu_completo)).toEqual([
      [null, ["inicio", "aprovacoes", "veiculos"]],
      ["Operação", ["locacoes", "vendas", "clientes", "manutencoes"]],
      ["Financeiro", ["caixa", "receber", "despesas", "relatorios"]],
    ]);
    expect(n.menu_completo[2]!.itens[2]!.contador).toBe("despesas");
  });

  it("vendedor: grupo Vendas no início, sem contador de despesas porque só lança", async () => {
    const { navegacao: n } = await euDe("bruna@motorapida.com.br");
    expect(n.inicio.variante).toBe("vendedor");
    expect(chaves(n.menu_inicio)).toEqual([
      [null, ["inicio"]],
      ["Operação", ["locacoes", "clientes"]],
      ["Vendas", ["propostas", "minhas_vendas", "veiculos_a_venda", "minhas_comissoes"]],
    ]);
    expect(chaves(n.menu_completo)).toEqual([
      [null, ["inicio"]],
      ["Operação", ["locacoes", "vendas", "clientes"]],
      ["Financeiro", ["caixa", "receber", "despesas"]],
    ]);
    expect(n.menu_completo[2]!.itens[2]!.contador).toBeNull();
    expect(n.barra_celular).toEqual(["inicio", "nova_locacao", "locacoes", "mais"]);
  });

  it("vistoriador: agenda do dia; vê locações pela vistoria, mas não cria", async () => {
    const { navegacao: n } = await euDe("joao@motorapida.com.br");
    expect(n.inicio.variante).toBe("vistoriador");
    expect(chaves(n.menu_inicio)).toEqual([[null, ["agenda", "consultar_veiculo", "avarias"]]]);
    expect(chaves(n.menu_completo)).toEqual([
      [null, ["inicio", "veiculos"]],
      ["Operação", ["locacoes", "manutencoes"]],
      ["Financeiro", ["despesas"]],
    ]);
    expect(n.barra_celular).toEqual(["inicio", "veiculos", "locacoes", "mais"]);
  });

  it("financeiro: Comissões no lugar de Relatórios no início; sem veículos nem locações", async () => {
    const { navegacao: n } = await euDe("financeiro@motorapida.com.br");
    expect(n.inicio.variante).toBe("financeiro");
    expect(chaves(n.menu_inicio)).toEqual([[null, ["inicio", "receber", "contas_a_pagar", "caixa_e_bancos", "comissoes"]]]);
    expect(chaves(n.menu_completo)).toEqual([
      [null, ["inicio"]],
      ["Operação", ["clientes"]],
      ["Financeiro", ["caixa", "receber", "despesas", "comissoes", "conciliacao", "relatorios"]],
    ]);
    expect(n.barra_celular).toEqual(["inicio", "mais"]);
  });
});

describe("plano, atividade e módulos escondem itens (USR-05)", () => {
  async function gerente() {
    const eu = await euDe("rodrigo@motorapida.com.br");
    return { pode: eu.pode, perfil: eu.perfil };
  }

  it("só os módulos entregues: o menu nunca leva a uma tela que não existe", async () => {
    const eu = await euDe("mariana@motorapida.com.br");
    const n = navegacaoFalsa(eu.perfil, eu.pode, "geral", { modulos: ["contas", "filiais", "plataforma"] });
    expect(chaves(n.menu_completo)).toEqual([
      [null, ["inicio"]],
      ["Administração", ["filiais", "usuarios", "assinatura"]],
    ]);
    expect(n.barra_celular).toEqual(["inicio", "mais"]);
  });

  it("plano Essencial: sem vendas, manutenção e despesas, comissões nem relatórios", async () => {
    const eu = await euDe("mariana@motorapida.com.br");
    const n = navegacaoFalsa(eu.perfil, eu.pode, "geral", { recursos: ["locacoes_vistoria", "contas_receber", "contrato_digital"] });
    expect(chaves(n.menu_completo)).toEqual([
      [null, ["inicio", "aprovacoes", "veiculos"]],
      ["Operação", ["locacoes", "clientes"]],
      ["Financeiro", ["caixa", "receber", "conciliacao"]],
      ["Administração", ADMINISTRACAO],
    ]);
  });

  it("quem só aluga não vê vendas; quem só vende não vê locações", async () => {
    const { pode, perfil } = await gerente();
    const aluga = navegacaoFalsa(perfil, pode, "gerente", { atividade: "aluga" });
    expect(aluga.menu_inicio[1]!.itens.map((i) => i.chave)).toEqual(["locacoes", "clientes", "manutencoes"]);
    const vende = navegacaoFalsa(perfil, pode, "gerente", { atividade: "vende" });
    expect(vende.menu_inicio[1]!.itens.map((i) => i.chave)).toEqual(["vendas", "clientes", "manutencoes"]);
    expect(vende.barra_celular).toEqual(["inicio", "veiculos", "mais"]);
  });

  it("vendedor sem o módulo de vendas perde o grupo Vendas do início", async () => {
    const eu = await euDe("bruna@motorapida.com.br");
    const modulos = TODOS_OS_MODULOS.filter((m) => m !== "vendas");
    const n = navegacaoFalsa(eu.perfil, eu.pode, "vendedor", { modulos, recursos: TODOS_OS_RECURSOS });
    expect(chaves(n.menu_inicio)).toEqual([
      [null, ["inicio"]],
      ["Operação", ["locacoes", "clientes"]],
    ]);
  });
});
