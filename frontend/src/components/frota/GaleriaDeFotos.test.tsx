// T-414 · Fotos do veículo (VEI-10, AUD-05). Critérios: docs/qa/criterios/T-414.md (CA-414-01 a 14).
// Contrato: docs/api/veiculos.md, "Fotos do veículo". A tela mostra o que a API manda: limite, formato e permissão.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, ErroApi, veiculos, type Eu, type FotoDaGaleria, type FotoDaVistoriaRecente, type VeiculoDetalhe } from "@/lib/api";
import { GaleriaDeFotos } from "./GaleriaDeFotos";
import { GaleriaNaFicha, GaleriaNaFichaCelular, tituloDaGaleria } from "./GaleriaNaFicha";
import { BotaoApagar, CartaoDeFoto, ListaDeRecusas, ZonaDeEnvio } from "./PecasDaGaleria";
import { indiceAposTecla, VisualizadorDeFotos } from "./VisualizadorDeFotos";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

const html = (el: ReactElement) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

const foto = (n: number, extra: Partial<FotoDaGaleria> = {}): FotoDaGaleria => ({
  id: 7000 + n,
  numero: n,
  rotulo: null,
  capa: n === 1,
  url: `/fotos/${n}.jpg`,
  url_download: `/fotos/${n}.jpg?download=1`,
  url_expira_em: "2099-01-01T00:00:00Z",
  nome_arquivo: `QXA-4B21-galeria-${n}.jpg`,
  enviada_em: "2026-10-07T13:02:00Z",
  enviada_por: { id: 1, nome: "Mariana Costa" },
  ...extra,
});
const tres = [foto(1), foto(2), foto(3)];
const acoes = { aoEnviar() {}, aoTrocar() {}, aoUsarComoCapa() {}, aoApagar() {} };

describe("galeria do editar (componente)", () => {
  it("CA-414-01, 05, 06, 07: quem edita vê Selecionar fotos, a capa e, nas outras, Usar como capa, Trocar e Apagar", () => {
    const t = texto(html(<GaleriaDeFotos fotos={tres} total={3} limite={20} podeEditar {...acoes} />));
    expect(t).toContain("3 de 20 fotos");
    expect(t).toContain("Selecionar fotos");
    expect(t).toContain("JPG ou PNG de até 10 MB");
    expect(t).toContain("Capa");
    expect(t.match(/Usar como capa/g)).toHaveLength(2);
    expect(t.match(/Trocar/g)).toHaveLength(3);
    expect(t.match(/Apagar/g)).toHaveLength(3);
  });

  it("CA-414-08, 09: sem `editar` não há botão, e o motivo da API aparece (veículo vendido ou baixado)", () => {
    const t = texto(html(<GaleriaDeFotos fotos={tres} total={3} limite={20} podeEditar={false} motivo="A galeria de veículo baixado fica só para ver." {...acoes} />));
    expect(t).toContain("A galeria de veículo baixado fica só para ver.");
    expect(t).not.toMatch(/Selecionar fotos|Usar como capa|Trocar|Apagar/);
  });

  it("CA-414-02, 03: a recusa de cada arquivo aparece com o nome e a mensagem da API", () => {
    const recusas = [
      { chave: "a", nome: "grande.jpg", mensagem: "Envie uma foto JPG ou PNG de até 10 MB." },
      { chave: "b", nome: "moto-18.jpg", mensagem: "O veículo já tem 20 fotos. Apague uma para enviar outra." },
    ];
    const t = texto(html(<GaleriaDeFotos fotos={tres} total={20} limite={20} podeEditar recusas={recusas} {...acoes} />));
    expect(t).toContain("grande.jpg");
    expect(t).toContain("Envie uma foto JPG ou PNG de até 10 MB.");
    expect(t).toContain("moto-18.jpg");
    expect(t).toContain("O veículo já tem 20 fotos. Apague uma para enviar outra.");
  });

  it("sem foto: Nenhuma foto do veículo.", () => {
    expect(texto(html(<GaleriaDeFotos fotos={[]} total={0} limite={20} podeEditar {...acoes} />))).toContain("Nenhuma foto do veículo.");
  });
});

describe("peças da galeria (reaproveitadas pelo cadastro, T-437)", () => {
  it("zona de envio: tracejada, com ícone, o texto de arrastar e soltar e o botão", () => {
    const h = html(<ZonaDeEnvio limite={20} aoEscolher={() => {}} />);
    expect(h).toContain("border-dashed");
    expect(h).toContain("<svg");
    expect(texto(h)).toContain("Clique para enviar fotos ou arraste arquivos aqui");
    expect(texto(h)).toContain("Selecionar fotos");
    expect(texto(html(<ZonaDeEnvio limite={20} rotulo="Escolher fotos" aoEscolher={() => {}} />))).toContain("Escolher fotos");
    expect(texto(html(<ZonaDeEnvio limite={20} rotulo="Escolher fotos" aoEscolher={() => {}} />))).not.toContain("Selecionar fotos");
  });

  it("D3: o título do visualizador na ficha leva a placa com hífen", async () => {
    const v = await veiculos.obter(501);
    expect(tituloDaGaleria(v.placa)).toBe("Galeria do veículo · QXA-4B21");
  });

  it("cartão de foto: selo de posição, selo Capa sólido, ações no slot e linha no celular (size-16) com cartão a partir de md", () => {
    const h = html(<CartaoDeFoto url="/f.jpg" alt="Foto 1 de 3" posicao={1} capa legenda="Foto 1 de 3" acoes={<button>Minha ação</button>} />);
    expect(h).toContain("wl-badge--solid");
    expect(h).toContain("size-16");
    expect(h).toContain("md:h-[140px]");
    expect(texto(h)).toContain("Minha ação");
    expect(html(<CartaoDeFoto url="/f.jpg" alt="x" posicao={2} capa={false} legenda="Foto 2 de 3" />)).not.toContain("wl-badge--solid");
  });

  it("apagar é o único botão em critical-ink do cartão", () => {
    const h = html(<GaleriaDeFotos fotos={tres} total={3} limite={20} podeEditar {...acoes} />);
    expect(h.match(/text-critical-ink/g)).toHaveLength(3);
    expect(html(<BotaoApagar aoClicar={() => {}} />)).toContain("text-critical-ink");
  });

  it("recusas: faixa critical-soft com ícone, o nome do arquivo e a frase", () => {
    const h = html(<ListaDeRecusas recusas={[{ chave: "a", nome: "grande.jpg", mensagem: "Envie uma foto JPG ou PNG de até 10 MB." }]} />);
    expect(h).toContain("bg-critical-soft");
    expect(h).toContain("<svg");
    expect(texto(h)).toContain("grande.jpg");
    expect(html(<ListaDeRecusas recusas={[]} />)).toBe("");
  });

  it("o contador é um selo", () => {
    expect(html(<GaleriaDeFotos fotos={tres} total={3} limite={20} podeEditar {...acoes} />)).toMatch(/<span class="wl-badge[^"]*"[^>]*>3 de 20 fotos/);
  });
});

describe("visualizador", () => {
  it("CA-414-10: as setas do teclado passam só por esta origem e param nas pontas", () => {
    expect(indiceAposTecla("ArrowRight", 0, 3)).toBe(1);
    expect(indiceAposTecla("ArrowRight", 2, 3)).toBe(2);
    expect(indiceAposTecla("ArrowLeft", 1, 3)).toBe(0);
    expect(indiceAposTecla("ArrowLeft", 0, 3)).toBe(0);
    expect(indiceAposTecla("Tab", 1, 3)).toBe(1);
  });

  it("faixa de miniaturas, setas sobre a imagem e a origem ativa", () => {
    const h = html(<VisualizadorDeFotos aberto aoFechar={() => {}} origem="Galeria do veículo" legenda={(f, _i, t) => `Foto ${f.numero} de ${t}`} fotos={tres} inicial={0} />);
    expect(h).toContain('aria-label="Fotos desta origem"');
    expect(h.match(/h-\[52px\] w-\[72px\]/g)).toHaveLength(3);
    expect(h).toContain('aria-current="true"');
    expect(h).toContain('aria-label="Próxima foto"');
    expect(h).toContain('aria-label="Foto anterior"');
    expect(texto(h)).toContain("Origem: Galeria do veículo (3 fotos)");
  });

  const props = { aberto: true, aoFechar() {}, origem: "Galeria do veículo · QXA4B21", legenda: (f: { numero: number }, _i: number, t: number) => `Foto ${f.numero} de ${t}` };

  it("CA-414-12: Baixar usa o url_download e o nome_arquivo da API, com a validade de 15 minutos", () => {
    const h = html(<VisualizadorDeFotos {...props} fotos={tres} inicial={0} />);
    expect(h).toContain('href="/fotos/1.jpg?download=1"');
    expect(h).toContain('download="QXA-4B21-galeria-1.jpg"');
    expect(texto(h)).toContain("Baixar (QXA-4B21-galeria-1.jpg)");
    expect(texto(h)).toContain("Link válido por 15 minutos.");
    expect(h).toContain('src="/fotos/1.jpg"');
  });

  it("CA-414-10, 14: só passa pelas fotos da origem aberta (a segunda foto não mostra a primeira nem a terceira)", () => {
    const h = html(<VisualizadorDeFotos {...props} fotos={tres} inicial={1} />);
    expect(h).toContain('src="/fotos/2.jpg"');
    expect(h).toContain('src="/fotos/2.jpg"');
    expect(texto(h)).toContain("Foto 2 de 3");
  });

  it("CA-414-12: link vencido não abre nem baixa; pede links novos", () => {
    const h = html(<VisualizadorDeFotos {...props} fotos={[foto(1, { url_expira_em: "2020-01-01T00:00:00Z" })]} inicial={0} aoAtualizarLinks={() => {}} />);
    expect(texto(h)).toContain("O link desta foto venceu");
    expect(texto(h)).toContain("Atualizar os links");
    expect(h).not.toContain("download=");
  });

  it("AUD-05, PLT-07: suporte em só ver recebe os links nulos e a tela não finge que tem foto", () => {
    const h = html(<VisualizadorDeFotos {...props} fotos={[foto(1, { url: null, url_download: null, url_expira_em: null })]} inicial={0} />);
    expect(texto(h)).toContain("Sem link para esta foto");
    expect(h).not.toContain("<img");
    expect(h).not.toContain("Baixar");
  });

  it("fechado não desenha nada", () => {
    expect(html(<VisualizadorDeFotos {...props} aberto={false} fotos={tres} inicial={0} />)).toBe("");
  });

  it("vistoria: o rótulo da posição e as de avaria passam pela mesma origem", () => {
    const vistoria: FotoDaVistoriaRecente[] = [
      { id: 901, numero: 1, rotulo: "Frente", posicao: "frente", tirada_em: "2026-09-23T12:00:00Z", avaria_id: null, url: "/v/1.jpg", url_download: "/v/1.jpg?d=1", url_expira_em: "2099-01-01T00:00:00Z", nome_arquivo: "QXA-4B21-vistoria-saida-frente.jpg" },
      { id: 902, numero: 2, rotulo: "Avaria 1", posicao: "avaria", tirada_em: "2026-09-23T12:01:00Z", avaria_id: 51, url: "/v/2.jpg", url_download: "/v/2.jpg?d=1", url_expira_em: "2099-01-01T00:00:00Z", nome_arquivo: "QXA-4B21-vistoria-saida-avaria-1.jpg" },
    ];
    const h = html(<VisualizadorDeFotos aberto aoFechar={() => {}} origem="Vistoria de saída · LOC-2841 · 23 set" legenda={(f, i, t) => `${f.rotulo} · ${i + 1} de ${t}`} fotos={vistoria} inicial={1} />);
    expect(texto(h)).toContain("Avaria 1 · 2 de 2");
    expect(texto(h)).toContain("Baixar (QXA-4B21-vistoria-saida-avaria-1.jpg)");
  });
});

describe("galeria na ficha", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("CA-414-10: a ficha do QXA-4B21 mostra as 3 fotos, a capa primeiro, e Gerenciar fotos para quem edita (desktop e celular)", async () => {
    const v = await veiculos.obter(501);
    for (const el of [<GaleriaNaFicha key="d" v={v} />, <GaleriaNaFichaCelular key="c" v={v} />]) {
      const h = html(el);
      expect(h).toContain("Ampliar a foto 1 de 3, capa");
      expect(h).toContain("Ampliar a foto 3 de 3");
      expect(texto(h)).toContain("Gerenciar fotos");
    }
    const d = html(<GaleriaNaFicha v={v} />);
    expect(texto(d)).toContain("3 de 20 fotos");
    expect(d).toContain("grid-cols-3");
    expect(d).toContain("wl-badge--solid");
    expect(d).toMatch(/wl-btn wl-btn--quiet wl-btn--sm[^>]*>Gerenciar fotos/);
  });

  it("CA-414-13: sem fotos, Nenhuma foto do veículo.; quem edita vê Adicionar fotos para o editar, quem só consulta não vê", async () => {
    const v = await veiculos.obter(502);
    expect(v.galeria.total).toBe(0);
    const h = html(<GaleriaNaFicha v={v} />);
    expect(texto(h)).toContain("Nenhuma foto do veículo.");
    expect(h).toContain('href="/veiculos/502/editar"');
    expect(texto(h)).toContain("Adicionar fotos");
    const semAcao: VeiculoDetalhe = { ...v, acoes: { ...v.acoes, editar_fotos: false } };
    expect(texto(html(<GaleriaNaFicha v={semAcao} />))).not.toContain("Adicionar fotos");
    expect(texto(html(<GaleriaNaFichaCelular v={semAcao} />))).not.toContain("Adicionar fotos");
  });
});

describe("fotos na API falsa (regras da API que a tela obedece)", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));
  const arquivo = (nome: string, bytes = 10) => new File([new Uint8Array(bytes)], nome);

  it("CA-414-05: a primeira foto vira capa, Usar como capa muda, e apagar a capa passa a capa para a mais antiga", async () => {
    const a = await veiculos.enviarFoto(503, arquivo("moto-1.jpg"));
    expect(a.fotos[0]?.capa).toBe(true);
    const b = await veiculos.enviarFoto(503, arquivo("moto-2.jpg"));
    const segunda = b.fotos.find((f) => !f.capa)!;
    const c = await veiculos.usarComoCapa(503, segunda.id);
    expect(c.fotos[0]?.id).toBe(segunda.id);
    expect(c.fotos[0]?.numero).toBe(1);
    const d = await veiculos.apagarFoto(503, segunda.id);
    expect(d.total).toBe(1);
    expect(d.fotos[0]?.capa).toBe(true);
  });

  it("CA-414-06: trocar mantém a posição e a capa, e o total", async () => {
    const antes = await veiculos.fotos(501);
    const capa = antes.fotos[0]!;
    const depois = await veiculos.trocarFoto(501, capa.id, arquivo("moto-1.jpg"));
    expect(depois.total).toBe(antes.total);
    expect(depois.fotos[0]?.capa).toBe(true);
    expect(depois.fotos[0]?.id).not.toBe(capa.id);
  });

  it("CA-414-02: arquivo fora do formato ou grande demais volta 400 com a mensagem do campo arquivo", async () => {
    for (const a of [arquivo("documento.pdf"), arquivo("moto.heic"), arquivo("grande.jpg", 11 * 1024 * 1024)]) {
      const e = await veiculos.enviarFoto(504, a).catch((x: unknown) => x);
      expect(e).toBeInstanceOf(ErroApi);
      expect((e as ErroApi).campos?.arquivo).toBe("Envie uma foto JPG ou PNG de até 10 MB.");
    }
  });

  it("CA-414-03: com 20 fotos a seguinte é recusada com a mensagem do limite", async () => {
    for (let i = 0; i < 20; i++) await veiculos.enviarFoto(505, arquivo(`moto-${i}.jpg`));
    const e = await veiculos.enviarFoto(505, arquivo("moto-21.jpg")).catch((x: unknown) => x);
    expect((e as ErroApi).campos?.arquivo).toBe("O veículo já tem 20 fotos. Apague uma para enviar outra.");
    expect((await veiculos.fotos(505)).total).toBe(20);
  });

  it("CA-414-08: a ficha de quem não edita vem com editar_fotos falso e a API recusa mexer (403)", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const v = await veiculos.obter(501);
    expect(v.acoes.editar_fotos).toBe(false);
    expect(v.galeria.total).toBeGreaterThan(0);
    const e = await veiculos.enviarFoto(501, arquivo("moto-1.jpg")).catch((x: unknown) => x);
    expect((e as ErroApi).status).toBe(403);
  });
});
