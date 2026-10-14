// Contas a receber e caixa do dia (T-023) contra docs/telas/html/Receber-*.dc.html e Caixa-*.dc.html, com os números do seed de 07 out.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, financeiro, type Eu } from "@/lib/api";
import { reiniciarFinanceiroFalso, type DiaDoCaixaFalso } from "@/testes/falsos/falso-financeiro";
import { composicaoDoValor, diaDaSemanaEData, rotuloDaParcela, situacaoDaConta, textoDoEvento } from "@/lib/financeiro";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
const filialDaTela = vi.hoisted(() => ({ atual: null as null | { todas: boolean; nome: string } }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => filialDaTela.atual }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/financeiro/receber", useSearchParams: () => new URLSearchParams() }));

import { CaixaDoDia } from "./CaixaDoDia";
import { ListaReceber } from "./ListaReceber";

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
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

async function paginaReceber(): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["contas-receber", { aba: "atrasadas", periodo: "mes", busca: "" }], await financeiro.listarContas({ periodo: "mes", situacao: "atrasadas" }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaReceber />
    </QueryClientProvider>,
  );
}

async function paginaCaixa(dia: DiaDoCaixaFalso = "aberto"): Promise<string> {
  reiniciarFinanceiroFalso(dia);
  const cache = new QueryClient();
  const hoje = await financeiro.caixaDeHoje();
  cache.setQueryData(["caixa", "hoje"], hoje);
  if ("id" in hoje) cache.setQueryData(["caixa", "movimentos", hoje.id], await financeiro.movimentos(hoje.id));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <CaixaDoDia />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  reiniciarFinanceiroFalso();
  filialDaTela.atual = null;
});

describe("filial escolhida no seletor (T-161, CA-023-05, CA-023-16)", () => {
  it("Receber mostra a filial escolhida no cabeçalho, inclusive Todas as filiais", async () => {
    await entrar("financeiro@motorapida.com.br");
    filialDaTela.atual = { todas: true, nome: "Todas as filiais" };
    expect(texto(await paginaReceber())).toContain("Todas as filiais");
    filialDaTela.atual = { todas: false, nome: "Filial Aldeota" };
    expect(texto(await paginaReceber())).toContain("Filial Aldeota");
  });

  it("o caixa é de uma filial: com Todas as filiais a tela pede a escolha, sem abrir nem receber", async () => {
    await entrar("mariana@motorapida.com.br");
    filialDaTela.atual = { todas: true, nome: "Todas as filiais" };
    const t = texto(await paginaCaixa());
    expect(t).toContain("Escolha uma filial no menu");
    expect(t).not.toContain("Receber pagamento");
    expect(t).not.toContain("Abrir caixa");
  });
});

describe("contas a receber, na ordem da referência (FIN-01, FIN-02, FIN-15)", () => {
  it("Novo lançamento só para gerente (e não para a vendedora), e o mês sai sem maiúscula no meio (USR-05)", async () => {
    await entrar("bruna@motorapida.com.br");
    const bruna = texto(await paginaReceber());
    expect(bruna).not.toContain("Novo lançamento");
    expect(bruna).not.toContain(" De ");
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await paginaReceber())).toContain("Novo lançamento");
  });

  it("indicadores, faixas, abas e as duas contas em atraso", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(await paginaReceber());
    ordem(t, ["Contas a receber", "Filial Centro", "Novo lançamento"]);
    ordem(t, ["Previsto no mês", "R$ 52 mil", "128 parcelas", "Recebido", "R$ 13,4 mil", "26% do previsto", "Vence hoje", "R$ 2.625,80", "6 parcelas", "Em atraso", "R$ 1.646,40", "2 clientes"]);
    ordem(t, ["Atraso por faixa", "R$ 1.646,40 em 2 parcelas", "R$ 299,40", "1 a 7 dias", "R$ 1.347,00", "8 a 30 dias", "R$ 0,00", "Mais de 30 dias"]);
    ordem(t, ["Todas", "130", "Em atraso", "2", "Vencem hoje", "6", "A vencer", "92", "Pagas", "30"]);
    ordem(t, ["Vencimento", "Cliente e contrato", "Parcela", "Forma", "Valor", "Situação"]);
    ordem(t, ["12 set", "Rafael Sousa", "LOC-2790 · PQD-6E21", "4 de 4", "Boleto", "R$ 1.347,00", "25 dias", "Cobrar"]);
    ordem(t, ["30 set", "Carlos Menezes", "LOC-2841 · QXA-4B21", "2 de 5", "Pix automático", "R$ 299,40", "7 dias", "Cobrar"]);
    ordem(t, ["Mostrando 2 de 2 parcelas em atraso", "Cobrar todos pelo WhatsApp"]);
  });

  it("celular: cartão com cobrança no WhatsApp e baixa", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(await paginaReceber());
    ordem(t, ["Rafael Sousa", "LOC-2790 · parcela 4 de 4", "R$ 1.347,00", "25 dias", "Boleto · venceu 12 set", "Cobrar no WhatsApp", "Dar baixa"]);
  });

  it("lista só o que a API devolveu: busca e situação são filtros da API", async () => {
    const r = await financeiro.listarContas({ situacao: "atrasadas", busca: "carlos" });
    expect(r.resultados.map((c) => c.cliente.nome)).toEqual(["Carlos Menezes"]);
  });
});

describe("valores e textos vindos da API", () => {
  it("o valor do dia (FIN-03) de Carlos é 30609: principal + multa + juros, sem conta no cliente", async () => {
    const r = await financeiro.listarContas({ situacao: "atrasadas" });
    const carlos = r.resultados.find((c) => c.cliente.nome === "Carlos Menezes");
    expect(carlos?.valor_hoje.total_centavos).toBe(30609);
    expect(composicaoDoValor(carlos!.valor_hoje)).toBe("R$ 299,40 + multa de R$ 5,99 + juros de R$ 0,70");
  });

  it("situação e parcela", async () => {
    const [rafael] = (await financeiro.listarContas({ situacao: "atrasadas" })).resultados;
    expect(situacaoDaConta(rafael!)).toEqual({ rotulo: "25 dias", tom: "critico" });
    expect(situacaoDaConta({ status: "vence_hoje", dias_atraso: 0 })).toEqual({ rotulo: "Vence hoje", tom: "alerta" });
    expect(rotuloDaParcela({ tipo: "acerto", numero: null, total_parcelas: null })).toBe("Acerto da devolução");
  });

  it("código de evento desconhecido aparece como está", () => {
    expect(textoDoEvento("cobranca.pix")).toBe("Pix gerado");
    expect(textoDoEvento("conta_receber.nova_coisa")).toBe("conta_receber.nova_coisa");
  });

  it("dia da semana do caixa", () => {
    expect(diaDaSemanaEData("2026-10-07")).toBe("Quarta, 07 out");
  });
});

describe("baixa e cobrança", () => {
  it("receber exige o valor inteiro do dia (FIN-01) e exige caixa aberto (FIN-07)", async () => {
    await expect(financeiro.receber(9010, { forma: "dinheiro", valor_centavos: 20000 })).rejects.toMatchObject({ status: 422, codigo: "FIN-01" });
    const paga = await financeiro.receber(9010, { forma: "dinheiro", valor_centavos: 30609 });
    expect(paga.status).toBe("paga");
    expect(paga.multa_centavos).toBe(599);
    reiniciarFinanceiroFalso("sem_caixa");
    await expect(financeiro.receber(9010, { forma: "dinheiro", valor_centavos: 30609 })).rejects.toMatchObject({ status: 422, codigo: "FIN-07", message: "Abra o caixa do dia para receber" });
  });

  it("cobrar duas vezes no dia não envia de novo, sem erro", async () => {
    expect(await financeiro.cobrar(9010)).toEqual({ enviadas: 1 });
    expect(await financeiro.cobrar(9010)).toEqual({ enviadas: 0 });
  });
});

describe("caixa do dia (FIN-07, APR-04)", () => {
  it("aberto: resumo, movimentos e gaveta na ordem da referência", async () => {
    await entrar("bruna@motorapida.com.br");
    const t = texto(await paginaCaixa());
    ordem(t, ["Caixa do dia", "Quarta, 07 out", "Filial Centro", "aberto por Bruna Alves às 07:55", "Sangria", "Fechar caixa"]);
    ordem(t, ["Entrou hoje", "R$ 1.111,90", "5 recebimentos", "Pix", "R$ 373,90", "Cartão", "R$ 109,00", "cai em 30 dias", "Dinheiro na gaveta", "R$ 281,00", "confere no fechamento"]);
    ordem(t, ["Movimentos", "Todos", "Entradas", "Saídas", "Hora", "Forma", "Descrição", "Valor"]);
    ordem(t, ["08:02", "Pix", "Juliana Rocha · LOC-2836 · 2ª semana", "R$ 329,00", "Dinheiro", "Sangria · Depósito no banco", "− R$ 500,00", "Óleo · QXA4B21", "− R$ 48,00"]);
    ordem(t, ["Receber pagamento"]);
    ordem(t, ["Gaveta", "Abertura (troco)", "R$ 200,00", "Entradas em dinheiro", "R$ 629,00", "Saídas em dinheiro", "− R$ 548,00", "Deve ter na gaveta", "R$ 281,00"]);
  });

  it("sem caixa aberto, pede o troco e não mostra recebimento", async () => {
    await entrar("bruna@motorapida.com.br");
    const t = texto(await paginaCaixa("sem_caixa"));
    expect(t).toContain("O caixa de hoje ainda não foi aberto. Abra o caixa do dia para receber.");
    ordem(t, ["Abrir o caixa de hoje", "Troco na gaveta (R$)", "Abrir caixa"]);
    expect(t).not.toContain("Receber pagamento");
  });

  it("aguardando aprovação mostra a diferença e esconde as ações", async () => {
    await entrar("bruna@motorapida.com.br");
    const t = texto(await paginaCaixa("aguardando"));
    expect(t).toContain("Aguardando aprovação");
    expect(t).toContain("Fechamento aguardando a aprovação do gerente · diferença de − R$ 10,00 · Troco errado.");
    expect(t).not.toContain("Fechar caixa");
    expect(t).not.toContain("Receber pagamento");
  });

  it("fechado mostra quem fechou e o contado", async () => {
    await entrar("bruna@motorapida.com.br");
    const t = texto(await paginaCaixa("fechado"));
    expect(t).toContain("Caixa fechado por Bruna Alves");
    expect(t).toContain("contado R$ 281,00");
  });

  it("fechar com diferença sem motivo é recusado; com motivo vai para o gerente (CA-017-15)", async () => {
    await expect(financeiro.fecharCaixa(240, { contado_centavos: 27100 })).rejects.toMatchObject({ status: 400, campos: { motivo_diferenca: expect.any(String) } });
    const c = await financeiro.fecharCaixa(240, { contado_centavos: 27100, motivo_diferenca: "Troco errado" });
    expect(c.status).toBe("aguardando_aprovacao");
    expect(c.fechamento?.diferenca_centavos).toBe(-1000);
  });

  it("sangria maior que a gaveta é recusada (CA-017-14)", async () => {
    await expect(financeiro.sangria(240, { valor_centavos: 30000, descricao: "Depósito" })).rejects.toMatchObject({ status: 422, codigo: "sangria_maior_que_gaveta" });
  });

  it("abrir de novo no mesmo dia: 409 FIN-07", async () => {
    await expect(financeiro.abrirCaixa(20000)).rejects.toMatchObject({ status: 409, codigo: "FIN-07" });
  });
});
