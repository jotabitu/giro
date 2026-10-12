// Nova locação (T-022) contra docs/telas/html/Locacao-Desktop.dc.html e Locacao-Mobile.dc.html, e as respostas da API falsa.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { clientes, contas, locacoes, veiculos } from "@/lib/api";
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

describe("nova locação: Lucas Ferreira, CG 160 Fan SAK-1D39, semanal Street", () => {
  beforeAll(() => entrarComo("bruna@motorapida.com.br"));
  afterEach(() => vi.useRealTimers());

  async function pagina(): Promise<{ html: string; t: string }> {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(AGORA);
    const planos = await locacoes.planosEspeciais();
    const corpo = corpoDaLocacao(valoresIniciais(1206, 504, AGORA), planos.resultados);
    if (!corpo) throw new Error("sem corpo");
    const cache = new QueryClient();
    cache.setQueryData(["cliente", 1206], await clientes.obter(1206));
    cache.setQueryData(["veiculo", 504], await veiculos.obter(504));
    cache.setQueryData(["extras"], await locacoes.extras());
    cache.setQueryData(["planos-especiais"], planos);
    cache.setQueryData(["locacao-simulacao", JSON.stringify(corpo)], await locacoes.simular(corpo));
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <NovaLocacao clienteInicial={1206} veiculoInicial={504} />
      </QueryClientProvider>,
    );
    return { html, t: texto(html) };
  }

  it("seções, campos e resumo na ordem da referência", async () => {
    const { html, t } = await pagina();
    ordem(t, ["Nova locação", "1 · Dados", "2 · Vistoria", "3 · Assinatura"]);
    ordem(t, ["Cliente e veículo", "Lucas Ferreira", "CPF ***.456.789-**", "Cadastro incompleto", "Trocar", "Honda CG 160 Fan", "SAK-1D39 · 3.120 km", "Trocar"]);
    ordem(t, ["Plano e período", "Diária", "R$ 54,90 / dia", "Semanal", "R$ 329,00 / semana", "Mensal", "Entregador", "R$ 279,00 / semana"]);
    ordem(t, ["Retirada", "Devolução prevista", "1 semana · renova a cada semana", "Franquia de km", "Km livre em todos os planos"]);
    // D-30: a cobrança só aparece depois do plano escolhido (a escolha é interação; aqui a página abre sem plano).
    expect(t).toContain("Escolha o plano para ver a cobrança.");
    expect(t).not.toContain("cobra a cada 7 dias");
    expect(t).not.toContain("Forma de pagamento");
    expect(html).toContain('value="Livre"');
    ordem(t, ["Adicionais", "Capacete extra", "R$ 3,00 / semana", "Baú traseiro", "Proteção contra roubo e furto", "Condutor adicional"]);
    ordem(t, ["Resumo", "1 semana × R$ 329,00", "R$ 329,00", "Adicionais", "R$ 0,00", "Desconto", "– R$ 0,00", "Caução (devolvida no fim)", "R$ 300,00", "Valor por semana", "R$ 329,00", "Próximas semanas", "R$ 329,00", "Hoje, na retirada", "R$ 629,00", "Hoje: primeira semana mais caução."]);
    ordem(t, ["Continuar para vistoria", "Salvar como reserva"]);
  });

  it("sem cliente nem veículo, o resumo pede a escolha e os botões ficam desligados", async () => {
    const cache = new QueryClient();
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <NovaLocacao />
      </QueryClientProvider>,
    );
    expect(texto(html)).toContain("Escolha o cliente e o veículo para ver os valores.");
    expect(html.match(/<button[^>]*disabled[^>]*>(Continuar para vistoria|Salvar como reserva)/g)).toHaveLength(2);
  });
});

describe("API falsa de locações: simular, criar e confirmar", () => {
  it("Lucas semanal Street: 32900, caução 30000, hoje na retirada 62900", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = corpoDaLocacao(valoresIniciais(1206, 504, AGORA), [])!;
    const s = await locacoes.simular(corpo);
    expect(s.valor_periodo_centavos).toBe(32900);
    expect(s.caucao_centavos).toBe(30000);
    expect(s.hoje_na_retirada_centavos).toBe(62900);
    expect(s.texto_retirada).toBe("Hoje: primeira semana mais caução.");
    expect(s.avisos.map((a) => a.codigo)).toContain("CLI-03");
  });

  it("plano especial Entregador troca o preço: 27900", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = { ...corpoDaLocacao(valoresIniciais(1201, 504, AGORA), [])!, plano_especial_id: 1 };
    expect((await locacoes.simular(corpo)).valor_periodo_centavos).toBe(27900);
  });

  it("desconto acima do limite pede aprovação só para o vendedor", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = { ...corpoDaLocacao(valoresIniciais(1201, 504, AGORA), [])!, desconto_pct: "10" };
    expect((await locacoes.simular(corpo)).precisa_aprovacao_desconto).toBe(true);
    await entrarComo("rodrigo@motorapida.com.br");
    expect((await locacoes.simular(corpo)).precisa_aprovacao_desconto).toBe(false);
  });

  it("mensal com menos de um mês responde 400 no campo da devolução", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = { ...corpoDaLocacao(valoresIniciais(1201, 504, AGORA), [])!, periodicidade: "mensal" as const, periodos: null, fim_previsto: "2026-10-14T12:30:00.000Z", parcelamento_mensal: "a_vista" as const };
    await expect(locacoes.simular(corpo)).rejects.toMatchObject({ status: 400, campos: { fim_previsto: expect.any(String) } });
  });

  it("veículo alugado: impedimento LOC-03 na simulação e 409 ao confirmar", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = corpoDaLocacao(valoresIniciais(1201, 502, AGORA), [])!;
    expect((await locacoes.simular(corpo)).impedimentos[0]?.codigo).toBe("LOC-03");
    const rascunho = await locacoes.criar(corpo);
    expect(rascunho.status).toBe("rascunho");
    await expect(locacoes.confirmar(rascunho.id)).rejects.toMatchObject({ status: 409, codigo: "LOC-03" });
  });

  it("rascunho vira aguardando_retirada ao confirmar, com as parcelas e a caução em aberto", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const corpo = corpoDaLocacao(valoresIniciais(1201, 509, AGORA), [])!;
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
