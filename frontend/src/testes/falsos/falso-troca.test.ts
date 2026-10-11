// Cancelar a troca de veículo (T-125; LOC-09, LOC-12) contra as fixtures de locações e vistorias.
import { describe, expect, it } from "vitest";
import { contas, locacoes, vistorias } from "@/lib/api";
import { simularTroca } from "./falso-locacoes";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

describe("cancelar a troca de veículo (LOC-09, LOC-12)", () => {
  it("sem troca pendente: acoes.cancelar_troca é false e a API responde 409 transicao_troca", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const l = await locacoes.obter(2850);
    expect(l.troca).toBeNull();
    expect(l.acoes.cancelar_troca).toBe(false);
    await expect(locacoes.cancelarTroca(2850, { motivo: "Desistiu" })).rejects.toMatchObject({ status: 409, codigo: "transicao_troca" });
  });

  it("com troca pendente: cancelar_troca vem true, cancelar a locação some e o bloco troca aparece", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const antes = await locacoes.obter(2850);
    expect(antes.acoes.cancelar).toBe("direto");
    await locacoes.trocarVeiculo(2850, { veiculo_novo_id: 504, motivo: "Pane no veículo" });
    const l = await locacoes.obter(2850);
    expect(l.acoes.cancelar_troca).toBe(true);
    expect(l.acoes.cancelar).toBe(false);
    expect(l.acoes.trocar_veiculo).toBe(false);
    expect(l.troca).toMatchObject({ status: "pendente", motivo: "Pane no veículo", veiculo_novo: { placa: "SAK1D39" }, devolucao_vistoria: { status: "rascunho" }, saida_vistoria: { status: "rascunho" } });
    expect(l.troca?.preco).toBeDefined();
  });

  it("cancelar a locação com troca pendente responde 409 troca_pendente com a mensagem da API", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    await expect(locacoes.cancelar(2850, { motivo: "Desistiu", forma_devolucao: "pix" })).rejects.toMatchObject({ status: 409, codigo: "troca_pendente", message: "Conclua ou cancele a troca antes" });
  });

  it("o vistoriador não recebe o preço da troca nem o botão de cancelar", async () => {
    await entrarComo("joao@motorapida.com.br");
    const l = await locacoes.obter(2850);
    expect(l.troca?.preco).toBeUndefined();
    expect(l.acoes.cancelar_troca).toBe(false);
  });

  it("o motivo é obrigatório (400 no campo motivo)", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    await expect(locacoes.cancelarTroca(2850, { motivo: "  " })).rejects.toMatchObject({ status: 400, campos: { motivo: expect.any(String) } });
  });

  it("com a saída do veículo novo concluída, cancelar_troca vem false e a API recusa com troca_saida_concluida", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    simularTroca(2850, { saidaConcluida: true });
    expect((await locacoes.obter(2850)).acoes.cancelar_troca).toBe(false);
    await expect(locacoes.cancelarTroca(2850, { motivo: "Desistiu" })).rejects.toMatchObject({ status: 409, codigo: "troca_saida_concluida", message: "O veículo novo já foi entregue. Conclua a troca com a chegada do veículo antigo." });
    simularTroca(2850, { saidaConcluida: false });
  });

  it("cancelar: vistorias descartadas, troca some do detalhe e a locação volta a poder ser cancelada", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const r = await locacoes.cancelarTroca(2850, { motivo: "Cliente desistiu da troca" });
    expect(r.troca).toMatchObject({ status: "cancelada", saida_vistoria: { status: "descartada" }, devolucao_vistoria: { status: "descartada" }, conta_caucao: null, devolucao_id: null });
    const l = await locacoes.obter(2850);
    expect(l.troca).toBeNull();
    expect(l.acoes).toMatchObject({ cancelar_troca: false, cancelar: "direto", trocar_veiculo: true });
  });

  it("vendedor pede a troca e também cancela", async () => {
    await entrarComo("bruna@motorapida.com.br");
    await locacoes.trocarVeiculo(2812, { veiculo_novo_id: 509, motivo: "Pneu" });
    expect((await locacoes.obter(2812)).acoes.cancelar_troca).toBe(true);
    await locacoes.cancelarTroca(2812, { motivo: "Resolvido" });
    expect((await locacoes.obter(2812)).acoes.cancelar_troca).toBe(false);
  });
});

describe("acerto com a diferença do período da troca (LOC-09, DEV-01)", () => {
  it("cobrança: item diferenca_troca em itens, como a API devolve", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    simularTroca(2836, { diferencaCentavos: 12000 });
    const a = (await vistorias.obterDevolucao(701)).acerto;
    const item = a?.itens.find((i) => i.tipo === "diferenca_troca");
    expect(item).toMatchObject({ valor_centavos: 12000, natureza: "cobranca", modo: "calculado" });
    expect(a?.creditos).toHaveLength(0);
  });

  it("crédito: item diferenca_troca em creditos, valor positivo, somando ao saldo", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    simularTroca(2836, { diferencaCentavos: 0 });
    const base = (await vistorias.obterDevolucao(701)).acerto;
    simularTroca(2836, { diferencaCentavos: -4000 });
    const a = (await vistorias.obterDevolucao(701)).acerto;
    expect(a?.creditos[0]).toMatchObject({ tipo: "diferenca_troca", natureza: "credito", valor_centavos: 4000 });
    expect(a?.itens.some((i) => i.tipo === "diferenca_troca")).toBe(false);
    expect(a?.total_creditos_centavos).toBe(4000);
    expect((a?.saldo_centavos ?? 0) - (base?.saldo_centavos ?? 0)).toBe(4000);
  });
});
