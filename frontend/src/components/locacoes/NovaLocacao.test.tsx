// Nova locação (T-022, T-497) contra docs/telas/html/Locacao-Desktop.dc.html e Locacao-Mobile.dc.html, e as respostas da API falsa.
// Os planos são os do veículo (LOC-01, VEI-12, ADR 0041): a tela só mostra o que `GET /api/veiculos/{id}/precos/` e a simulação trazem.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { clientes, contas, locacoes, veiculos, type PrecosDoVeiculo } from "@/lib/api";
import { corpoDaLocacao, valoresIniciais } from "@/lib/locacao-form";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes/nova", useSearchParams: () => new URLSearchParams() }));

import { NovaLocacao } from "./NovaLocacao";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

const AGORA = new Date("2026-10-07T12:20:00Z");
const SEMANAL = 7002;
const ENTREGADOR = 7004;

describe("nova locação: Lucas Ferreira, CG 160 Fan SAK-1D39, plano Semanal do veículo", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));
  afterEach(() => vi.useRealTimers());

  async function pagina(plano: number | undefined, precos?: PrecosDoVeiculo): Promise<{ html: string; t: string }> {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(AGORA);
    const doVeiculo = precos ?? (await veiculos.precos(504));
    const corpo = plano ? corpoDaLocacao({ ...valoresIniciais(1206, 504, AGORA), plano_veiculo_id: plano }, doVeiculo.planos.find((p) => p.id === plano)) : null;
    const cache = new QueryClient();
    cache.setQueryData(["cliente", 1206], await clientes.obter(1206));
    cache.setQueryData(["veiculo", 504], await veiculos.obter(504));
    cache.setQueryData(["veiculo-precos", 504], doVeiculo);
    cache.setQueryData(["extras"], await locacoes.extras());
    if (corpo) cache.setQueryData(["locacao-simulacao", JSON.stringify(corpo)], await locacoes.simular(corpo));
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <NovaLocacao clienteInicial={1206} veiculoInicial={504} planoInicial={plano} />
      </QueryClientProvider>,
    );
    return { html, t: texto(html) };
  }

  it("seções, campos e resumo na ordem da referência", async () => {
    const { html, t } = await pagina(SEMANAL);
    ordem(t, ["Nova locação", "1 · Dados", "2 · Vistoria", "3 · Assinatura"]);
    ordem(t, ["Cliente e veículo", "Lucas Ferreira", "CPF ***.456.789-**", "Cadastro incompleto", "Trocar", "Honda CG 160 Fan", "SAK-1D39 · 3.120 km", "Trocar"]);
    ordem(t, ["Plano e período", "Diária", "R$ 54,90 / dia", "Semanal", "R$ 329,00 / semana", "Mensal", "R$ 1.190,00 / mês", "Entregador", "R$ 279,00 / semana"]);
    ordem(t, ["Retirada", "Devolução prevista", "1 semana · renova a cada semana", "Franquia de km", "Km livre neste plano"]);
    expect(html).toContain('value="Livre"');
    ordem(t, ["Cobrança", "Como o cliente paga", "Definido no plano deste veículo", "Forma de pagamento", "Primeiro vencimento", "Caução", "Devolvida no encerramento sem pendências"]);
    expect(html).toContain('value="Toda semana, adiantado"');
    expect(html).toContain('value="R$ 300,00"');
    ordem(t, ["Adicionais", "Capacete extra", "R$ 3,00 / semana", "Baú traseiro", "Proteção contra roubo e furto", "Condutor adicional"]);
    ordem(t, ["Resumo", "1 semana × R$ 329,00", "R$ 329,00", "Adicionais", "R$ 0,00", "Desconto", "– R$ 0,00", "Caução (devolvida no fim)", "R$ 300,00", "Valor por semana", "R$ 329,00", "Próximas semanas", "R$ 329,00", "Hoje, na retirada", "R$ 629,00", "Hoje: primeira semana mais caução."]);
    ordem(t, ["Salvar como reserva", "Cancelar", "Continuar para vistoria"]);
    expect(html).toContain('aria-pressed="true"');
  });

  it("loc_01_so_os_planos_ligados_do_veiculo_aparecem_com_o_que_a_api_manda", async () => {
    const { t } = await pagina(undefined);
    expect(t).toContain("Toda semana, adiantado");
    expect(t).toContain("Caução R$ 300,00 à vista");
    expect(t).toContain("Km livre");
    expect(t).toContain("1.200 km por semana");
    expect(t).toContain("Mínimo de 4 semanas");
    // Sem plano escolhido não há cobrança nem resumo.
    expect(t).toContain("Escolha o plano para ver a cobrança.");
    expect(t).not.toContain("Forma de pagamento");
    expect(t).toContain("Escolha o plano para ver os valores.");
  });

  it("vei_12_plano_desligado_nao_aparece", async () => {
    const precos = await veiculos.precos(504);
    const sem = { ...precos, planos: precos.planos.map((p) => (p.tipo === "entregador" ? { ...p, ligado: false } : p)) };
    const { t } = await pagina(SEMANAL, sem);
    expect(t).not.toContain("Entregador");
    expect(t).toContain("Semanal");
  });

  it("vei_15_veiculo_sem_plano_ligado_mostra_o_aviso_da_api", async () => {
    const precos = await veiculos.precos(504);
    const aviso = "A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda.";
    const sem = { ...precos, aviso_preco: aviso, planos: precos.planos.map((p) => ({ ...p, ligado: false })) };
    const { t } = await pagina(undefined, sem);
    expect(t).toContain(aviso);
    expect(t).toContain("Abrir Planos e preços");
    expect(t).not.toContain("Escolha o plano para ver a cobrança.");
    expect(t).not.toContain("R$ 329,00 / semana");
  });

  it("vei_12_forma_aceita_vem_do_plano", async () => {
    const { t, html } = await pagina(ENTREGADOR);
    expect(t).toContain("Entregador");
    // O Entregador aceita só Pix e boleto: cartão e dinheiro não aparecem na forma de pagamento.
    expect(html).toContain("Pix automático");
    expect(html).toContain("Boleto");
    expect(html).not.toContain(">Dinheiro<");
    expect(html).not.toContain(">Cartão<");
    expect(t).toContain("1.200 km por semana");
  });

  it("loc_16_compra_usa_o_plano_do_veiculo_sem_lista_de_planos", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(AGORA);
    const precos = await veiculos.precos(504);
    const corpo = corpoDaLocacao({ ...valoresIniciais(1206, 504, AGORA), tipo: "intencao_compra" })!;
    expect(corpo).not.toHaveProperty("plano_compra_id");
    expect(corpo).not.toHaveProperty("periodicidade");
    const cache = new QueryClient();
    cache.setQueryData(["cliente", 1206], await clientes.obter(1206));
    cache.setQueryData(["veiculo", 504], await veiculos.obter(504));
    cache.setQueryData(["veiculo-precos", 504], precos);
    cache.setQueryData(["extras"], await locacoes.extras());
    cache.setQueryData(["locacao-simulacao", JSON.stringify(corpo)], await locacoes.simular(corpo));
    const t = texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <NovaLocacao clienteInicial={1206} veiculoInicial={504} tipoInicial="intencao_compra" />
        </QueryClientProvider>,
      ),
    );
    ordem(t, ["Plano de compra", "Locação com compra", "R$ 191,01", "104 parcelas", "Entrada R$ 1.000,00"]);
    expect(t).not.toContain("Plano e período");
  });

  it("sem cliente nem veículo, o resumo pede a escolha e os botões ficam desligados", async () => {
    const cache = new QueryClient();
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <NovaLocacao />
      </QueryClientProvider>,
    );
    expect(texto(html)).toContain("Escolha o cliente e o veículo para ver os valores.");
    expect(texto(html)).toContain("Escolha o veículo para ver os planos.");
    expect(html.match(/<button[^>]*disabled[^>]*>(Continuar para vistoria|Salvar como reserva)/g)).toHaveLength(3);
  });
});

describe("API falsa de locações: simular, criar e confirmar pelo plano do veículo", () => {
  const corpoDe = (cliente: number, veiculo: number, plano = SEMANAL) => corpoDaLocacao({ ...valoresIniciais(cliente, veiculo, AGORA), plano_veiculo_id: plano })!;

  it("loc_01_semanal_do_veiculo: 32900, caução 30000, hoje na retirada 62900", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = corpoDe(1206, 504);
    expect(corpo).toMatchObject({ plano_veiculo_id: SEMANAL, periodos: 1 });
    expect(corpo).not.toHaveProperty("periodicidade");
    expect(corpo).not.toHaveProperty("parcelamento_mensal");
    const s = await locacoes.simular(corpo);
    expect(s.valor_periodo_centavos).toBe(32900);
    expect(s.caucao_centavos).toBe(30000);
    expect(s.hoje_na_retirada_centavos).toBe(62900);
    expect(s.texto_retirada).toBe("Hoje: primeira semana mais caução.");
    expect(s.plano).toMatchObject({ id: SEMANAL, rotulo: "Semanal", periodo: "semana" });
    expect(s.avisos.map((a) => a.codigo)).toContain("CLI-03");
  });

  it("vei_12_entregador_vale_27900_e_o_prazo_minimo_vira_o_periodo_de_partida", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const precos = await veiculos.precos(504);
    const entregador = precos.planos.find((p) => p.id === ENTREGADOR)!;
    const corpo = corpoDaLocacao({ ...valoresIniciais(1201, 504, AGORA), plano_veiculo_id: ENTREGADOR }, entregador)!;
    expect(corpo.periodos).toBe(4);
    const s = await locacoes.simular(corpo);
    expect(s.valor_periodo_centavos).toBe(27900);
    expect(s.periodos).toBe(4);
  });

  it("vei_12_forma_fora_das_aceitas_responde_400_no_campo", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = { ...corpoDe(1201, 504, ENTREGADOR), forma_pagamento: "cartao" as const, periodos: 4 };
    await expect(locacoes.simular(corpo)).rejects.toMatchObject({ status: 400, campos: { forma_pagamento: "Este plano não aceita Cartão." } });
  });

  it("loc_01_plano_inexistente_ou_de_outro_veiculo_responde_400", async () => {
    await entrarComo("bruna@motorapida.com.br");
    await expect(locacoes.simular(corpoDe(1201, 504, 9999))).rejects.toMatchObject({ status: 400, campos: { plano_veiculo_id: "Escolha um plano deste veículo." } });
  });

  it("desconto acima do limite pede aprovação só para o vendedor", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = { ...corpoDe(1201, 504), desconto_pct: "10" };
    expect((await locacoes.simular(corpo)).precisa_aprovacao_desconto).toBe(true);
    await entrarComo("rodrigo@motorapida.com.br");
    expect((await locacoes.simular(corpo)).precisa_aprovacao_desconto).toBe(false);
  });

  it("mensal com menos de um mês responde 400 no campo da devolução", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = { ...corpoDe(1201, 504, 7003), periodos: null, fim_previsto: "2026-10-14T12:30:00.000Z" };
    await expect(locacoes.simular(corpo)).rejects.toMatchObject({ status: 400, campos: { fim_previsto: expect.any(String) } });
  });

  it("veículo alugado: impedimento LOC-03 na simulação e 409 ao confirmar", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = corpoDe(1201, 502);
    expect((await locacoes.simular(corpo)).impedimentos[0]?.codigo).toBe("LOC-03");
    const rascunho = await locacoes.criar(corpo);
    expect(rascunho.status).toBe("rascunho");
    await expect(locacoes.confirmar(rascunho.id)).rejects.toMatchObject({ status: 409, codigo: "LOC-03" });
  });

  it("rascunho vira aguardando_retirada ao confirmar, com as parcelas e a caução em aberto", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = corpoDe(1201, 509);
    const rascunho = await locacoes.criar(corpo);
    expect(rascunho.codigo).toMatch(/^LOC-\d+$/);
    const editado = await locacoes.atualizar(rascunho.id, { ...corpo, desconto_pct: "5" });
    expect(editado.precos?.desconto_pct).toBe("5");
    const l = await locacoes.confirmar(rascunho.id);
    expect(l.status).toBe("aguardando_retirada");
    expect(l.parcelas?.map((p) => p.tipo)).toEqual(["parcela", "caucao"]);
    await expect(locacoes.atualizar(rascunho.id, corpo)).rejects.toMatchObject({ status: 409, codigo: "transicao_locacao" });
  });
});
