// T-371 · Reembolsos (DEV-02) e pendências do pagamento (AUT-05, PLT-12) contra docs/telas/html/Reembolsos-*.dc.html e Pendencias-Pagamento-*.dc.html,
// com os números do seed de 07 out. Texto, indicadores e ações vêm da API (docs/api/financeiro.md, T-380); a tela só mostra.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, financeiro, ErroApi, type Eu, type ListaPendencias as DadosDePendencias, type ListaReembolsos as DadosDeReembolsos } from "@/lib/api";
import { hrefDoDestino, montarMenu, rotaPermitida } from "@/lib/menu";
import { reiniciarFinanceiroFalso } from "@/testes/falsos/falso-financeiro";
import { chamadasDePendencia, chamadasDeReembolso, planoDoFalso } from "@/testes/falsos/falso-reembolsos";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
const url = vi.hoisted(() => ({ params: "" }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/financeiro", useSearchParams: () => new URLSearchParams(url.params) }));

import { DialogoMarcarFeito } from "./DialogoMarcarFeito";
import { DialogoResolverPendencia } from "./DialogoResolverPendencia";
import { ListaPendencias } from "./ListaPendencias";
import { ListaReembolsos } from "./ListaReembolsos";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

async function paginaDeReembolsos(aba: "a_fazer" | "feito" | "todos" = "a_fazer", alterar?: (d: DadosDeReembolsos) => DadosDeReembolsos): Promise<string> {
  const cache = new QueryClient();
  url.params = aba === "a_fazer" ? "" : `aba=${aba}`;
  const dados = await financeiro.listarReembolsos({ status: aba });
  cache.setQueryData(["reembolsos", { aba, periodo: "mes", cursor: undefined, busca: "" }], alterar ? alterar(dados) : dados);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaReembolsos />
    </QueryClientProvider>,
  );
}

async function paginaDePendencias(aba: "aberta" | "resolvida" | "todas" = "aberta", alterar?: (d: DadosDePendencias) => DadosDePendencias): Promise<string> {
  const cache = new QueryClient();
  url.params = aba === "aberta" ? "" : `aba=${aba}`;
  const dados = await financeiro.listarPendencias({ status: aba });
  cache.setQueryData(["pendencias-pagamento", { aba, cursor: undefined, busca: "" }], alterar ? alterar(dados) : dados);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaPendencias />
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

beforeAll(() => entrar("financeiro@motorapida.com.br"));
beforeEach(() => reiniciarFinanceiroFalso());

describe("Reembolsos (DEV-02)", () => {
  it("dev_02_a_fazer: Juliana com R$ 183,00 a fazer, os textos da API e as duas ações", async () => {
    const h = await paginaDeReembolsos();
    const t = texto(h);
    for (const trecho of ["Reembolsos", "A reembolsar", "R$ 183,00", "1 cliente com devolução", "Juliana Rocha", "LOC-2836", "QXA-4B21 · Honda CG 160 Fan", "Devolução com caução", "Caução de R$ 600,00 menos diárias e acerto", "Pix", "A fazer", "Marcar como feito", "Ver acerto"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).toContain("A fazer 1");
    expect(t).toContain("Feitos 3");
    expect(t).toContain("Todos 4");
    expect(h).toContain('href="/locacoes/2836"');
    expect(t).not.toContain("Diego Santos");
  });

  it("dev_02_todos: os feitos mostram Feito com a data, o comprovante quando há, e só o a fazer tem o botão", async () => {
    const h = await paginaDeReembolsos("todos");
    const t = texto(h);
    for (const trecho of ["Diego Santos", "Estorno no cartão", "R$ 600,00", "Feito · 06 out", "Letícia Barbosa", "Locação cancelada antes da retirada", "Marcos Lima", "Dinheiro", "R$ 150,00", "Reembolsados no período", "R$ 1.100,00", "3 reembolsos feitos"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(h).toContain('href="/comprovantes/reembolso.pdf"');
    expect(h.match(/Marcar como feito/g)?.length).toBe(1 + 1); // o botão da Juliana e a nota de rodapé
  });

  it("plt_07_suporte: com acoes.marcar_feito false e sem comprovante, a tela não oferece o botão nem o arquivo", async () => {
    const h = await paginaDeReembolsos("todos", (d) => ({ ...d, resultados: d.resultados.map((r) => ({ ...r, acoes: { marcar_feito: false }, comprovante: null })) }));
    expect(h).not.toContain("wl-btn--solid");
    expect(h).not.toContain("Comprovante</a>");
    expect(texto(h)).toContain("Ver acerto");
  });

  it("lista vazia mostra a frase de vazio, sem tabela", async () => {
    const t = texto(await paginaDeReembolsos("a_fazer", (d) => ({ ...d, resultados: [] })));
    expect(t).toContain("Nenhum reembolso a fazer.");
  });

  it("dev_02_marcar_feito: manda o comprovante quando há e a segunda vez dá 409 transicao_reembolso", async () => {
    const feito = await financeiro.marcarReembolsoFeito(31, new File(["x"], "pix.pdf", { type: "application/pdf" }));
    expect(feito.status).toBe("feito");
    expect(feito.comprovante).not.toBeNull();
    expect(feito.acoes.marcar_feito).toBe(false);
    expect(chamadasDeReembolso).toEqual([{ id: 31, comprovante: true }]);
    const erro = await falha(financeiro.marcarReembolsoFeito(31));
    expect([erro.status, erro.codigo]).toEqual([409, "transicao_reembolso"]);
    const depois = await financeiro.listarReembolsos();
    expect(depois.indicadores.a_fazer.valor_centavos).toBe(0);
    expect(depois.contagens).toEqual({ a_fazer: 0, feito: 4, todos: 4 });
  });

  it("o diálogo diz quem recebe, o valor e que o comprovante é opcional", async () => {
    const [juliana] = (await financeiro.listarReembolsos()).resultados;
    const h = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <DialogoMarcarFeito reembolso={juliana!} aoFechar={() => {}} aoConcluir={() => {}} />
      </QueryClientProvider>,
    );
    const t = texto(h);
    expect(t).toContain("Marcar como feito");
    expect(t).toContain("Juliana Rocha · R$ 183,00 · Pix");
    expect(t).toContain("Comprovante (opcional)");
  });
});

describe("Pendências do pagamento (AUT-05)", () => {
  it("aut_05_abertas: indicadores, motivo e detalhe da API, valor do parceiro e Resolver", async () => {
    const t = texto(await paginaDePendencias());
    for (const trecho of ["Pendências do pagamento", "Pendências abertas", "R$ 628,40 em análise", "Resolvidas no mês", "1 resolvida no mês", "Carlos Menezes", "pay_88192", "LOC-2841 · parcela 2 de 5", "Valor pago diferente", "Pagou R$ 299,40; a conta estava em R$ 306,09 (falta R$ 6,69).", "R$ 299,40", "Aberta", "Resolver", "A conta já não estava aberta", "Roberto Dias"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).toContain("Abertas 2");
    expect(t).toContain("Resolvidas 1");
    expect(t).not.toContain("Rafael Sousa");
  });

  it("aut_05_resolvidas: mostra o texto de resolução que a API montou, sem botão Resolver", async () => {
    const h = await paginaDePendencias("resolvida");
    const t = texto(h);
    expect(t).toContain("Rafael Sousa");
    expect(t).toContain("Estornada no parceiro");
    expect(t).toContain("Ignorada: estorno registrado");
    expect(t).toContain("R$ 1.347,00");
    expect(h).not.toContain("wl-btn--solid");
  });

  it("plt_07_suporte: com acoes.resolver false a tela não oferece Resolver", async () => {
    const h = await paginaDePendencias("aberta", (d) => ({ ...d, resultados: d.resultados.map((p) => ({ ...p, acoes: { resolver: false, baixar: false } })) }));
    expect(h).not.toContain("wl-btn--solid");
    expect(texto(h)).toContain("Carlos Menezes");
  });

  it("aut_05_dialogo_baixar: com a conta aberta oferece Baixar e Ignorar; sem ela, só Ignorar", async () => {
    const [carlos, roberto] = (await financeiro.listarPendencias()).resultados;
    const abrir = (p: NonNullable<typeof carlos>) =>
      texto(
        renderToStaticMarkup(
          <QueryClientProvider client={new QueryClient()}>
            <DialogoResolverPendencia pendencia={p} aoFechar={() => {}} aoConcluir={() => {}} />
          </QueryClientProvider>,
        ),
      );
    const comConta = abrir(carlos!);
    expect(comConta).toContain("Baixar a conta");
    expect(comConta).toContain("Ignorar o aviso");
    expect(comConta).toContain("Pagou R$ 299,40; a conta estava em R$ 306,09 (falta R$ 6,69).");
    const semConta = abrir(roberto!);
    expect(semConta).not.toContain("Baixar a conta");
    expect(semConta).toContain("A conta não está mais aberta, por isso só dá para ignorar o aviso.");
  });

  it("aut_05_resolver: manda a ação e o motivo; sem motivo 400; já resolvida 409; baixar sem conta aberta 409", async () => {
    const sem = await falha(financeiro.resolverPendencia(12, { acao: "baixar", motivo: " " }));
    expect([sem.status, sem.campos?.motivo]).toEqual([400, "Informe o motivo."]);
    const baixada = await financeiro.resolverPendencia(12, { acao: "baixar", motivo: "diferença paga no caixa" });
    expect(baixada.status).toBe("resolvida");
    expect(baixada.resolucao?.texto).toBe("Baixada: diferença paga no caixa");
    expect(chamadasDePendencia.at(-1)).toEqual({ id: 12, acao: "baixar", motivo: "diferença paga no caixa" });
    const jaResolvida = await falha(financeiro.resolverPendencia(12, { acao: "ignorar", motivo: "de novo" }));
    expect([jaResolvida.status, jaResolvida.codigo]).toEqual([409, "transicao_pendencia"]);
    const semConta = await falha(financeiro.resolverPendencia(11, { acao: "baixar", motivo: "tentativa" }));
    expect([semConta.status, semConta.codigo]).toEqual([409, "transicao_conta"]);
    const lista = await financeiro.listarPendencias();
    expect(lista.contagens).toEqual({ aberta: 1, resolvida: 2, todas: 3 });
  });

  it("plt_12_essencial: a API recusa com 403 PLT-12 e o menu do plano não tem o item nem libera a rota", async () => {
    planoDoFalso.essencial = true;
    const erro = await falha(financeiro.listarPendencias());
    expect([erro.status, erro.codigo]).toEqual([403, "PLT-12"]);
    const eu = sessao.eu as Eu;
    const semItem = { ...eu, navegacao: { ...eu.navegacao, menu_completo: eu.navegacao.menu_completo.map((g) => ({ ...g, itens: g.itens.filter((i) => i.chave !== "pendencias_pagamento") })) } };
    expect(rotaPermitida(semItem, "/financeiro/pendencias-pagamento")).toBe(false);
  });
});

describe("Menu e Para hoje (T-371)", () => {
  it("os itens da API viram links para as duas rotas", async () => {
    const grupos = [{ grupo: "Financeiro", itens: [{ chave: "reembolsos", rotulo: "Reembolsos", contador: null }, { chave: "pendencias_pagamento", rotulo: "Pendências do pagamento", contador: null }] }] as Parameters<typeof montarMenu>[0];
    const itens = montarMenu(grupos, "/financeiro/reembolsos")[0]!.itens;
    expect(itens.map((i) => [i.chave, i.href, i.ativo])).toEqual([
      ["reembolsos", "/financeiro/reembolsos", true],
      ["pendencias_pagamento", "/financeiro/pendencias-pagamento", false],
    ]);
  });

  it("o destino do Para hoje (reembolsos, id 31) leva à lista, que não tem página de detalhe", () => {
    expect(hrefDoDestino("reembolsos", undefined, 31)).toBe("/financeiro/reembolsos");
  });
});
