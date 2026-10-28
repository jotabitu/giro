// T-397 · Passo Recebimentos dentro da casca do assistente (docs/api/plataforma.md, "Recebimentos da empresa"; FIN-04, IMP-07, PLT-12).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErroApi, recebimentos, type AndamentoDoAssistente, type SituacaoDosRecebimentos } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { andamentoFalso, ANDAMENTO_PROFISSIONAL } from "@/testes/falsos/falso-implantacao";
import { corposEnviados, definirRecebimentosFalsos, recebimentosEm } from "@/testes/falsos/falso-recebimentos";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {}, replace: () => {} }) }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: null, sair: async () => {} }) }));

import { corpoDosRecebimentos } from "./PassoRecebimentos";
import { CorpoDoPasso } from "./PassoDoAssistente";

const botaoDesligado = (h: string, rotulo: string) => new RegExp(`<button[^>]*disabled[^>]*>${rotulo}</button>`).test(h);

function passo(situacao: SituacaoDosRecebimentos, andamento: AndamentoDoAssistente = ANDAMENTO_PROFISSIONAL): string {
  const cache = new QueryClient();
  cache.setQueryData(["implantacao"], andamento);
  cache.setQueryData(["recebimentos"], recebimentosEm(situacao));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <CorpoDoPasso andamento={andamento} passo="recebimentos" />
    </QueryClientProvider>,
  );
}

beforeEach(() => definirRecebimentosFalsos());

describe("não conectado: formulário pré-preenchido pela sugestão", () => {
  it("fin_04_recebimentos_formulario: campos do corpo, valores da sugestão e o texto da API", () => {
    const h = passo("desconectado");
    expect(h).toContain("Conectar recebimentos");
    expect(h).toContain("Não conectado");
    expect(h).toContain("Conecte para gerar Pix e boleto e dar baixa sozinho.");
    for (const r of ["Razão social ou nome", "CNPJ ou CPF", "Tipo de empresa", "Faturamento mensal estimado", "E-mail financeiro", "Celular com DDD", "CEP", "Logradouro", "Número", "Complemento", "Bairro"]) expect(h).toContain(r);
    for (const v of ["Moto Rápida Locadora LTDA", "12.345.678/0001-95", "mariana@motorapida.com.br", "(85) 99812-4410", "60110-000", "Av. Santos Dumont", "1500", "Aldeota"]) expect(h).toContain(v);
    for (const t of ["Sociedade Limitada (LTDA)", "Microempreendedor Individual (MEI)", "Empresário Individual", "Associação"]) expect(h).toContain(t);
  });

  it("sem os campos que a API não tem: banco, agência, chave Pix e interruptores", () => {
    const h = passo("desconectado");
    for (const t of ["Agência", "Chave Pix", "Banco", "WhatsApp"]) expect(h).not.toContain(t);
  });

  it("imp_07_recebimentos_passo_nao_feito: Pular navega, Continuar fica desligado até a API marcar o passo", () => {
    const h = passo("desconectado");
    expect(h).toContain('href="/implantacao/contrato"');
    expect(h).toContain('href="/implantacao/importar"');
    expect(h).toContain("Pular por agora");
    expect(botaoDesligado(h, "Continuar")).toBe(true);
    // Sem faturamento digitado o envio não vale.
    expect(botaoDesligado(h, "Conectar recebimentos")).toBe(true);
  });
});

describe("as outras situações usam o texto da API e não mostram o formulário", () => {
  it("pendente: em análise, com Pular e Continuar desligado", () => {
    const h = passo("pendente");
    expect(h).toContain("Em análise pelo parceiro");
    expect(h).toContain("O parceiro está conferindo o cadastro.");
    expect(h).not.toContain("<form");
    expect(botaoDesligado(h, "Continuar")).toBe(true);
    expect(h).toContain("Pular por agora");
  });

  it("recusada: texto da API e sem formulário (novo pedido fica com a equipe Giro)", () => {
    const h = passo("recusada");
    expect(h).toContain("Cadastro recusado");
    expect(h).toContain("O parceiro recusou o cadastro. Fale com a equipe Giro.");
    expect(h).not.toContain("<form");
    expect(h).not.toContain("Conectar recebimentos</button>");
  });

  it("imp_07_recebimentos_so_na_aprovacao: aprovada com o passo feito libera o Continuar", () => {
    const feito = andamentoFalso(["marca", "filial", "ramo", "precos", "contrato", "recebimentos"]);
    const h = passo("aprovada", feito);
    expect(h).toContain("Recebimentos ligados");
    expect(h).toContain("Pix e boleto saem pelo parceiro");
    expect(botaoDesligado(h, "Continuar")).toBe(false);
    expect(h).not.toContain("Pode deixar para depois");
  });

  it("aprovada, mas o andamento ainda sem o passo (relendo): Continuar continua desligado", () => {
    expect(botaoDesligado(passo("aprovada"), "Continuar")).toBe(true);
  });
});

describe("carregando", () => {
  it("sem dados ainda: mostra o carregando, sem formulário", () => {
    const cache = new QueryClient();
    cache.setQueryData(["implantacao"], ANDAMENTO_PROFISSIONAL);
    const h = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <CorpoDoPasso andamento={ANDAMENTO_PROFISSIONAL} passo="recebimentos" />
      </QueryClientProvider>,
    );
    expect(h).toContain("Carregando os recebimentos…");
    expect(h).not.toContain("<form");
  });
});

describe("corpo do envio", () => {
  const valores = {
    nome: " Moto Rápida Locadora LTDA ",
    documento: "12.345.678/0001-95",
    tipo: "LIMITED" as const,
    faturamento: "50.000,00",
    email: "financeiro@motorapida.com.br",
    celular: "(85) 99812-4410",
    cep: "60110-000",
    logradouro: "Av. Santos Dumont",
    numero: "1500",
    complemento: "",
    bairro: "Aldeota",
  };

  it("fin_04_corpo: só dígitos nos campos numéricos e o faturamento em centavos", () => {
    expect(corpoDosRecebimentos(valores)).toEqual({
      nome: "Moto Rápida Locadora LTDA",
      documento: "12345678000195",
      email: "financeiro@motorapida.com.br",
      celular: "85998124410",
      cep: "60110000",
      logradouro: "Av. Santos Dumont",
      numero: "1500",
      complemento: "",
      bairro: "Aldeota",
      faturamento_mensal_centavos: 5000000,
      tipo_empresa: "LIMITED",
    });
  });

  it("faturamento que não é valor não monta o corpo", () => {
    expect(corpoDosRecebimentos({ ...valores, faturamento: "" })).toBeNull();
    expect(corpoDosRecebimentos({ ...valores, faturamento: "muito" })).toBeNull();
  });
});

describe("conversa com a API (fixture)", () => {
  const corpo = {
    nome: "Moto Rápida Locadora LTDA",
    documento: "12345678000195",
    email: "financeiro@motorapida.com.br",
    celular: "85998124410",
    cep: "60110000",
    logradouro: "Av. Santos Dumont",
    numero: "1500",
    complemento: "",
    bairro: "Aldeota",
    faturamento_mensal_centavos: 5000000,
    tipo_empresa: "LIMITED" as const,
  };

  it("fin_04_conectar: o 201 volta pendente, sem sugestão e sem ação de conectar", async () => {
    const r = await recebimentos.conectar(corpo);
    expect(r.situacao).toBe("pendente");
    expect(r.sugestao).toBeNull();
    expect(r.acoes.conectar).toBe(false);
    expect(corposEnviados).toHaveLength(1);
  });

  it("os erros do contrato chegam com a mensagem pronta (409, 422, 503, 429)", async () => {
    const erros = [
      new ErroApi(409, "recebimentos_conectados", "Os recebimentos já estão conectados."),
      new ErroApi(422, "parceiro_recusou", "O parceiro não aceitou o CNPJ informado."),
      new ErroApi(503, "parceiro_indisponivel", "O parceiro está fora do ar. Tente de novo em alguns minutos."),
    ];
    for (const e of erros) {
      definirRecebimentosFalsos("desconectado", e);
      await expect(recebimentos.conectar(corpo)).rejects.toBe(e);
      expect(mensagemDoErro(e)).toBe(e.message);
    }
    expect(mensagemDoErro(new ErroApi(429, "muitas_requisicoes", "Muitas tentativas.", { tentar_de_novo_em_segundos: 90 }))).toBe("Muitas tentativas seguidas. Espere 2 minutos e tente de novo.");
  });

  it("400 validacao traz o erro no campo certo", async () => {
    const e = await recebimentos.conectar({ ...corpo, faturamento_mensal_centavos: 0 }).catch((x: unknown) => x);
    expect(e).toBeInstanceOf(ErroApi);
    expect((e as ErroApi).campos).toEqual({ faturamento_mensal_centavos: "Informe um valor maior que zero." });
  });
});
