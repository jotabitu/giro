// Movimentações (T-289) contra docs/telas/html/Movimentacoes-*, Movimentacao-Nova-* e Movimentacao-Chegada-Mobile, com o seed de 07 out
// da camada provisória (MOV-01 a MOV-06). A tela mostra o que a API manda; aqui a API é a de exemplo do contrato.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, ErroApi, movimentacoes, type Eu, type LinhaDaMovimentacao } from "@/lib/api";
import { reiniciarMovimentacoesDeExemplo } from "@/testes/falsos/falso-movimentacoes";
import { esquemaMovimentacao, paraCorpoMovimentacao, campoDoFormulario, VALORES_INICIAIS_MOVIMENTACAO } from "@/lib/movimentacao-form";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/movimentacoes", useSearchParams: () => new URLSearchParams() }));

import { CartaoDaMovimentacao } from "./CartaoDaMovimentacao";
import { NovaMovimentacao } from "./NovaMovimentacao";
import { QuadroDeMovimentacoes } from "./QuadroDeMovimentacoes";
import { RegistrarChegada } from "./RegistrarChegada";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function entrarComo(email: string, movimentar: "gerir" | "levar" | "nao") {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
  sessao.eu = { ...r.usuario, pode: { ...r.usuario.pode, movimentacoes: movimentar } };
}

const comCache = (cache: QueryClient, filho: React.ReactNode) => renderToStaticMarkup(<QueryClientProvider client={cache}>{filho}</QueryClientProvider>);

async function quadro(): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["movimentacoes", "quadro"], await movimentacoes.quadro());
  return comCache(cache, <QuadroDeMovimentacoes />);
}

async function chegada(id: number): Promise<string> {
  const cache = new QueryClient();
  const m = await movimentacoes.obter(id);
  cache.setQueryData(["movimentacoes", "detalhe", id], m);
  cache.setQueryData(["movimentacoes", "recebem", id], (await movimentacoes.recebedores(id)).resultados);
  return comCache(cache, <RegistrarChegada id={id} />);
}

beforeEach(() => {
  reiniciarMovimentacoesDeExemplo();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-07T14:24:00Z"));
});
afterEach(() => vi.useRealTimers());

describe("quadro das movimentações (Movimentacoes)", () => {
  it("cabeçalho e as quatro colunas com a contagem da API", async () => {
    await entrarComo("rodrigo@motorapida.com.br", "gerir");
    const t = texto(await quadro());
    for (const trecho of ["Movimentações", "Levar veículos entre filiais, lava-jato, oficina e despachante", "Agendadas", "Em trânsito", "No local de apoio", "Concluídas", "Nova movimentação", "Nenhum veículo em local de apoio."]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("os três cartões do seed: rota, placa, quem leva e o resumo pronto da API", async () => {
    await entrarComo("rodrigo@motorapida.com.br", "gerir");
    const t = texto(await quadro());
    for (const trecho of [
      "MOV-0003", "Honda Pop 110i", "Centro → Moto Peças CE → Centro", "PMZ-3E17", "João", "amanhã 08:00",
      "MOV-0002", "Honda CG 160 Fan", "Centro → Lava Rápido Aldeota → Filial Caucaia", "SAK-1D39", "saiu 10:02 · 1 parada",
      "MOV-0001", "Centro → Lava Rápido Aldeota → Centro", "hoje 08:30 · 1 h 10 min", "R$ 35,00",
    ]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("mov_02: cada cartão mostra só os botões que `acoes` manda", async () => {
    await entrarComo("rodrigo@motorapida.com.br", "gerir");
    const q = await movimentacoes.quadro();
    const [agendadas, emTransito, , concluidas] = q.colunas.map((c) => c.itens[0]!) as [LinhaDaMovimentacao, LinhaDaMovimentacao, LinhaDaMovimentacao | undefined, LinhaDaMovimentacao];
    const html = (m: LinhaDaMovimentacao) => renderToStaticMarkup(<CartaoDaMovimentacao m={m} ocupado={false} aoIniciar={() => {}} aoCancelar={() => {}} />);
    expect(texto(html(agendadas))).toContain("Iniciar");
    expect(texto(html(agendadas))).toContain("Cancelar");
    expect(texto(html(agendadas))).not.toContain("Registrar chegada");
    expect(texto(html(emTransito))).toContain("Registrar chegada");
    expect(html(emTransito)).toContain("/veiculos/movimentacoes/2/chegada");
    expect(texto(html(emTransito))).not.toContain("Iniciar");
    expect(texto(html(concluidas))).not.toMatch(/Iniciar|Cancelar|Registrar chegada/);
  });

  it("quem só leva não vê Nova movimentação (pode.movimentacoes = levar)", async () => {
    await entrarComo("joao@motorapida.com.br", "levar");
    const t = texto(await quadro());
    expect(t).not.toContain("Nova movimentação");
    expect(t).toContain("MOV-0002");
  });
});

describe("registrar chegada (Movimentacao-Chegada-Mobile)", () => {
  it("transferência com vistoria rápida: percurso, km, combustível, fotos 2 de 4 e quem recebe", async () => {
    await entrarComo("rodrigo@motorapida.com.br", "gerir");
    const t = texto(await chegada(2));
    for (const trecho of [
      "Registrar chegada", "MOV-0002", "Honda CG 160 Fan", "SAK-1D39",
      "Filial Centro", "saiu 10:02 · 3.120 km", "Lava Rápido Aldeota", "lavagem completa · 10:15 a 10:58 · despesa lançada", "R$ 35,00",
      "Filial Caucaia", "chegando agora · 11:24",
      "Km na chegada", "não pode ser menor que 3.120", "Combustível", "Res.", "1/4", "1/2", "3/4", "Cheio",
      "Fotos · 2 de 4", "Frente", "Traseira", "Esquerda", "Direita", "Recebido por", "Usuário da Filial Caucaia.", "Confirmar chegada",
    ]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("movimentação que não espera chegada não mostra o formulário", async () => {
    await entrarComo("rodrigo@motorapida.com.br", "gerir");
    const t = texto(await chegada(1));
    expect(t).toContain("Esta movimentação não espera chegada agora.");
    expect(t).not.toContain("Confirmar chegada");
  });
});

describe("nova movimentação (Movimentacao-Nova)", () => {
  it("as três seções, o destino e as opções de quando", async () => {
    await entrarComo("rodrigo@motorapida.com.br", "gerir");
    const t = texto(comCache(new QueryClient(), <NovaMovimentacao />));
    for (const trecho of ["Nova movimentação", "1 · Veículo", "2 · Para onde vai", "Saída", "Adicionar parada", "Destino", "Filial de destino", "O destino é sempre uma filial.", "3 · Quando e quem leva", "Sair agora", "Agendar", "Quem leva", "Vistoria rápida na chegada", "Cancelar"]) {
      expect(t, trecho).toContain(trecho);
    }
    // MOV-04 e CA-246-07: no MVP a parada não tem ordem de serviço.
    expect(t).not.toContain("Ordem de serviço");
  });
});

describe("formulário da Nova movimentação (MOV-01)", () => {
  const base = { ...VALORES_INICIAIS_MOVIMENTACAO, veiculo_id: "503", destino_filial_id: "1", levado_por_id: "4" };

  it("falta veículo, destino e quem leva", () => {
    const r = esquemaMovimentacao.safeParse(VALORES_INICIAIS_MOVIMENTACAO);
    expect(r.success).toBe(false);
    const campos = r.success ? [] : r.error.issues.map((i) => i.path.join("."));
    expect(campos).toEqual(expect.arrayContaining(["veiculo_id", "destino_filial_id", "levado_por_id"]));
  });

  it("agendar pede dia e hora; sair agora não pede", () => {
    expect(esquemaMovimentacao.safeParse({ ...base, quando: "agora" }).success).toBe(true);
    const r = esquemaMovimentacao.safeParse({ ...base, quando: "agendar" });
    expect(r.success).toBe(false);
    expect(r.success ? [] : r.error.issues.map((i) => i.path.join("."))).toEqual(["dia", "hora"]);
  });

  it("parada pede local e serviço, e o valor tem de ser um valor", () => {
    const r = esquemaMovimentacao.safeParse({ ...base, paradas: [{ local_id: "", servico: " ", valor_previsto: "abc" }] });
    expect(r.success ? [] : r.error.issues.map((i) => i.path.join("."))).toEqual(["paradas.0.local_id", "paradas.0.servico", "paradas.0.valor_previsto"]);
  });

  it("corpo do POST: centavos, hora de Brasília em UTC, sem categoria da parada", () => {
    const corpo = paraCorpoMovimentacao({
      ...base,
      paradas: [{ local_id: "5", servico: " Revisão ", valor_previsto: "120,00" }],
      quando: "agendar",
      dia: "2026-10-08",
      hora: "08:00",
    });
    expect(corpo).toEqual({
      veiculo_id: 503,
      paradas: [{ local_id: 5, servico: "Revisão", valor_previsto_centavos: 12000 }],
      destino_filial_id: 1,
      categoria_destino_id: null,
      levado_por_id: 4,
      sair_agora: false,
      agendada_para: "2026-10-08T11:00:00.000Z",
      vistoria_rapida: false,
    });
  });

  it("campos da API voltam nos campos certos", () => {
    expect(campoDoFormulario("paradas[1].local_id")).toBe("paradas.1.local_id");
    expect(campoDoFormulario("paradas[0].valor_previsto_centavos")).toBe("paradas.0.valor_previsto");
    expect(campoDoFormulario("levado_por_id")).toBe("levado_por_id");
    expect(campoDoFormulario("agendada_para")).toBe("dia");
    expect(campoDoFormulario("qualquer_outro")).toBe("");
  });
});

describe("camada de exemplo do contrato (provisória)", () => {
  it("mov_03: uma movimentação aberta por veículo (409 MOV-03)", async () => {
    const corpo = { veiculo_id: 503, paradas: [], destino_filial_id: 1, categoria_destino_id: null, levado_por_id: 4, sair_agora: true, agendada_para: null, vistoria_rapida: false };
    await expect(movimentacoes.criar(corpo)).rejects.toMatchObject({ status: 409, codigo: "MOV-03", message: "O veículo já está na MOV-0003." });
  });

  it("mov_02: só a agendada inicia e cancela; as outras dão 409 transicao_movimentacao", async () => {
    await expect(movimentacoes.iniciar(2)).rejects.toMatchObject({ status: 409, codigo: "transicao_movimentacao" });
    await expect(movimentacoes.cancelar(2, "x")).rejects.toMatchObject({ status: 409, codigo: "transicao_movimentacao" });
    const m = await movimentacoes.iniciar(3);
    expect(m.status).toBe("em_transito");
    expect(m.acoes.registrar_chegada).toBe(false);
    expect(m.acoes.chegar_parada).toBe(true);
  });

  it("mov_05: a chegada com vistoria rápida pede combustível, as 4 fotos e quem recebe; o km não diminui", async () => {
    const erro = await movimentacoes.registrarChegada(2, { km: 3146 }).catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect((erro as ErroApi).campos).toEqual({ combustivel: "Informe o combustível.", fotos: "Faltam 2 fotos.", recebido_por_id: "Informe quem recebe o veículo." });
    await expect(movimentacoes.registrarChegada(2, { km: 3000, combustivel: "cheio", recebido_por_id: 9 }).catch((e: unknown) => e)).resolves.toMatchObject({ campos: expect.any(Object) });
    const arquivo = new File(["x"], "f.jpg", { type: "image/jpeg" });
    await movimentacoes.enviarFotoDaChegada(2, "traseira", arquivo);
    await movimentacoes.enviarFotoDaChegada(2, "lado_esquerdo", arquivo);
    await expect(movimentacoes.registrarChegada(2, { km: 3000, combustivel: "cheio", recebido_por_id: 9 })).rejects.toMatchObject({ status: 422, codigo: "VEI-01", message: "O km informado é menor que o atual (3.120)." });
    const m = await movimentacoes.registrarChegada(2, { km: 3146, combustivel: "cheio", recebido_por_id: 9 });
    expect(m.status).toBe("concluida");
    expect(m.chegada?.km).toBe(3146);
  });

  it("mov_01: local de apoio com nome único (409 local_existente)", async () => {
    await expect(movimentacoes.criarLocal({ nome: "  lava rápido aldeota ", tipo: "lava_jato" })).rejects.toMatchObject({ status: 409, codigo: "local_existente" });
    const novo = await movimentacoes.criarLocal({ nome: "Despachante Norte", tipo: "despachante" });
    expect((await movimentacoes.locais()).resultados.map((l) => l.id)).toContain(novo.id);
  });
});
