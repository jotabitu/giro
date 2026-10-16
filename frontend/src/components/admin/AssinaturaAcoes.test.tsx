// T-187 · Assinatura completa: mudar e comparar planos, forma de pagamento, faturas e dados fiscais (docs/api/assinatura.md, PLT-04, PLT-13 a PLT-15).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { assinatura, type Assinatura } from "@/lib/api";
import { definirAccess } from "@/lib/api/http";
import { assinaturaApi } from "@/lib/api/assinatura";
import { definirAssinaturaFalsa, pagarFaturaNoParceiroFalso } from "@/testes/falsos/falso-assinatura";
import { DadosFiscaisDaAssinatura } from "./DadosFiscaisDaAssinatura";
import { FaturasDaAssinatura } from "./FaturasDaAssinatura";
import { FormaDePagamentoDaAssinatura } from "./FormaDePagamentoDaAssinatura";
import { PlanosDaAssinatura } from "./PlanosDaAssinatura";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const com = (cache: QueryClient, filho: React.ReactNode) => renderToStaticMarkup(<QueryClientProvider client={cache}>{filho}</QueryClientProvider>);

beforeEach(() => definirAssinaturaFalsa(null));
afterEach(() => definirAssinaturaFalsa(null));

describe("Mudar de plano e Comparar planos (PLT-04, CA-ASS-13, 15, 18)", () => {
  async function lista(podeMudar: boolean) {
    const cache = new QueryClient();
    cache.setQueryData(["assinatura", "planos"], await assinatura.planos());
    return com(cache, <PlanosDaAssinatura podeMudar={podeMudar} aoFechar={() => {}} aoConcluir={() => {}} />);
  }

  it("mudar: os três planos, o atual marcado e o que o Essencial não comporta, como a API disse", async () => {
    const html = await lista(true);
    const t = texto(html);
    for (const trecho of ["Mudar de plano", "Essencial", "R$ 199,00 por mês", "Profissional", "Seu plano", "R$ 449,00 por mês", "Completo", "R$ 899,00 por mês", "Veículos, filiais e usuários sem limite"]) expect(t, trecho).toContain(trecho);
    expect(t).toContain("Seu uso não cabe neste plano hoje.");
    expect(t).toContain("86 de 30 veículos");
    expect(t).toContain("5 de 3 usuários");
    expect(t).toContain("Resolva antes: 1 despesa aguardando aprovação e 2 despesas a pagar");
    expect(t).not.toContain("1 de 1 filiais");
    expect(html).toMatch(/<button[^>]*>[^<]*Mudar para o Completo/);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>[^<]*Descer para o Essencial/);
  });

  it("comparar (sem acoes.mudar_plano): só a comparação, sem botão de escolha", async () => {
    const t = texto(await lista(false));
    expect(t).toContain("Comparar planos");
    expect(t).toContain("Completo");
    expect(t).not.toContain("Mudar para o Completo");
    expect(t).not.toContain("Descer para o");
  });

  it("simular o Completo no teste: vale agora, sem diferença, primeira fatura de R$ 899,00 (CA-ASS-13)", async () => {
    const s = await assinatura.simularMudanca({ plano_id: 3, ciclo: "mensal" });
    expect(s).toMatchObject({ tipo: "upgrade", vale_em: "2026-10-10", diferenca_centavos: 0, fatura_diferenca: null });
    expect(s.mensagem).toBe("O plano Completo vale agora. A primeira fatura, em 22 out, fica em R$ 899,00.");
    expect(s.proxima_fatura).toMatchObject({ vencimento: "2026-10-22", valor_centavos: 89900 });
  });

  it("confirmar muda o plano, a próxima fatura e some a oferta", async () => {
    const depois = await assinatura.mudarPlano({ plano_id: 3, ciclo: "mensal", confirmar_valor_centavos: 0 });
    expect(depois.plano).toMatchObject({ nome: "Completo", preco_contratado_centavos: 89900 });
    expect(depois.proxima_fatura?.valor_centavos).toBe(89900);
    expect(depois.oferta).toBeNull();
  });

  it("valor que mudou entre simular e confirmar: 409 valor_mudou, nada muda", async () => {
    await expect(assinatura.mudarPlano({ plano_id: 3, ciclo: "mensal", confirmar_valor_centavos: 100 })).rejects.toMatchObject({ status: 409, codigo: "valor_mudou" });
    expect((await assinatura.obter()).plano.nome).toBe("Profissional");
  });

  it("downgrade que não cabe: 422 PLT-04 com o que excede e o que está aberto (CA-ASS-15)", async () => {
    await expect(assinatura.simularMudanca({ plano_id: 1, ciclo: "mensal" })).rejects.toMatchObject({
      status: 422,
      codigo: "PLT-04",
      detalhes: { veiculos: { usado: 86, limite: 30 }, usuarios: { usado: 5, limite: 3 }, abertos_texto: "1 despesa aguardando aprovação e 2 despesas a pagar" },
    });
  });

  it("outro ciclo e o mesmo plano são recusados (CA-ASS-18)", async () => {
    await expect(assinatura.simularMudanca({ plano_id: 3, ciclo: "anual" })).rejects.toMatchObject({ codigo: "mudanca_ciclo" });
    await expect(assinatura.simularMudanca({ plano_id: 2, ciclo: "mensal" })).rejects.toMatchObject({ codigo: "mesmo_plano" });
  });

  it("desfazer sem mudança agendada é 404", async () => {
    await expect(assinatura.desfazerMudanca()).rejects.toMatchObject({ status: 404 });
  });
});

describe("Forma de pagamento (PLT-13, ADR 0023)", () => {
  const seed = async () => (await assinatura.obter()).forma_pagamento as NonNullable<Assinatura["forma_pagamento"]>;

  it("sem forma: a situação da API, as três opções e nenhuma marcada", async () => {
    const html = com(new QueryClient(), <FormaDePagamentoDaAssinatura forma={await seed()} pode />);
    const t = texto(html);
    for (const trecho of ["Forma de pagamento", "Nenhuma cadastrada. Escolha até 21 out para não perder o acesso.", "Cartão de crédito", "Cobrança automática todo mês", "Pix automático", "Autoriza uma vez no app do banco", "Boleto", "Enviado por e-mail 5 dias antes"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).not.toContain("Em uso");
    expect(html).not.toContain('disabled=""');
  });

  it("sem acoes.escolher_forma_pagamento as opções ficam paradas; a forma escolhida aparece Em uso", async () => {
    const r = await assinatura.escolherForma("boleto");
    const html = com(new QueryClient(), <FormaDePagamentoDaAssinatura forma={r.forma_pagamento} pode={false} />);
    expect(texto(html)).toContain("Em uso");
    expect(html.match(/disabled=""/g)).toHaveLength(3);
  });

  it("cada forma devolve o próximo passo da API: boleto nenhum, Pix com o copia e cola, cartão com a página do parceiro", async () => {
    expect((await assinatura.escolherForma("boleto")).proximo_passo).toBeNull();
    const pix = await assinatura.escolherForma("pix_automatico");
    expect(pix.proximo_passo).toMatchObject({ tipo: "autorizar_pix", pix_copia_e_cola: expect.stringMatching(/^0002/), expira_em: expect.any(String) });
    expect(pix.forma_pagamento.situacao.codigo).toBe("aguardando_autorizacao");
    const cartao = await assinatura.escolherForma("cartao");
    expect(cartao.proximo_passo).toMatchObject({ tipo: "pagina_parceiro", fatura: "FAT-0001", url: expect.stringContaining("https://") });
    expect(cartao.forma_pagamento.situacao.codigo).toBe("cartao_na_primeira_fatura");
    // Escolher a forma não muda o estado da empresa (CA-ASS-02).
    expect((await assinatura.obter()).status).toBe("em_teste");
  });
});

describe("Faturas (PLT-14, CA-ASS-11, 12, 27)", () => {
  async function tabela(forma: "boleto" | null) {
    if (forma) await assinatura.escolherForma(forma);
    const cache = new QueryClient();
    cache.setQueryData(["assinatura", "faturas"], await assinatura.faturas());
    return com(cache, <FaturasDaAssinatura forma={forma} />);
  }

  it("sem forma: a FAT-0001 sem Pagar, e a linha do teste", async () => {
    const t = texto(await tabela(null));
    expect(t).toContain("Sem forma de pagamento");
    expect(t).toContain("Teste grátis de 14 dias");
    expect(t).not.toContain("Pagar");
  });

  it("com forma: Pagar aparece pela acoes.pagar da API", async () => {
    const t = texto(await tabela("boleto"));
    expect(t).toContain("Vence em 22 out");
    expect(t).toContain("Pagar");
  });

  it("pagar sem forma e sem meio é 422; com meio devolve a cobrança sem trocar a forma", async () => {
    await expect(assinatura.pagarFatura("FAT-0001")).rejects.toMatchObject({ status: 422, codigo: "sem_forma_pagamento" });
    const pix = await assinatura.pagarFatura("FAT-0001", "pix");
    expect(pix).toMatchObject({ forma: "pix", pix_copia_e_cola: expect.stringMatching(/^0002/), url_pagina: null });
    const boleto = await assinatura.pagarFatura("FAT-0001", "boleto");
    expect(boleto).toMatchObject({ forma: "boleto", linha_digitavel: expect.any(String), url_boleto: expect.stringContaining("https://") });
    const cartao = await assinatura.pagarFatura("FAT-0001", "cartao");
    expect(cartao.url_pagina).toContain("https://");
    expect((await assinatura.obter()).forma_pagamento?.forma).toBeNull();
  });

  it("fatura paga: recibo no detalhe e 409 ao pagar de novo", async () => {
    pagarFaturaNoParceiroFalso();
    const f = await assinatura.fatura("FAT-0001");
    expect(f.acoes.recibo).toBe(true);
    expect(f.recibo_url).toContain("https://");
    await expect(assinatura.pagarFatura("FAT-0001", "pix")).rejects.toMatchObject({ status: 409, codigo: "fatura_nao_pagavel" });
  });
});

describe("Dados da nota fiscal (PLT-15, CA-ASS-29, 48)", () => {
  it("mostra razão social, CNPJ, e-mail e endereço; Editar só com a ação da API", async () => {
    const dados = (await assinatura.obter()).dados_fiscais as NonNullable<Assinatura["dados_fiscais"]>;
    const com_ = texto(com(new QueryClient(), <DadosFiscaisDaAssinatura dados={dados} pode aoConcluir={() => {}} />));
    for (const trecho of ["Dados da nota fiscal", "Editar", "Moto Rápida Locações Ltda", "CNPJ 12.345.678/0001-95", "financeiro@motorapida.com.br", "Av. Bezerra de Menezes, 1200", "São Gerardo", "Fortaleza, CE", "CEP 60325-000"]) {
      expect(com_, trecho).toContain(trecho);
    }
    expect(texto(com(new QueryClient(), <DadosFiscaisDaAssinatura dados={dados} pode={false} aoConcluir={() => {}} />))).not.toContain("Editar");
  });

  it("endereço ainda vazio pede para completar", async () => {
    const dados = { ...((await assinatura.obter()).dados_fiscais as NonNullable<Assinatura["dados_fiscais"]>), endereco: null };
    expect(texto(com(new QueryClient(), <DadosFiscaisDaAssinatura dados={dados} pode aoConcluir={() => {}} />))).toContain("Endereço ainda não informado");
  });

  it("salvar devolve os dados novos; CNPJ não muda por aqui", async () => {
    const r = await assinatura.editarDadosFiscais({ razao_social: "Moto Rápida Ltda", email_cobranca: "contas@motorapida.com.br" });
    expect(r.dados_fiscais).toMatchObject({ razao_social: "Moto Rápida Ltda", email_cobranca: "contas@motorapida.com.br", cnpj: "12345678000195" });
    expect((await assinatura.obter()).dados_fiscais?.razao_social).toBe("Moto Rápida Ltda");
    await expect(assinatura.editarDadosFiscais({ cnpj: "11111111000111" } as never)).rejects.toMatchObject({ status: 400, campos: { cnpj: "O CNPJ não muda por aqui. Fale com o suporte." } });
  });
});

describe("cliente HTTP real", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    fetchMock = vi.fn(async () => new Response(JSON.stringify({}), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    definirAccess("abc");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    definirAccess(null);
  });
  const chamada = (n = 0) => {
    const [url, init] = fetchMock.mock.calls[n] as unknown as [string, RequestInit];
    return { url, metodo: init.method, corpo: init.body ? JSON.parse(String(init.body)) : undefined };
  };

  it("rotas, métodos e corpos do contrato", async () => {
    await chamarTudo();
    expect(chamada(0)).toMatchObject({ url: "/api/assinatura/mudanca-plano/simular/", metodo: "POST", corpo: { plano_id: 3, ciclo: "mensal" } });
    expect(chamada(1)).toMatchObject({ url: "/api/assinatura/mudanca-plano/", metodo: "POST", corpo: { plano_id: 3, ciclo: "mensal", confirmar_valor_centavos: 0 } });
    expect(chamada(2)).toMatchObject({ url: "/api/assinatura/mudanca-plano/", metodo: "DELETE" });
    expect(chamada(3)).toMatchObject({ url: "/api/assinatura/forma-pagamento/", metodo: "PUT", corpo: { forma: "pix_automatico" } });
    expect(chamada(4)).toMatchObject({ url: "/api/assinatura/faturas/FAT-0001/pagar/", metodo: "POST", corpo: { meio: "pix" } });
    expect(chamada(5)).toMatchObject({ url: "/api/assinatura/faturas/FAT-0001/pagar/", metodo: "POST", corpo: {} });
    expect(chamada(6)).toMatchObject({ url: "/api/assinatura/dados-fiscais/", metodo: "PATCH", corpo: { razao_social: "X" } });
  });

  async function chamarTudo() {
    await assinaturaApi.simularMudanca({ plano_id: 3, ciclo: "mensal" });
    await assinaturaApi.mudarPlano({ plano_id: 3, ciclo: "mensal", confirmar_valor_centavos: 0 });
    await assinaturaApi.desfazerMudanca();
    await assinaturaApi.escolherForma("pix_automatico");
    await assinaturaApi.pagarFatura("FAT-0001", "pix");
    await assinaturaApi.pagarFatura("FAT-0001");
    await assinaturaApi.editarDadosFiscais({ razao_social: "X" });
  }
});
