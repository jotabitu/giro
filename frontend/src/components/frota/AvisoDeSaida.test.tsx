// T-462 · Aviso ao sair da tela com fotos enviando (VEI-10, "Sair da tela com fotos enviando"; CA-437-11).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  destinoInterno,
  FaltamFotos,
  guardarVoltar,
  textoDeFaltam,
  textoDoAviso,
} from "./AvisoDeSaida";
import {
  EnvioDasFotos,
  fotosQueFaltam,
  type EstadoDaFoto,
  type ItemDoEnvio,
} from "./FotosDoCadastro";

const base = {
  href: "https://locadora.giro.test/veiculos/novo",
  origin: "https://locadora.giro.test",
  pathname: "/veiculos/novo",
  search: "",
};

function clique(
  href: string,
  extra: Record<string, unknown> = {},
  atributos: { target?: string; download?: boolean } = {},
) {
  const ancora = {
    href: new URL(href, base.href).href,
    target: atributos.target ?? "",
    hasAttribute: (n: string) => n === "download" && !!atributos.download,
  };
  return {
    defaultPrevented: false,
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    target: { closest: () => ancora },
    ...extra,
  } as unknown as Parameters<typeof destinoInterno>[0];
}

const item = (estado: EstadoDaFoto, n: number): ItemDoEnvio => ({
  chave: `f${n}`,
  arquivo: new File(["x"], `f${n}.jpg`, { type: "image/jpeg" }),
  url: null,
  capa: n === 0,
  estado,
});

describe("VEI-10 · aviso ao sair com fotos enviando (T-462)", () => {
  it("test_vei_10_texto_de_quantas_faltam", () => {
    expect(textoDeFaltam(3)).toBe("Faltam 3 fotos. Não feche esta tela.");
    expect(textoDeFaltam(1)).toBe("Falta 1 foto.");
  });

  it("test_vei_10_texto_do_aviso_de_saida", () => {
    expect(textoDoAviso(3)).toBe(
      "Ainda faltam 3 fotos. Se sair, elas não serão enviadas.",
    );
    expect(textoDoAviso(1)).toBe(
      "Ainda falta 1 foto. Se sair, ela não será enviada.",
    );
  });

  it("test_vei_10_faltam_conta_fila_enviando_e_parada_por_conexao", () => {
    const itens = [
      item("enviada", 0),
      item("enviando", 1),
      item("fila", 2),
      item("sem_conexao", 3),
      item("recusada", 4),
    ];
    expect(fotosQueFaltam(itens)).toBe(3);
    expect(fotosQueFaltam([item("enviada", 0), item("recusada", 1)])).toBe(0);
  });

  it("test_vei_10_tela_mostra_quantas_faltam_so_enquanto_ha_foto_por_subir", () => {
    expect(renderToStaticMarkup(<FaltamFotos faltam={2} />)).toContain(
      "Faltam 2 fotos. Não feche esta tela.",
    );
    expect(renderToStaticMarkup(<FaltamFotos faltam={0} />)).toBe("");
    const subindo = renderToStaticMarkup(
      <EnvioDasFotos
        itens={[item("enviada", 0), item("enviando", 1), item("fila", 2)]}
        placa="QXA-4B21"
        veiculoId={7}
        aoTentarDeNovo={() => {}}
      />,
    );
    expect(subindo).toContain("Enviando fotos · 2 de 3");
    expect(subindo).toContain("Faltam 2 fotos. Não feche esta tela.");
    const parado = renderToStaticMarkup(
      <EnvioDasFotos
        itens={[item("enviada", 0), item("recusada", 1)]}
        placa="QXA-4B21"
        veiculoId={7}
        aoTentarDeNovo={() => {}}
      />,
    );
    expect(parado).not.toContain("Faltam");
    expect(parado).not.toContain("Falta 1");
  });

  it("test_vei_10_link_interno_pede_sair_ou_ficar", () => {
    expect(destinoInterno(clique("/veiculos"), base)).toBe("/veiculos");
    expect(destinoInterno(clique("/locacoes?status=ativa#topo"), base)).toBe(
      "/locacoes?status=ativa#topo",
    );
  });

  it("test_vei_10_links_que_nao_saem_da_tela_passam_direto", () => {
    expect(destinoInterno(clique("https://outro.site/x"), base)).toBeNull();
    expect(destinoInterno(clique("#fotos"), base)).toBeNull();
    expect(
      destinoInterno(clique("/veiculos", {}, { target: "_blank" }), base),
    ).toBeNull();
    expect(
      destinoInterno(clique("/veiculos", {}, { download: true }), base),
    ).toBeNull();
    expect(
      destinoInterno(clique("/veiculos", { ctrlKey: true }), base),
    ).toBeNull();
    expect(destinoInterno(clique("/veiculos", { button: 1 }), base)).toBeNull();
    expect(
      destinoInterno(clique("/veiculos", { defaultPrevented: true }), base),
    ).toBeNull();
    expect(
      destinoInterno(
        {
          ...clique("/veiculos"),
          target: { closest: () => null },
        } as unknown as Parameters<typeof destinoInterno>[0],
        base,
      ),
    ).toBeNull();
  });
});

describe("VEI-10 · Voltar do navegador (T-462)", () => {
  it("test_vei_10_voltar_do_navegador_pede_sair_ou_ficar", () => {
    const ouvintes: Record<string, () => void> = {};
    const pilha: unknown[] = [];
    const janela = {
      location: { href: "https://locadora.giro.test/veiculos/novo" },
      history: {
        state: { __NA: true },
        pushState: (s: unknown) => pilha.push(s),
        back: () => ouvintes.popstate?.(),
      },
      addEventListener: (n: string, f: () => void) => (ouvintes[n] = f),
      removeEventListener: (n: string) => delete ouvintes[n],
    } as unknown as Parameters<typeof guardarVoltar>[0];
    let perguntas = 0;
    const guarda = guardarVoltar(janela, () => perguntas++);
    // Liga: empilha uma entrada igual à da tela, com o state do Next.
    expect(pilha).toEqual([{ __NA: true, guardaFotos: true }]);
    // Voltar: pergunta.
    ouvintes.popstate!();
    expect(perguntas).toBe(1);
    // Ficar: empilha de novo e volta a perguntar no próximo Voltar.
    guarda.ficar();
    expect(pilha).toHaveLength(2);
    ouvintes.popstate!();
    expect(perguntas).toBe(2);
    // Sair: volta de verdade, sem perguntar outra vez.
    guarda.sair();
    expect(perguntas).toBe(2);
    guarda.desligar();
    expect(ouvintes.popstate).toBeUndefined();
  });

  it("test_vei_10_fila_vazia_tira_a_entrada_de_guarda_sem_perguntar", () => {
    const ouvintes: Record<string, () => void> = {};
    const estado = { atual: { __NA: true } as Record<string, unknown> };
    let voltas = 0;
    const janela = {
      location: { href: "https://locadora.giro.test/veiculos/novo" },
      history: {
        get state() {
          return estado.atual;
        },
        pushState: (s: Record<string, unknown>) => (estado.atual = s),
        back: () => {
          voltas++;
          estado.atual = { __NA: true };
          ouvintes.popstate?.();
        },
      },
      addEventListener: (n: string, f: () => void) => (ouvintes[n] = f),
      removeEventListener: (n: string) => delete ouvintes[n],
    } as unknown as Parameters<typeof guardarVoltar>[0];
    let perguntas = 0;
    // A fila esvazia com a guarda no topo: tira a entrada, uma volta, nenhuma pergunta.
    guardarVoltar(janela, () => perguntas++).desligar();
    expect(voltas).toBe(1);
    expect(perguntas).toBe(0);
    // Outra página já está no topo (a pessoa saiu por um link): não volta nada.
    const g = guardarVoltar(janela, () => perguntas++);
    estado.atual = { __NA: true };
    g.desligar();
    expect(voltas).toBe(1);
  });

  it("test_vei_10_fim_do_envio_depois_de_ficar_abre_a_ficha_sem_voltar_a_entrada", () => {
    // Cadastro gravado, a pessoa tocou "Ficar" e o envio terminou: a ficha entra no lugar da entrada de guarda
    // (router.replace) e a limpeza do aviso não pode chamar history.back(), que desfaria a navegação (A3, T-462).
    const ouvintes: Record<string, () => void> = {};
    const estado = { atual: { __NA: true } as Record<string, unknown> };
    let voltas = 0;
    const janela = {
      location: { href: "https://locadora.giro.test/veiculos/novo" },
      history: {
        get state() {
          return estado.atual;
        },
        pushState: (s: Record<string, unknown>) => (estado.atual = s),
        back: () => {
          voltas++;
          estado.atual = { __NA: true };
          ouvintes.popstate?.();
        },
      },
      addEventListener: (n: string, f: () => void) => (ouvintes[n] = f),
      removeEventListener: (n: string) => delete ouvintes[n],
    } as unknown as Parameters<typeof guardarVoltar>[0];
    let perguntas = 0;
    const guarda = guardarVoltar(janela, () => perguntas++);
    guarda.ficar(); // "Ficar" depois do Voltar: empilha de novo
    expect(guarda.entregar()).toBe(true);
    estado.atual = { __NA: true }; // o router.replace troca a entrada pela ficha
    guarda.desligar(); // limpeza do efeito quando a fila zera
    expect(voltas).toBe(0);
    expect(perguntas).toBe(0);
    expect(ouvintes.popstate).toBeUndefined();
  });
});
