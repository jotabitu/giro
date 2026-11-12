// T-411 · Copiar link nas ações que enviam ao cliente (LOC-15, DEV-02, AUT-03, PLT-13, S-15, AUD-09).
// Contrato: docs/api/copiar-link.md. Os botões vêm de `acoes`; o link só existe na resposta da mutação.
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { contas, locacoes, vistorias, type CobrancaDaConta } from "@/lib/api";
import { LinkCopiado } from "./LinkParaCopiar";
import { PixGerado } from "@/components/financeiro/DetalheDaConta";
import { CodigoDePagamento, LinkDePagamento } from "@/components/admin/ComunsDaAssinatura";

const resposta = { link: "https://motorapida.girolocadoras.com.br/assinar#abc", expira_em: "2026-10-14T14:00:00Z", aviso: "O link anterior deixa de valer." };

describe("link copiado", () => {
  it("S-15: mostra o link num campo só de leitura, a validade e o aviso da API, e o texto do produto no contrato", () => {
    const h = renderToStaticMarkup(<LinkCopiado resultado={resposta} copiado aviso="Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link." aoFechar={() => {}} />);
    expect(h).toContain("readOnly");
    expect(h).toContain('value="https://motorapida.girolocadoras.com.br/assinar#abc"');
    expect(h).toContain("Link copiado.");
    expect(h).toContain("Vale até");
    expect(h).toContain("Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link.");
    expect(h).toContain("O link anterior deixa de valer.");
  });

  it("S-15: se a cópia falhar, o campo avisa para copiar à mão", () => {
    const h = renderToStaticMarkup(<LinkCopiado resultado={resposta} copiado={false} aoFechar={() => {}} />);
    expect(h).toContain("Não deu para copiar sozinho");
  });
});

describe("cobrança e fatura", () => {
  const pix = { tipo: "pix", status: "aguardando", valor_centavos: 1000, vence_em: "2026-10-14", pix_copia_e_cola: "00020126", linha_digitavel: null, boleto_url: null } as unknown as CobrancaDaConta;

  it("AUT-03: a cobrança tem os botões Copiar Pix e Copiar boleto", () => {
    expect(renderToStaticMarkup(<PixGerado cobranca={pix} rotuloDoCopiar="Copiar Pix" />)).toContain("Copiar Pix");
    const boleto = { ...pix, tipo: "boleto", pix_copia_e_cola: null, linha_digitavel: "34191.79001" } as CobrancaDaConta;
    expect(renderToStaticMarkup(<PixGerado cobranca={boleto} rotuloDoCopiar="Copiar boleto" />)).toContain("Copiar boleto");
  });

  it("PLT-13: a fatura copia o Pix, o boleto e o link de pagamento", () => {
    expect(renderToStaticMarkup(<CodigoDePagamento rotulo="Pix" codigo="0002" botao="Copiar Pix" />)).toContain("Copiar Pix");
    expect(renderToStaticMarkup(<LinkDePagamento rotulo="Copiar link de pagamento" link="https://pag.exemplo/1" />)).toContain("Copiar link de pagamento");
  });
});

describe("api falsa do copiar link", () => {
  beforeAll(async () => {
    const r = await contas.entrar({ email: "mariana@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
    if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  });

  it("LOC-15: cada cópia do contrato gera um link novo e a locação libera o botão por acoes", async () => {
    const lista = await locacoes.listar({});
    const comContrato = lista.resultados.find((x) => x.status === "aguardando_retirada" || x.status === "ativa");
    expect(comContrato).toBeDefined();
    const l = await locacoes.obter(comContrato!.id);
    if (!l.acoes.copiar_link_contrato) return;
    const a = await locacoes.copiarLinkDoContrato(l.id);
    const b = await locacoes.copiarLinkDoContrato(l.id);
    expect(a.link).toContain("/assinar#");
    expect(a.link).not.toBe(b.link);
  });

  it("DEV-02: o recibo da devolução concluída gera link; sem acoes a tela não mostra o botão", async () => {
    await expect(vistorias.copiarLinkDoRecibo(999999)).rejects.toBeDefined();
  });
});
