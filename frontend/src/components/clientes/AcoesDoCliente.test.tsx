// T-370 · Bloquear, desbloquear, inativar e reativar o cliente (CLI-03, CLI-05, CLI-09, APR-05; docs/api/clientes.md).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { clientes, contas, ErroApi, type Eu } from "@/lib/api";
import { reiniciarClientesFalsos } from "@/testes/falsos/falso-clientes";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { acoesDoCliente, linhasDaPendencia } from "./AcoesDoCliente";
import { DetalheDoCliente } from "./DetalheDoCliente";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

async function pagina(id: number): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["cliente", id], await clientes.obter(id));
  cache.setQueryData(["cliente", id, "locacoes"], await clientes.locacoes(id));
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDoCliente id={id} />
    </QueryClientProvider>,
  );
  return texto(html);
}

const falha = async (p: Promise<unknown>) => {
  try {
    await p;
  } catch (e) {
    if (e instanceof ErroApi) return e;
  }
  throw new Error("esperava ErroApi");
};

beforeEach(() => reiniciarClientesFalsos());

describe("quais ações cabem (CLI-05, CLI-09)", () => {
  it("cli_05_matriz: administrador e gerente mexem; o vendedor só pede o desbloqueio; os outros nada", () => {
    expect(acoesDoCliente("administrador", "ativo")).toEqual(["bloquear", "inativar"]);
    expect(acoesDoCliente("gerente", "incompleto")).toEqual(["bloquear", "inativar"]);
    expect(acoesDoCliente("gerente", "bloqueado")).toEqual(["desbloquear", "inativar"]);
    expect(acoesDoCliente("administrador", "inativo")).toEqual(["reativar"]);
    expect(acoesDoCliente("vendedor", "bloqueado")).toEqual(["desbloquear"]);
    expect(acoesDoCliente("vendedor", "ativo")).toEqual([]);
    expect(acoesDoCliente("financeiro", "bloqueado")).toEqual([]);
    expect(acoesDoCliente("vistoriador", "ativo")).toEqual([]);
  });

  it("cli_09_pendencia: as linhas do 422 seguem a ordem do contrato e omitem o que não tem", () => {
    expect(linhasDaPendencia({ locacao_aberta: true, em_aberto_centavos: 30609, venda_aberta: true })).toEqual(["Tem locação em andamento.", "Tem R$ 306,09 em aberto.", "Tem venda em andamento."]);
    expect(linhasDaPendencia({ locacao_aberta: false, em_aberto_centavos: 0, venda_aberta: false })).toEqual([]);
  });
});

describe("detalhe do cliente: botões por perfil e situação", () => {
  it("cli_05_gerente: cliente ativo mostra Bloquear e Inativar; bloqueado mostra Desbloquear; inativo mostra Reativar", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const ativo = await pagina(1201);
    expect(ativo).toContain("Bloquear cliente");
    expect(ativo).toContain("Inativar cliente");
    expect(ativo).not.toContain("Desbloquear cliente");
    const bloqueado = await pagina(1203);
    expect(bloqueado).toContain("Desbloquear cliente");
    expect(bloqueado).not.toContain("Bloquear cliente|");
    const inativo = await pagina(1210);
    expect(inativo).toContain("Reativar cliente");
    expect(inativo).not.toContain("Inativar cliente");
  });

  it("apr_05_vendedor: vê só Desbloquear no cliente bloqueado e nenhum botão no ativo", async () => {
    await entrar("bruna@motorapida.com.br");
    const bloqueado = await pagina(1203);
    expect(bloqueado).toContain("Desbloquear cliente");
    expect(bloqueado).not.toContain("Inativar cliente");
    const ativo = await pagina(1201);
    expect(ativo).not.toContain("Bloquear cliente");
    expect(ativo).not.toContain("Inativar cliente");
  });
});

describe("contrato das ações do cliente", () => {
  it("cli_05_bloquear: bloqueio manual com motivo; bloquear de novo volta 409; sem motivo, 400", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect((await falha(clientes.bloquear(1201, " "))).campos?.motivo).toBe("Informe o motivo.");
    const c = await clientes.bloquear(1201, "Documento suspeito");
    expect(c.status).toBe("bloqueado");
    expect(c.bloqueio).toMatchObject({ motivo: "manual", desbloqueia_sozinho: false });
    expect((await falha(clientes.bloquear(1201, "de novo"))).codigo).toBe("transicao_cliente");
  });

  it("apr_05_desbloquear: gerente desbloqueia na hora (200); vendedor só cria o pedido (202)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const r = await clientes.desbloquear(1203, "Pagou a dívida");
    expect(r).toMatchObject({ status: 200 });
    if (r.status === 200) expect(r.cliente.status).not.toBe("bloqueado");
    reiniciarClientesFalsos();
    await entrar("bruna@motorapida.com.br");
    const pedido = await clientes.desbloquear(1203, "Cliente quitou");
    expect(pedido).toEqual({ status: 202, pedido: { id: 88, tipo: "APR-05", status: "pendente" } });
    expect((await clientes.obter(1203)).status).toBe("bloqueado");
  });

  it("cli_09_inativar: com locação, valor em aberto ou venda volta 422 cliente_com_pendencia com os detalhes", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const e = await falha(clientes.inativar(1202, "Mudou de cidade"));
    expect([e.status, e.codigo]).toEqual([422, "cliente_com_pendencia"]);
    expect(e.detalhes).toMatchObject({ locacao_aberta: true });
    const venda = await falha(clientes.inativar(1207, "Teste"));
    expect(venda.detalhes).toMatchObject({ venda_aberta: true });
  });

  it("cli_03_inativar_e_reativar: sem pendência inativa, e o reativar volta a ativo ou incompleto", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const reativado = await clientes.reativar(1210, "Voltou a alugar");
    expect(["ativo", "incompleto"]).toContain(reativado.status);
    expect((await clientes.inativar(1210, "Sem uso")).status).toBe("inativo");
    expect((await falha(clientes.inativar(1210, "de novo"))).codigo).toBe("transicao_cliente");
  });

  it("a ação só é aceita para administrador e gerente: o vendedor recebe 403", async () => {
    await entrar("bruna@motorapida.com.br");
    expect((await falha(clientes.bloquear(1201, "x"))).status).toBe(403);
    expect((await falha(clientes.inativar(1210, "x"))).status).toBe(403);
  });
});
