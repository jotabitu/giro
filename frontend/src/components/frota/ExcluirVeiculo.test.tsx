// T-515 · Excluir o veículo sem histórico (VEI-22; docs/api/veiculos.md; Veiculo-Desktop e Veiculo-Mobile).
// A API decide: `acoes.excluir` traz a confirmação ou o aviso prontos; a tela mostra e chama a rota.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, ErroApi, veiculos, type Eu } from "@/lib/api";
import { avisoDaLista, esquecerAvisoDaLista } from "@/lib/aviso-da-lista";
import { mensagemDoErro } from "@/lib/erros";
import { definirHistoricoDoVeiculoFalso } from "@/testes/falsos/falso-frota";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos", useSearchParams: () => new URLSearchParams() }));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { excluirEVoltar, JanelaDeExcluir, recusaMudaAFicha } from "@/components/comum/ExcluirCadastro";
import { ExcluirVeiculo, FichaVeiculo } from "./FichaVeiculo";
import { ListaVeiculos } from "./ListaVeiculos";

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
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

const html = (no: ReactNode) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{no}</QueryClientProvider>);

async function ficha(id: number): Promise<{ desktop: string; celular: string }> {
  const cache = new QueryClient();
  cache.setQueryData(["veiculo", id], await veiculos.obter(id));
  cache.setQueryData(["veiculo", id, "documentos"], await veiculos.documentos(id));
  cache.setQueryData(["veiculo", id, "locacoes"], await veiculos.locacoes(id));
  cache.setQueryData(["veiculo", id, "manutencoes"], await veiculos.manutencoes(id));
  const h = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <FichaVeiculo id={id} />
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

beforeEach(() => {
  esquecerAvisoDaLista("/veiculos");
  definirHistoricoDoVeiculoFalso(509, ["locacao", "vistoria"]);
});

describe("VEI-22: o botão Excluir na ficha", () => {
  it("test_vei_22_gerente_e_administrador_veem_excluir_no_cabecalho_e_no_fim_da_ficha", async () => {
    for (const email of ["rodrigo@motorapida.com.br", "mariana@motorapida.com.br"]) {
      await entrar(email);
      const { desktop, celular } = await ficha(501);
      // Desktop: no cabeçalho, depois das outras ações; tom de perigo, botão de texto.
      ordem(texto(desktop), ["Editar", "Colocar à venda", "Excluir", "Rendeu no ano"]);
      expect(desktop).toMatch(/<button type="button" class="wl-btn bg-transparent text-critical-ink ">Excluir<\/button>/);
      // Celular: no fim da ficha, na largura toda, "Excluir veículo".
      const t = texto(celular);
      expect(t.trimEnd().endsWith("|Excluir veículo|")).toBe(true);
      expect(celular).toMatch(/class="wl-btn bg-transparent text-critical-ink w-full justify-center" style="height:48px">Excluir veículo<\/button>/);
    }
  });

  it("test_vei_22_o_botao_aparece_com_ou_sem_historico", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto((await ficha(510)).desktop)).toContain("|Excluir|");
    expect(texto((await ficha(504)).desktop)).toContain("|Excluir|");
  });

  it("test_vei_22_vendedor_vistoriador_e_financeiro_nao_veem_excluir", async () => {
    for (const email of ["bruna@motorapida.com.br", "joao@motorapida.com.br", "financeiro@motorapida.com.br"]) {
      await entrar(email);
      expect((await veiculos.obter(510)).acoes.excluir).toBeNull();
      const { desktop, celular } = await ficha(510);
      expect(texto(desktop)).not.toContain("Excluir");
      expect(texto(celular)).not.toContain("Excluir");
    }
  });
});

describe("VEI-22: veículo sem histórico", () => {
  it("test_vei_22_confirmacao_com_o_titulo_o_texto_e_os_botoes_da_regra", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const v = await veiculos.obter(510);
    const desktop = texto(html(<ExcluirVeiculo v={v} abertoDeInicio />));
    ordem(desktop, [
      "Excluir a UEF-8L63?",
      "Use só para um cadastro feito por engano. O carro sai da frota e de todas as listas, com as fotos, os documentos e os preços. A placa e o chassi ficam livres para um novo cadastro. Não dá para desfazer.",
      "Manter veículo",
      "Excluir veículo",
    ]);
    // Sem campo de motivo.
    expect(html(<ExcluirVeiculo v={v} abertoDeInicio />)).not.toContain("<input");
    // Celular: gaveta de baixo, o botão de perigo em cima.
    const celular = html(<ExcluirVeiculo v={v} celular abertoDeInicio />);
    expect(celular).toContain("wl-gaveta--baixo");
    ordem(texto(celular), ["Excluir a UEF-8L63?", "Excluir veículo", "Manter veículo"]);
    expect(celular).toContain('class="wl-btn bg-critical text-on-critical w-full justify-center"');
  });

  it("test_vei_22_confirmar_chama_a_rota_e_volta_para_a_frota_com_o_aviso_da_api", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const navegar = vi.fn();
    const antes = vi.fn(async () => {});
    const mensagem = await excluirEVoltar(() => veiculos.excluir(510), "/veiculos", navegar, antes);
    expect(mensagem).toBe("Veículo UEF-8L63 excluído.");
    expect(antes).toHaveBeenCalledOnce();
    expect(navegar).toHaveBeenCalledWith("/veiculos");
    expect(avisoDaLista("/veiculos")).toBe("Veículo UEF-8L63 excluído.");
    // A Frota mostra o aviso como veio; a ficha some (404).
    expect(texto(html(<ListaVeiculos />))).toContain("|Veículo UEF-8L63 excluído.|");
    expect((await falha(veiculos.obter(510))).status).toBe(404);
  });
});

describe("VEI-22: veículo com histórico", () => {
  it("test_vei_22_aviso_do_gerente_com_o_motivo_o_caminho_e_colocar_a_venda", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const v = await veiculos.obter(504);
    expect(v.acoes.excluir?.permitido).toBe(false);
    const t = texto(html(<ExcluirVeiculo v={v} abertoDeInicio />));
    ordem(t, [
      "Este veículo não pode ser excluído",
      "Este veículo já tem locação e vistoria. Ele fica guardado e não pode ser excluído. Para tirar a moto da frota, coloque à venda ou peça a baixa ao administrador (perda total, roubo ou sucata).",
      "Fechar",
      "Colocar à venda",
    ]);
    expect(t).not.toContain("Excluir veículo");
    // Celular: "Colocar à venda" em cima, "Fechar" embaixo.
    ordem(texto(html(<ExcluirVeiculo v={v} celular abertoDeInicio />)), ["Este veículo não pode ser excluído", "Colocar à venda", "Fechar"]);
  });

  it("test_vei_22_aviso_do_administrador_fala_em_fazer_a_baixa", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(html(<ExcluirVeiculo v={await veiculos.obter(504)} abertoDeInicio />));
    expect(t).toContain("Para tirar a moto da frota, coloque à venda ou faça a baixa (perda total, roubo ou sucata).");
  });

  it("test_vei_22_sem_poder_colocar_a_venda_o_aviso_so_tem_fechar", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const v = await veiculos.obter(501); // alugado: `acoes.colocar_a_venda` é falso
    const t = texto(html(<ExcluirVeiculo v={v} abertoDeInicio />));
    expect(t).toContain("Fechar");
    expect(t).not.toContain("Colocar à venda");
  });

  it("test_vei_22_409_com_historico_mostra_a_frase_da_api_e_manda_reler_a_ficha", async () => {
    await entrar("rodrigo@motorapida.com.br");
    definirHistoricoDoVeiculoFalso(509, []);
    const confirmacao = (await veiculos.obter(509)).acoes.excluir!;
    expect(confirmacao.permitido).toBe(true);
    // Uma venda e uma despesa entram depois de a ficha abrir: a API recusa.
    definirHistoricoDoVeiculoFalso(509, ["venda", "despesa"]);
    const navegar = vi.fn();
    const e = await falha(excluirEVoltar(() => veiculos.excluir(509), "/veiculos", navegar));
    expect(e).toMatchObject({ status: 409, codigo: "VEI-22", detalhes: { historico: ["venda", "despesa"] } });
    expect(e.message).toBe("Este veículo já tem venda e despesa. Ele fica guardado e não pode ser excluído.");
    expect(navegar).not.toHaveBeenCalled();
    expect(avisoDaLista("/veiculos")).toBeNull();
    expect(recusaMudaAFicha(e)).toBe(true);
    // Enquanto a ficha não volta, a confirmação mostra a frase como veio.
    const comErro = html(<JanelaDeExcluir acao={confirmacao} coisa="veículo" erro={mensagemDoErro(e)} aoConfirmar={() => {}} aoFechar={() => {}} />);
    expect(comErro).toContain('role="alert"');
    expect(texto(comErro)).toContain("|Este veículo já tem venda e despesa. Ele fica guardado e não pode ser excluído.|");
    // A ficha relida já traz o aviso.
    expect((await veiculos.obter(509)).acoes.excluir).toMatchObject({ permitido: false, motivo: e.message });
  });

  it("test_vei_22_403_mostra_a_mensagem_da_api_e_nao_rele_a_ficha", async () => {
    await entrar("bruna@motorapida.com.br");
    const e = await falha(veiculos.excluir(510));
    expect(e).toMatchObject({ status: 403, codigo: "permissao" });
    expect(recusaMudaAFicha(e)).toBe(false);
    const confirmacao = { permitido: true, titulo: "Excluir a UEF-8L63?", texto: "Use só para um cadastro feito por engano.", motivo: null, caminho: null };
    expect(texto(html(<JanelaDeExcluir acao={confirmacao} coisa="veículo" erro={mensagemDoErro(e)} aoConfirmar={() => {}} aoFechar={() => {}} />))).toContain("|Seu perfil não tem acesso a esta ação.|");
  });
});
