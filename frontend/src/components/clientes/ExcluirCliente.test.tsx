// T-515 · Excluir o cliente sem histórico (CLI-13; docs/api/clientes.md; Cliente-Detalhe-Desktop e Cliente-Detalhe-Mobile).
// A API decide: `acoes.excluir` traz a confirmação ou o aviso prontos; a tela mostra e chama a rota.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { clientes, contas, ErroApi, type ClienteCompleto, type Eu } from "@/lib/api";
import { avisoDaLista, esquecerAvisoDaLista } from "@/lib/aviso-da-lista";
import { mensagemDoErro } from "@/lib/erros";
import { definirHistoricoDoClienteFalso, reiniciarClientesFalsos } from "@/testes/falsos/falso-clientes";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/clientes", useSearchParams: () => new URLSearchParams() }));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { excluirEVoltar, JanelaDeExcluir, recusaMudaAFicha } from "@/components/comum/ExcluirCadastro";
import { DetalheDoCliente } from "./DetalheDoCliente";
import { ExcluirCliente } from "./ExcluirCliente";
import { ListaClientes } from "./ListaClientes";

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

const html = (no: ReactNode) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{no}</QueryClientProvider>);
const obter = async (id: number) => (await clientes.obter(id)) as ClienteCompleto;

async function ficha(id: number): Promise<{ desktop: string; celular: string }> {
  const cache = new QueryClient();
  cache.setQueryData(["cliente", id], await clientes.obter(id));
  cache.setQueryData(["cliente", id, "locacoes"], await clientes.locacoes(id));
  const h = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDoCliente id={id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = h.replace(/^(<link[^>]*>)+/, "").match(/^<div class="hidden md:block">(.*)<\/div><div class="md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop, celular };
}

const falha = async (p: Promise<unknown>) => {
  try {
    await p;
  } catch (e) {
    if (e instanceof ErroApi) return e;
  }
  throw new Error("esperava ErroApi");
};

/** Cadastro feito por engano: nasce sem histórico. */
const cadastroNovo = (tipo: "pf" | "pj" = "pf", cpf = "52998224725") =>
  tipo === "pf"
    ? clientes.criar({ tipo: "pf", nome: "Cliente Repetido", documento: cpf, celular: "85988880000" })
    : clientes.criar({ tipo: "pj", nome: "Teste Entregas Ltda", documento: "11444777000161", celular: "85988880001", responsavel: { nome: "Ana Teste", cpf: "52998224725", celular: "85988880002" } });

const nada = () => {};

beforeEach(() => {
  reiniciarClientesFalsos();
  esquecerAvisoDaLista("/clientes");
});

describe("CLI-13: o botão Excluir na ficha", () => {
  it("test_cli_13_gerente_e_administrador_veem_excluir_no_cabecalho_e_no_fim_da_ficha", async () => {
    for (const email of ["rodrigo@motorapida.com.br", "mariana@motorapida.com.br"]) {
      await entrar(email);
      const { desktop, celular } = await ficha(1201);
      // Desktop: no cabeçalho, depois de Editar (e de Iniciar locação, como na referência); tom de perigo, botão de texto.
      ordem(texto(desktop), ["Juliana Rocha", "Editar", "Iniciar locação", "Total pago", "Ações", "WhatsApp", "Excluir", "Dados pessoais"]);
      expect(desktop).toContain('<button type="button" class="wl-acao wl-acao--perigo" aria-label="Excluir">');
      // Celular: no fim da ficha, depois da última seção, "Excluir cliente".
      expect(texto(celular).trimEnd().endsWith("|Excluir cliente|")).toBe(true);
      expect(celular).toMatch(/class="wl-btn bg-transparent text-critical-ink w-full justify-center" style="height:48px">Excluir cliente<\/button>/);
    }
  });

  it("test_cli_13_vendedor_nao_ve_excluir", async () => {
    await entrar("bruna@motorapida.com.br");
    expect((await obter(1201)).acoes?.excluir).toBeNull();
    const { desktop, celular } = await ficha(1201);
    expect(texto(desktop)).not.toContain("Excluir");
    expect(texto(celular)).not.toContain("Excluir");
  });
});

describe("CLI-13: cliente sem histórico", () => {
  it("test_cli_13_confirmacao_com_o_titulo_o_texto_e_os_botoes_da_regra", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const c = await obter((await cadastroNovo()).id);
    const desktop = html(<ExcluirCliente c={c} aoAvisar={nada} abertoDeInicio />);
    ordem(texto(desktop), [
      "Excluir o cadastro de Cliente Repetido?",
      "Use só para um cadastro feito por engano. O cliente sai da lista, os dados pessoais e os documentos enviados são apagados, e o CPF fica livre para um novo cadastro. Não dá para desfazer.",
      "Manter cliente",
      "Excluir cliente",
    ]);
    expect(desktop).not.toContain("<input");
    const celular = html(<ExcluirCliente c={c} celular aoAvisar={nada} abertoDeInicio />);
    expect(celular).toContain("wl-gaveta--baixo");
    ordem(texto(celular), ["Excluir o cadastro de Cliente Repetido?", "Excluir cliente", "Manter cliente"]);
  });

  it("test_cli_13_pessoa_juridica_fala_do_cnpj", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const c = await obter((await cadastroNovo("pj")).id);
    const t = texto(html(<ExcluirCliente c={c} aoAvisar={nada} abertoDeInicio />));
    expect(t).toContain("Excluir o cadastro de Teste Entregas Ltda?");
    expect(t).toContain("e o CNPJ fica livre para um novo cadastro.");
  });

  it("test_cli_13_confirmar_chama_a_rota_e_volta_para_a_lista_com_o_aviso_da_api", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const { id } = await cadastroNovo("pf", "39053344705");
    const navegar = vi.fn();
    const mensagem = await excluirEVoltar(() => clientes.excluir(id), "/clientes", navegar);
    expect(mensagem).toBe("Cliente excluído.");
    expect(navegar).toHaveBeenCalledWith("/clientes");
    expect(avisoDaLista("/clientes")).toBe("Cliente excluído.");
    expect(texto(html(<ListaClientes />))).toContain("|Cliente excluído.|");
    expect((await falha(clientes.obter(id))).status).toBe(404);
    // CLI-01: o CPF fica livre para um cadastro novo.
    await expect(cadastroNovo("pf", "39053344705")).resolves.toMatchObject({ nome: "Cliente Repetido" });
  });
});

describe("CLI-13: cliente com histórico", () => {
  it("test_cli_13_aviso_do_gerente_com_o_motivo_o_caminho_e_inativar", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const c = await obter(1201);
    const t = texto(html(<ExcluirCliente c={c} aoAvisar={nada} abertoDeInicio />));
    ordem(t, [
      "Este cliente não pode ser excluído",
      "Este cliente já tem locação e conta na empresa. O cadastro fica guardado e não pode ser excluído. Para ele não fazer novas locações nem compras, inative o cadastro.",
      "Fechar",
      "Inativar cliente",
    ]);
    expect(t).not.toContain("anonimizar");
    expect(t).not.toContain("Excluir cliente");
    ordem(texto(html(<ExcluirCliente c={c} celular aoAvisar={nada} abertoDeInicio />)), ["Este cliente não pode ser excluído", "Inativar cliente", "Fechar"]);
  });

  it("test_cli_13_aviso_do_administrador_fala_da_anonimizacao", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(html(<ExcluirCliente c={await obter(1201)} aoAvisar={nada} abertoDeInicio />));
    expect(t).toContain("inative o cadastro. Se o cliente pediu para apagar os dados dele, peça à equipe Giro para anonimizar o cadastro.");
    expect(t).toContain("Inativar cliente");
  });

  it("test_cli_13_cliente_ja_inativo_nao_oferece_inativar", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(html(<ExcluirCliente c={await obter(1210)} aoAvisar={nada} abertoDeInicio />));
    expect(t).toContain("O cadastro fica guardado e não pode ser excluído. O cadastro já está inativo.");
    expect(t).toContain("Fechar");
    expect(t).not.toContain("Inativar cliente");
  });

  it("test_cli_13_bloqueado_sem_historico_pede_para_desbloquear", async () => {
    await entrar("rodrigo@motorapida.com.br");
    definirHistoricoDoClienteFalso(1203, []);
    const c = await obter(1203);
    const t = texto(html(<ExcluirCliente c={c} aoAvisar={nada} abertoDeInicio />));
    ordem(t, ["Este cliente não pode ser excluído", "Desbloqueie o cliente antes de excluir.", "Fechar"]);
    expect(t).not.toContain("Inativar cliente");
    const e = await falha(clientes.excluir(1203));
    expect(e).toMatchObject({ status: 409, codigo: "transicao_cliente" });
    expect(recusaMudaAFicha(e)).toBe(true);
  });

  it("test_cli_13_409_com_historico_mostra_a_frase_da_api_e_manda_reler_a_ficha", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const { id } = await cadastroNovo("pf", "11144477735");
    const confirmacao = (await obter(id)).acoes!.excluir!;
    expect(confirmacao.permitido).toBe(true);
    // Uma venda entra depois de a ficha abrir: a API recusa.
    definirHistoricoDoClienteFalso(id, ["venda"]);
    const navegar = vi.fn();
    const e = await falha(excluirEVoltar(() => clientes.excluir(id), "/clientes", navegar));
    expect(e).toMatchObject({ status: 409, codigo: "CLI-13", detalhes: { historico: ["venda"] } });
    expect(e.message).toBe("Este cliente já tem venda na empresa. O cadastro fica guardado e não pode ser excluído.");
    expect(navegar).not.toHaveBeenCalled();
    expect(recusaMudaAFicha(e)).toBe(true);
    const comErro = html(<JanelaDeExcluir acao={confirmacao} coisa="cliente" erro={mensagemDoErro(e)} aoConfirmar={nada} aoFechar={nada} />);
    expect(texto(comErro)).toContain("|Este cliente já tem venda na empresa. O cadastro fica guardado e não pode ser excluído.|");
    expect((await obter(id)).acoes?.excluir).toMatchObject({ permitido: false, motivo: e.message, inativar: true });
  });

  it("test_cli_13_403_mostra_a_mensagem_da_api", async () => {
    await entrar("bruna@motorapida.com.br");
    const e = await falha(clientes.excluir(1201));
    expect(e).toMatchObject({ status: 403 });
    expect(recusaMudaAFicha(e)).toBe(false);
  });
});
