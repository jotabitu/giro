// Detalhe da locação (T-022) contra docs/telas/html/Locacao-Detalhe-Desktop.dc.html e Locacao-Detalhe-Mobile.dc.html.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, locacoes } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes", useSearchParams: () => new URLSearchParams() }));

import { DetalheDaLocacao } from "./DetalheDaLocacao";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

async function pagina(id: number): Promise<{ desktop: string; celular: string; html: string }> {
  const l = await locacoes.obter(id);
  const historico = await locacoes.historico(id);
  const cache = new QueryClient();
  cache.setQueryData(["locacao", id], l);
  cache.setQueryData(["locacao", id, "historico"], historico);
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDaLocacao id={id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = html.match(/^<div class="hidden flex-col gap-6 md:flex">(.*)<\/div><div class="flex flex-col gap-4 md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop, celular, html };
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

describe("detalhe da locação, gerente: LOC-2836 da Juliana", () => {
  it("desktop e celular são duas árvores; hidden e md:hidden nunca ficam num elemento wl-", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = await pagina(2836);
    expect(desktop).not.toBe("");
    expect(celular).not.toBe("");
    for (const m of (desktop + celular).matchAll(/class="([^"]*)"/g)) {
      const classes = m[1] ?? "";
      if (/\bwl-/.test(classes)) expect(classes, "wl- com hidden").not.toMatch(/(^|\s)(md:)?hidden(\s|$)/);
    }
  });

  it("desktop: seções e rótulos na ordem da referência", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const t = texto((await pagina(2836)).desktop);
    ordem(t, ["Locações", "LOC-2836", "Juliana Rocha", "Ativa", "· Semanal · 30 set → 14 out 18:00"]);
    ordem(t, ["Renovar", "Trocar veículo", "Cancelar locação", "Registrar devolução"]);
    ordem(t, ["Yamaha Factor 150", "PNB-7C04 · saiu com 18.402 km", "Juliana Rocha", "(85) 98114-2290 · CNH A"]);
    ordem(t, ["Pagamentos", "tudo em dia", "Parcela", "Vencimento", "Valor", "Situação", "30 set", "R$ 329,00", "Pago · Pix", "07 out", "Caução", "R$ 300,00", "Devolver na entrega"]);
    ordem(t, ["Contrato", "Imprimir", "Reenviar por WhatsApp", "Contrato LOC-2836.pdf", "Modelo “Locação semanal” · assinado em 30 set", "Assinado"]);
    ordem(t, ["Devolução em 14 out às 18:00", "faltam 7 dias", "Se atrasar, cobra R$ 54,90 por dia a mais (diária)"]);
    ordem(t, ["Resumo", "Plano", "Semanal · R$ 329,00", "Período", "2 semanas", "Km incluído", "livre", "Extras", "Capacete extra", "Caução", "R$ 300,00", "Total pago", "R$ 958,00"]);
    ordem(t, ["Histórico", "Locação criada por Bruna Alves", "30 set, 09:10", "Vistoria de saída · 12 fotos", "João Silva · 18.402 km · tanque 4/4", "Contrato assinado pela cliente", "Pagamento da 2ª semana", "07 out, 08:02 · Pix", "Devolução prevista"]);
  });

  it("celular: resumo, contrato, histórico e os botões na ordem da referência", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const t = texto((await pagina(2836)).celular);
    ordem(t, ["Devolução em 14 out às 18:00", "faltam 7 dias", "Yamaha Factor 150 · PNB-7C04"]);
    ordem(t, ["Resumo", "Plano", "R$ 329,00/sem", "Pagamentos", "2 de 2 pagos", "Caução", "R$ 300,00", "Telefone", "(85) 98114-2290"]);
    ordem(t, ["Contrato", "Contrato LOC-2836.pdf", "Histórico", "Locação criada por Bruna Alves", "Renovar", "Registrar devolução"]);
  });
});

describe("detalhe da locação: cancelamento pendente (LOC-2812) e perfis", () => {
  it("mostra a multa e o valor a devolver como estimativa para a data, e não oferece renovar nem cancelar de novo", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const t = texto((await pagina(2812)).desktop);
    ordem(t, ["Pedido de cancelamento", "Aguardando o gerente", "Multa de encerramento", "R$ 84,80", "A devolver ao cliente", "R$ 286,20", "Estimativa para 07 out. O valor final sai na devolução."]);
    expect(t).not.toContain("Renovar");
    expect(t).not.toContain("Cancelar locação");
    expect(t).not.toContain("Pedir cancelamento");
  });

  it("vendedor pede o cancelamento; o botão diz isso", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const t = texto((await pagina(2836)).desktop);
    expect(t).toContain("Pedir cancelamento");
    expect(t).not.toContain("Cancelar locação");
  });

  it("vistoriador não vê valores, parcelas nem ações de dinheiro", async () => {
    await entrarComo("joao@motorapida.com.br");
    const t = texto((await pagina(2836)).desktop);
    expect(t).toContain("Registrar devolução");
    expect(t).not.toContain("Pagamentos");
    expect(t).not.toContain("Total pago");
    expect(t).not.toContain("Renovar");
    expect(t).not.toContain("Pagamento da 2ª semana");
  });

  it("aguardando assinatura: contrato não assinado e botão da vistoria de saída", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const t = texto((await pagina(2856)).desktop);
    expect(t).toContain("Aguardando assinatura");
    expect(t).toContain("Fazer vistoria de saída");
    expect(t).not.toContain("Registrar devolução");
  });
});

describe("detalhe da locação com troca de veículo pendente (LOC-09, LOC-12)", () => {
  it("mostra o bloco da troca e o botão Cancelar troca, sem Cancelar locação; ao cancelar, o botão some", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    await locacoes.trocarVeiculo(2841, { veiculo_novo_id: 504, motivo: "Pane no veículo" });
    const { desktop, celular } = await pagina(2841);
    const t = texto(desktop);
    ordem(t, ["Troca de veículo", "Veículo atual", "Veículo novo", "SAK-1D39", "Motivo", "Pane no veículo", "Chegada do veículo atual", "Em andamento", "Saída do veículo novo", "Em andamento"]);
    expect(t).toContain("Cancelar troca");
    expect(t).not.toContain("Cancelar locação");
    expect(t).not.toContain("Trocar veículo");
    expect(texto(celular)).toContain("Cancelar troca");
    await locacoes.cancelarTroca(2841, { motivo: "Resolvido" });
    const depois = texto((await pagina(2841)).desktop);
    expect(depois).not.toContain("Cancelar troca");
    expect(depois).not.toContain("Chegada do veículo atual");
    expect(depois).toContain("Cancelar locação");
  });

  it("vistoriador vê a troca sem preço nem caução", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    await locacoes.trocarVeiculo(2836, { veiculo_novo_id: 504, motivo: "Pneu" });
    await entrarComo("joao@motorapida.com.br");
    const t = texto((await pagina(2836)).desktop);
    expect(t).toContain("Troca de veículo");
    expect(t).not.toContain("Preço do veículo novo");
    expect(t).not.toContain("Cancelar troca");
  });
});

describe("cliente na locação sem abrir a ficha (USR-09, D-05 da T-025)", () => {
  it("t_207_vistoriador_ve_celular_e_cnh_sem_link_para_a_ficha", async () => {
    await entrarComo("joao@motorapida.com.br");
    const { desktop, html } = await pagina(2836);
    const t = texto(desktop);
    expect(t).toContain("Juliana Rocha");
    expect(t).toContain("(85) 98114-2290 · CNH A");
    expect(html).not.toContain('href="/clientes/');
  });

  it("t_207_gerente_ve_o_mesmo_contato_com_link_para_a_ficha", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, html } = await pagina(2836);
    expect(texto(desktop)).toContain("(85) 98114-2290 · CNH A");
    expect(html).toContain('href="/clientes/1201"');
  });
});

describe("detalhe da locação: enviar contrato (LOC-04, T-208)", () => {
  async function semContrato(id: number) {
    const l = await locacoes.obter(id);
    const cache = new QueryClient();
    cache.setQueryData(["locacao", id], { ...l, contrato: null, condicoes: { ...l.condicoes, contrato_assinado_em: null } });
    return texto(renderToStaticMarkup(<QueryClientProvider client={cache}><DetalheDaLocacao id={id} /></QueryClientProvider>));
  }

  it("aguardando retirada sem contrato: o gerente vê Enviar contrato; com contrato enviado vê só Reenviar", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const t = await semContrato(2856);
    ordem(t, ["Contrato", "Enviar contrato", "Contrato ainda não enviado", "link de assinatura por WhatsApp"]);
    const comContrato = texto((await pagina(2856)).desktop);
    expect(comContrato).toContain("Reenviar por WhatsApp");
    expect(comContrato).not.toContain("Enviar contrato");
  });

  it("locação ativa sem contrato não oferece o botão", async () => {
    expect(await semContrato(2836)).not.toContain("Enviar contrato");
  });

  it("vistoriador não vê o botão", async () => {
    await entrarComo("joao@motorapida.com.br");
    expect(await semContrato(2856)).not.toContain("Enviar contrato");
  });

  it("a API falsa recusa o segundo pedido com contrato_existente", async () => {
    await entrarComo("bruna@motorapida.com.br");
    await expect(locacoes.gerarContrato(2856)).rejects.toMatchObject({ status: 409, codigo: "contrato_existente" });
  });
});
