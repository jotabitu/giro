import { beforeAll, describe, expect, it } from "vitest";
import { clientes, contas, locacoes, vistorias, ErroApi } from "@/lib/api";
import { corpoDaLocacao, valoresIniciais } from "@/lib/locacao-form";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}
const imagem = (nome = "f.jpg", tipo = "image/jpeg") => new File([new Uint8Array(10)], nome, { type: tipo });
const pendencias = (e: unknown) => ((e as ErroApi).detalhes?.pendencias as { codigo: string }[]).map((p) => p.codigo);

describe("vistoria de saída (VIS-01 a VIS-04, VEI-01, CLI-03)", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));

  it("concluir devolve todas as pendências de uma vez, na mensagem do 422", async () => {
    const e = await vistorias.concluir(3001).catch((x) => x as ErroApi);
    expect(e).toMatchObject({ status: 422, message: "Resolva as 3 pendências antes de concluir" });
    expect(pendencias(e)).toEqual(["VIS-01", "VIS-02", "CLI-03"]);
  });

  it("foto que não é JPG nem PNG, ou passa de 10 MB, responde 400 no campo do arquivo", async () => {
    await expect(vistorias.enviarFoto(3001, "lado_direito", imagem("a.pdf", "application/pdf"))).rejects.toMatchObject({ status: 400, campos: { arquivo: expect.any(String) } });
    const grande = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "g.jpg", { type: "image/jpeg" });
    await expect(vistorias.enviarFoto(3001, "lado_direito", grande)).rejects.toMatchObject({ status: 400 });
  });

  it("foto de posição fixa substitui a anterior; a de avaria acumula", async () => {
    await vistorias.enviarFoto(3001, "frente", imagem());
    await vistorias.enviarFoto(3001, "avaria", imagem());
    await vistorias.enviarFoto(3001, "avaria", imagem());
    const v = await vistorias.obter(3001);
    expect(v.fotos.filter((f) => f.posicao === "frente")).toHaveLength(1);
    expect(v.fotos.filter((f) => f.posicao === "avaria")).toHaveLength(2);
    expect(v.fotos_obrigatorias).toMatchObject({ feitas: 3, total: 5, faltam: ["lado_direito", "painel"] });
    expect(v.pendencias[0]).toBe("fotos");
  });

  it("a avaria precisa de foto da mesma vistoria; o vistoriador não informa valor", async () => {
    await expect(vistorias.registrarAvaria(3001, { descricao: "Riscos", foto_id: 1 })).rejects.toMatchObject({ status: 400, campos: { foto_id: expect.any(String) } });
    const v = await vistorias.obter(3001);
    const f = v.fotos.find((x) => x.posicao === "avaria");
    await expect(vistorias.registrarAvaria(3001, { descricao: "Riscos", foto_id: f?.id ?? 0, valor_centavos: 500 })).rejects.toMatchObject({ status: 400 });
    const com = await vistorias.registrarAvaria(3001, { descricao: "Risco na carenagem", foto_id: f?.id ?? 0 });
    expect(com.avarias.map((a) => a.descricao)).toContain("Risco na carenagem");
    expect(com.avarias.at(-1)?.preexistente).toBe(true);
  });

  it("km menor que o do veículo recusa com VEI-01 e o km atual", async () => {
    await vistorias.editar(3001, { km: 3000 });
    const e = await vistorias.concluir(3001).catch((x) => x as ErroApi);
    expect(pendencias(e)).toContain("VEI-01");
    const p = ((e as ErroApi).detalhes?.pendencias as { codigo: string; km_atual?: number }[]).find((x) => x.codigo === "VEI-01");
    expect(p?.km_atual).toBe(3118);
  });

  it("fluxo completo com cliente ativo: concluir grava o km da saída e a vistoria não se edita mais (409)", async () => {
    const corpo = corpoDaLocacao(valoresIniciais(1201, 509, new Date("2026-10-07T12:20:00Z")), [])!;
    const rascunho = await locacoes.criar(corpo);
    await locacoes.confirmar(rascunho.id);
    const v = await vistorias.iniciarSaida(rascunho.id);
    expect(v.status).toBe("rascunho");
    expect(v.itens.map((i) => i.rotulo)).toContain("Pneus e freios");
    expect((await vistorias.iniciarSaida(rascunho.id)).id).toBe(v.id);
    for (const p of ["frente", "traseira", "lado_esquerdo", "lado_direito", "painel"] as const) await vistorias.enviarFoto(v.id, p, imagem());
    await vistorias.editar(v.id, { km: 7500, combustivel: "cheio", itens: v.itens.map((i) => ({ codigo: i.codigo, ok: true })) });
    expect((await vistorias.obter(v.id)).pode_concluir).toBe(true);
    const feita = await vistorias.concluir(v.id);
    expect(feita.status).toBe("concluida");
    expect((await locacoes.obter(rascunho.id)).km_saida).toBe(7500);
    await expect(vistorias.editar(v.id, { km: 7600 })).rejects.toMatchObject({ status: 409, codigo: "vistoria_concluida" });
    // Concluída, a saída não se abre de novo para a mesma locação em rascunho.
    expect((await vistorias.iniciarSaida(rascunho.id)).id).not.toBe(v.id);
  });

  it("saída só vale para locação aguardando a retirada", async () => {
    await expect(vistorias.iniciarSaida(2836)).rejects.toMatchObject({ status: 409, codigo: "transicao_locacao" });
  });

  it("corrigir é do gerente e do administrador", async () => {
    await expect(vistorias.corrigir(3001, { motivo: "x" })).rejects.toMatchObject({ status: 403 });
  });

  it("cliente com cadastro incompleto não passa na saída (CLI-03)", async () => {
    expect((await clientes.obter(1206)).status).toBe("incompleto");
  });
});

describe("agenda e avarias abertas (VIS-05)", () => {
  it("hoje, amanhã e semana", async () => {
    await entrarComo("joao@motorapida.com.br");
    const hoje = await vistorias.agenda("hoje");
    expect(hoje.resumo).toBe("Quarta, 07 out · 1 saída e 1 devolução");
    expect(hoje.resultados.map((i) => i.id)).toEqual(["devolucao-2790", "saida-2856"]);
    expect(hoje.proxima).toEqual({ item_id: "saida-2856", em_minutos: 20 });
    expect((await vistorias.agenda("amanha")).resultados).toEqual([]);
    expect((await vistorias.agenda("semana")).resultados.map((i) => i.id)).toEqual(["saida-2856", "devolucao-2848"]);
    expect((await vistorias.avarias()).resultados).toHaveLength(2);
  });
});
