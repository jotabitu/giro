// T-437 · Fotos do veículo no cadastro (VEI-10, "Galeria no cadastro"). Critérios: docs/qa/criterios/T-437.md (CA-437-01 a 13).
// Contrato: docs/api/veiculos.md, "Fotos do veículo" (não muda). O cadastro usa POST /api/veiculos/ e, depois do 201,
// POST /api/veiculos/{id}/fotos/ uma foto por vez.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, ErroApi, veiculos, type Eu, type NovoVeiculo } from "@/lib/api";
import { definirLimiteDoPlanoFalso } from "@/testes/falsos/falso-frota";
import {
  andamentoDoEnvio,
  cadastrarComFotos,
  capaDaLista,
  EnvioDasFotos,
  enviarEmSequencia,
  envioTerminouBem,
  escolherFotos,
  FOTO_INVALIDA,
  FotosEscolhidas,
  itensDoEnvio,
  ordemDeEnvio,
  SEM_CONEXAO,
  type FotoEscolhida,
  type ItemDoEnvio,
} from "./FotosDoCadastro";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {}, replace: () => {} }), usePathname: () => "/veiculos/novo", useSearchParams: () => new URLSearchParams() }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { NovoVeiculoForm } from "./NovoVeiculoForm";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

const html = (el: ReactElement) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const arquivo = (nome: string, bytes = 10) => new File([new Uint8Array(bytes)], nome, { type: /\.png$/.test(nome) ? "image/png" : /\.jpe?g$/.test(nome) ? "image/jpeg" : "" });
const nomes = (l: { arquivo: File }[]) => l.map((f) => f.arquivo.name);

// Honda Pop 110i, placa TBC-5H21, na Urbana 110–125 (Filial Centro).
const TBC: NovoVeiculo = { placa: "TBC5H21", chassi: "9C2JC7500TR012345", marca: "Honda", modelo: "Pop 110i ES", ano_fabricacao: 2026, ano_modelo: 2026, cor: "Preta", km_atual: 0, categoria_id: 1, filial_id: 1 };

describe("antes de salvar (escolha)", () => {
  it("test_vei_10_cadastro_escolher_sem_enviar (CA-437-01): três escolhidas, a 1ª é a capa, e nada é chamado na API", () => {
    const envio = vi.spyOn(veiculos, "enviarFoto");
    const r = escolherFotos([], [arquivo("moto-1.jpg"), arquivo("moto-2.jpg"), arquivo("moto.png")]);
    expect(nomes(r.lista)).toEqual(["moto-1.jpg", "moto-2.jpg", "moto.png"]);
    expect(r.recusas).toEqual([]);
    expect(capaDaLista(r.lista, null)).toBe(r.lista[0]!.chave);
    expect(envio).not.toHaveBeenCalled();
    envio.mockRestore();

    const t = texto(html(<FotosEscolhidas fotos={r.lista} capa={null} recusas={[]} passouDoLimite={false} aoEscolher={() => {}} aoTirar={() => {}} aoUsarComoCapa={() => {}} aoDispensarRecusas={() => {}} />));
    expect(t).toContain("Fotos do veículo");
    expect(t).toContain("3 de 20 fotos");
    expect(t).toContain("moto-1.jpg");
    expect(t.match(/\|Capa\|/g)?.length).toBeGreaterThan(0);
    expect(t.match(/Usar como capa/g)).toHaveLength(2);
    expect(t.match(/Tirar/g)).toHaveLength(3);
  });

  it("test_vei_10_cadastro_tirar_e_escolher_a_capa (CA-437-02): tira moto-2.jpg, marca moto.png, e moto.png sobe primeiro", () => {
    const { lista } = escolherFotos([], [arquivo("moto-1.jpg"), arquivo("moto-2.jpg"), arquivo("moto.png")]);
    const semMoto2 = lista.filter((f) => f.arquivo.name !== "moto-2.jpg");
    const capa = semMoto2.find((f) => f.arquivo.name === "moto.png")!.chave;
    expect(nomes(semMoto2)).toEqual(["moto-1.jpg", "moto.png"]);
    expect(nomes(ordemDeEnvio(semMoto2, capa))).toEqual(["moto.png", "moto-1.jpg"]);
    // Tirada a capa, a primeira da lista volta a ser a capa.
    expect(capaDaLista(semMoto2.filter((f) => f.chave !== capa), capa)).toBe(semMoto2[0]!.chave);
  });

  it("test_vei_10_cadastro_limite_de_20_na_escolha (CA-437-03): de moto-1 a moto-21 entram 20, e a tela avisa", () => {
    const todos = Array.from({ length: 21 }, (_, i) => arquivo(`moto-${i + 1}.jpg`));
    const r = escolherFotos([], todos);
    expect(r.lista).toHaveLength(20);
    expect(r.passouDoLimite).toBe(true);
    expect(nomes(r.lista).at(-1)).toBe("moto-20.jpg");
    const t = texto(html(<FotosEscolhidas fotos={r.lista} capa={null} recusas={[]} passouDoLimite aoEscolher={() => {}} aoTirar={() => {}} aoUsarComoCapa={() => {}} aoDispensarRecusas={() => {}} />));
    expect(t).toContain("O veículo pode ter até 20 fotos.");
    expect(t).toContain("20 de 20 fotos");
    expect(t).toContain("Tire uma foto da lista para escolher outra");
    expect(t).not.toContain("Selecionar fotos");
    // Com a lista cheia, escolher mais não entra.
    expect(escolherFotos(r.lista, [arquivo("moto-21.jpg")]).lista).toHaveLength(20);
  });

  it("test_vei_10_cadastro_arquivo_recusado_na_escolha (CA-437-04): grande.jpg, moto.heic e documento.pdf ficam de fora, as outras seguem", () => {
    const r = escolherFotos([], [arquivo("moto-1.jpg"), arquivo("grande.jpg", 11 * 1024 * 1024), arquivo("moto.heic"), arquivo("documento.pdf"), arquivo("moto.png")]);
    expect(nomes(r.lista)).toEqual(["moto-1.jpg", "moto.png"]);
    expect(r.recusas.map((x) => [x.nome, x.mensagem])).toEqual([
      ["grande.jpg", FOTO_INVALIDA],
      ["moto.heic", FOTO_INVALIDA],
      ["documento.pdf", FOTO_INVALIDA],
    ]);
    const t = texto(html(<FotosEscolhidas fotos={r.lista} capa={null} recusas={r.recusas} passouDoLimite={false} aoEscolher={() => {}} aoTirar={() => {}} aoUsarComoCapa={() => {}} aoDispensarRecusas={() => {}} />));
    expect(t).toContain("grande.jpg|: Envie uma foto JPG ou PNG de até 10 MB.");
  });
});

describe("salvar (API falsa)", () => {
  beforeAll(() => entrarComo("mariana@motorapida.com.br"));

  const escolhidas = (): { lista: FotoEscolhida[]; capa: string } => {
    const { lista } = escolherFotos([], [arquivo("moto-1.jpg"), arquivo("moto-2.jpg"), arquivo("moto.png")]);
    return { lista, capa: lista[2]!.chave };
  };

  it("test_vei_10_cadastro_com_fotos (CA-437-05): 201 e depois três envios, moto.png primeiro; andamento 1 de 3 a 3 de 3; galeria com moto.png capa", async () => {
    const { lista, capa } = escolhidas();
    const ordem: string[] = [];
    const andamentos: string[] = [];
    const { criado, itens } = await cadastrarComFotos(
      () => veiculos.criar(TBC),
      itensDoEnvio(lista, capa),
      (id, a) => {
        ordem.push(a.name);
        return veiculos.enviarFoto(id, a);
      },
      () => ordem.push("cadastro"),
      (agora) => andamentos.push(andamentoDoEnvio(agora)),
    );
    expect(ordem).toEqual(["cadastro", "moto.png", "moto-1.jpg", "moto-2.jpg"]);
    expect(andamentos).toContain("Enviando fotos · 1 de 3");
    expect(andamentos).toContain("Enviando fotos · 3 de 3");
    expect(envioTerminouBem(itens)).toBe(true);
    const g = await veiculos.fotos(criado.id);
    expect(g.total).toBe(3);
    expect(g.fotos[0]?.capa).toBe(true);
  });

  it("test_vei_10_cadastro_sem_fotos (CA-437-06): sem escolha, só o cadastro, e a galeria fica vazia", async () => {
    const envio = vi.fn();
    const { criado, itens } = await cadastrarComFotos(() => veiculos.criar({ ...TBC, placa: "TBC5H22", chassi: "9C2JC7500TR012346" }), [], envio, () => {}, () => {});
    expect(envio).not.toHaveBeenCalled();
    expect(envioTerminouBem(itens)).toBe(true);
    expect((await veiculos.fotos(criado.id)).total).toBe(0);
  });

  it("test_vei_10_cadastro_falha_fotos_ficam (CA-437-07): SAK-1D39 responde 409 VEI-01, nenhuma foto sai; com outra placa sobe com as mesmas", async () => {
    const { lista } = escolherFotos([], [arquivo("moto-1.jpg"), arquivo("moto-2.jpg")]);
    const envio = vi.fn((id: number, a: File) => veiculos.enviarFoto(id, a));
    const e = await cadastrarComFotos(() => veiculos.criar({ ...TBC, placa: "SAK1D39", chassi: "9C2JC7500TR012347" }), itensDoEnvio(lista, null), envio, () => {}, () => {}).catch((x: unknown) => x);
    expect(e).toBeInstanceOf(ErroApi);
    expect((e as ErroApi).status).toBe(409);
    expect((e as ErroApi).codigo).toBe("VEI-01");
    expect(envio).not.toHaveBeenCalled();
    // A mesma lista, sem escolher de novo.
    const { criado } = await cadastrarComFotos(() => veiculos.criar({ ...TBC, placa: "TBC5H23", chassi: "9C2JC7500TR012347" }), itensDoEnvio(lista, null), envio, () => {}, () => {});
    expect(envio).toHaveBeenCalledTimes(2);
    expect((await veiculos.fotos(criado.id)).total).toBe(2);
  });

  it("test_vei_10_cadastro_limite_do_plano (CA-437-08): 422 PLT-03 e nenhuma foto enviada", async () => {
    definirLimiteDoPlanoFalso(1);
    try {
      const envio = vi.fn();
      const e = await cadastrarComFotos(() => veiculos.criar({ ...TBC, placa: "TBC5H24", chassi: "9C2JC7500TR012348" }), itensDoEnvio(escolhidas().lista, null), envio, () => {}, () => {}).catch((x: unknown) => x);
      expect((e as ErroApi).codigo).toBe("PLT-03");
      expect(envio).not.toHaveBeenCalled();
    } finally {
      definirLimiteDoPlanoFalso(150);
    }
  });
});

describe("depois de salvar (envio uma a uma)", () => {
  const itens = (): ItemDoEnvio[] => itensDoEnvio(escolherFotos([], [arquivo("moto.png"), arquivo("moto-1.jpg"), arquivo("moto-2.jpg")]).lista, null);
  const recusa400 = new ErroApi(400, "validacao", "Dados inválidos.", undefined, { arquivo: FOTO_INVALIDA });
  const semRede = new ErroApi(0, "sem_conexao", "Sem conexão com o servidor. Confira a internet e tente de novo.");

  it("test_vei_10_cadastro_foto_recusada_depois_de_salvar (CA-437-09): a recusa marca o item, as outras sobem, e a tela para com Ir para o veículo", async () => {
    const subiram: string[] = [];
    const fim = await enviarEmSequencia(itens(), async (a) => {
      if (a.name === "moto-1.jpg") throw recusa400;
      subiram.push(a.name);
    }, () => {});
    expect(subiram).toEqual(["moto.png", "moto-2.jpg"]);
    expect(fim.map((i) => i.estado)).toEqual(["enviada", "recusada", "enviada"]);
    expect(fim[1]?.mensagem).toBe(FOTO_INVALIDA);
    expect(envioTerminouBem(fim)).toBe(false);
    const t = texto(html(<EnvioDasFotos itens={fim} placa="TBC-5H21" veiculoId={600} aoTentarDeNovo={() => {}} />));
    expect(t).toContain("Fotos enviadas · 2 de 3");
    expect(t).toContain("Envie uma foto JPG ou PNG de até 10 MB.");
    expect(t).toContain("Ir para o veículo");
    expect(t).not.toContain("Tentar de novo");
    expect(html(<EnvioDasFotos itens={fim} placa="TBC-5H21" veiculoId={600} aoTentarDeNovo={() => {}} />)).toContain('href="/veiculos/600"');
  });

  it("test_vei_10_cadastro_falha_de_conexao (CA-437-10): cai na 2ª, para ali com Tentar de novo; retomar envia só as que faltam", async () => {
    const subiram: string[] = [];
    let cair = true;
    const enviar = async (a: File) => {
      if (a.name === "moto-1.jpg" && cair) {
        cair = false;
        throw semRede;
      }
      subiram.push(a.name);
    };
    const parado = await enviarEmSequencia(itens(), enviar, () => {});
    expect(parado.map((i) => i.estado)).toEqual(["enviada", "sem_conexao", "fila"]);
    expect(parado[1]?.mensagem).toBe(SEM_CONEXAO);
    expect(andamentoDoEnvio(parado)).toBe("Enviando fotos · parou na 2 de 3");
    const t = texto(html(<EnvioDasFotos itens={parado} placa="TBC-5H21" veiculoId={600} aoTentarDeNovo={() => {}} />));
    expect(t).toContain("Tentar de novo");
    expect(t).toContain("Ir para o veículo");
    expect(t).toContain("Na fila");

    const fim = await enviarEmSequencia(parado, enviar, () => {});
    expect(subiram).toEqual(["moto.png", "moto-1.jpg", "moto-2.jpg"]);
    expect(envioTerminouBem(fim)).toBe(true);
  });

  it("test_vei_10_cadastro_andamento_enquanto_envia (CA-437-11): enviando mostra o andamento e avisa que o veículo já está gravado", () => {
    const l = itens().map((it, i): ItemDoEnvio => ({ ...it, estado: i === 0 ? "enviada" : i === 1 ? "enviando" : "fila" }));
    expect(andamentoDoEnvio(l)).toBe("Enviando fotos · 2 de 3");
    const t = texto(html(<EnvioDasFotos itens={l} placa="TBC-5H21" veiculoId={600} aoTentarDeNovo={() => {}} />));
    expect(t).toContain("O veículo TBC-5H21 já está gravado. Se você sair agora, ele fica com as fotos que já subiram.");
    expect(t).toContain("Enviada");
    expect(t).not.toContain("Ir para o veículo");
  });
});

describe("tela Cadastrar veículo com o bloco de fotos", () => {
  it("test_vei_10_cadastro_bloco_de_fotos_para_quem_cadastra (CA-437-12): o gerente vê Fotos do veículo; o painel de documentos não manda mais as fotos para a ficha", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const t = texto(html(<NovoVeiculoForm />));
    expect(t).toContain("Fotos do veículo");
    expect(t).toContain("Escolha agora. As fotos são enviadas logo depois de Salvar veículo, a capa primeiro.");
    expect(t).toContain("0 de 20 fotos");
    expect(t).not.toContain("o seguro e as fotos na ficha");
  });

  it("test_vei_10_cadastro_suporte_nao_ve_o_bloco_de_fotos (CA-437-12, PLT-07)", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    sessao.eu = { ...(sessao.eu as Eu), suporte: { acesso_suporte_id: 1, nome: "Equipe Giro", permissao: "ver_editar", fim: "2026-11-10T20:00:00Z", motivo: "Ajuda no cadastro" } };
    const t = texto(html(<NovoVeiculoForm />));
    expect(t).toContain("Cadastrar veículo");
    expect(t).not.toContain("Fotos do veículo");
  });
});
