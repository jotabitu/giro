// Compra pública (T-435, docs/api/compra.md): as telas mostram o que a API manda (Moto Rápida, compra em 07 out 2026).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { AndamentoDoPedido, CatalogoDaCompra } from "@/lib/api/tipos-compra";

vi.mock("@/lib/api/compra", () => ({ compraApi: {} }));

import { AmbientePronto } from "./AmbientePronto";
import { Checkout } from "./Checkout";
import { EscolhaDoPlano } from "./EscolhaDoPlano";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const render = (no: ReactNode) => texto(renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{no}</QueryClientProvider>));

const CATALOGO: CatalogoDaCompra = {
  planos: [
    {
      codigo: "essencial",
      nome: "Essencial",
      descricao: "Para quem está começando a frota.",
      mensal_centavos: 19900,
      anual_centavos: 199000,
      limites: { veiculos: 30, filiais: 1, usuarios: 3 },
      inclui: ["Locação, vistoria e contas a receber"],
      destaque: false,
    },
    {
      codigo: "profissional",
      nome: "Profissional",
      descricao: "Para locadoras com equipe e mais de uma loja.",
      mensal_centavos: 44900,
      anual_centavos: 449000,
      limites: { veiculos: 150, filiais: 3, usuarios: 10 },
      inclui: ["Tudo do Essencial, mais despesas", "Pix e boleto automáticos"],
      destaque: true,
    },
  ],
  teste: { dias: 14, inicio: "2026-10-07", fim: "2026-10-21", lembrete: "2026-10-19", primeira_fatura: "2026-10-22" },
};

describe("compra pública", () => {
  it("lista só os planos da API, com o selo e o preço do ciclo (PLT-11)", () => {
    const mensal = render(<EscolhaDoPlano catalogo={CATALOGO} ciclo="mensal" aoMudarCiclo={() => {}} aoEscolher={() => {}} />);
    expect(mensal).toContain("14 dias grátis · sem cartão");
    expect(mensal).toContain("Mais escolhido");
    expect(mensal).toContain("R$ 449| /mês");
    expect(mensal).toContain("Até 150 veículos");
    expect(mensal).not.toContain("Completo");
    const anual = render(<EscolhaDoPlano catalogo={CATALOGO} ciclo="anual" aoMudarCiclo={() => {}} aoEscolher={() => {}} />);
    expect(anual).toContain("R$ 4.490| /ano");
  });

  it("checkout mostra o plano escolhido e o teste com as datas da API (PLT-01)", () => {
    const t = render(<Checkout catalogo={CATALOGO} plano={CATALOGO.planos[1]!} ciclo="mensal" aoTrocarPlano={() => {}} aoCriar={() => {}} />);
    for (const p of ["Crie sua conta", "Endereço de acesso", "Profissional", "R$ 449,00 por mês", "19 out", "primeira fatura vence em 22 out", "Criar minha conta"]) {
      expect(t, p).toContain(p);
    }
    expect(t).not.toContain("Tamanho da frota");
  });

  const PRONTO: AndamentoDoPedido = {
    status: "pronto",
    administrador: { nome: "Mariana", email: "mariana@motorapida.com.br" },
    empresa: { nome_exibicao: "Moto Rápida", endereco: "motorapida.girolocadoras.com.br" },
    passos: [
      { passo: "administrador", texto: "Conta de administrador criada", feito_em: "2026-10-07T12:12:04Z" },
      { passo: "banco", texto: "Banco de dados exclusivo da empresa", feito_em: "2026-10-07T12:12:09Z" },
      { passo: "endereco", texto: "Endereço de acesso reservado", feito_em: "2026-10-07T12:12:10Z" },
      { passo: "assinatura", texto: "Teste de 14 dias ativo, até 21 out", feito_em: "2026-10-07T12:12:10Z" },
    ],
    acessar: { url: "https://motorapida.girolocadoras.com.br/convite#token", uma_vez: true },
  };

  it("ambiente pronto mostra os passos com a hora de São Paulo e o link uma vez (D-430-06)", () => {
    const t = render(<AmbientePronto chave="c" inicial={PRONTO} aoRecomecar={() => {}} />);
    expect(t).toContain("Tudo pronto, Mariana");
    expect(t).toContain("motorapida.girolocadoras.com.br");
    expect(t).toContain("09:12:04");
    expect(t).toContain("Acessar meu sistema");
    const depois = render(<AmbientePronto chave="c" inicial={{ ...PRONTO, acessar: null }} aoRecomecar={() => {}} />);
    expect(depois).toContain("Abra o link que enviamos para mariana@motorapida.com.br.");
    expect(depois).not.toContain("Acessar meu sistema");
  });

  it("falha mostra a mensagem da API", () => {
    const t = render(<AmbientePronto chave="c" inicial={{ status: "falhou", mensagem: "Não conseguimos criar o seu sistema agora." }} aoRecomecar={() => {}} />);
    expect(t).toContain("Não conseguimos criar o seu sistema agora.");
  });
});
