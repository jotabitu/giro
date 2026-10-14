// Assistente › Importar dados (T-172) contra docs/telas/html/Onboarding-Importar-*.dc.html e CA-027-22 (IMP-02, IMP-03, IMP-05).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, importacao, type Eu } from "@/lib/api";
import { atualDoTipo, emAndamento, plural, resumoDoArquivo } from "@/lib/importacao";
import { rotaPermitida } from "@/lib/menu";
import { reiniciarImportacaoFalso } from "@/testes/falsos/falso-importacao";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
vi.mock("@/lib/marca-empresa", () => ({ useMarcaDaEmpresa: () => ({ nome: "Moto Rápida", iniciais: "MR", logo: null }) }));

import { ImportarDados } from "./ImportarDados";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

async function pagina(): Promise<string> {
  const cache = new QueryClient();
  const lista = await importacao.listar();
  cache.setQueryData(["importacao", "lista"], lista);
  for (const i of lista) cache.setQueryData(["importacao", "linhas", i.id, i.contagens.com_erro, i.contagens.prontas], await importacao.linhas(i.id, "com_erro"));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ImportarDados />
    </QueryClientProvider>,
  );
}

beforeEach(() => reiniciarImportacaoFalso());

describe("passo Importar dados (Onboarding-Importar)", () => {
  it("sem nada enviado: duas caixas com área de envio, planilha modelo e os botões do passo", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    for (const trecho of ["Moto Rápida", "Configuração inicial", "Salvar e sair", "Passo 7 de 8", "Importar dados", "Convidar equipe", "Traga sua frota e seus clientes", "Baixe a planilha modelo, preencha e envie. Conferimos linha por linha antes de importar.", "Veículos", "Clientes", "Nome, CPF, CNH, telefone e endereço", "Arraste a planilha aqui", "ou clique para escolher (.xlsx ou .csv)", "Baixar planilha modelo de veículos", "Baixar planilha modelo de clientes", "Contratos em andamento você cadastra pela tela de nova locação", "Voltar", "Cadastrar um por um depois", "Continuar"]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("CA-027-22: frota enviada mostra 83 prontos, 3 com erro e as três linhas com a mensagem da API", async () => {
    reiniciarImportacaoFalso({ veiculosEnviados: true });
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    expect(t).toContain("frota-moto-rapida.xlsx · 86 linhas");
    expect(t).toContain("83 prontos");
    expect(t).toContain("3 com erro");
    for (const l of ["14|Placa QXA4B2 está incompleta", "37|Chassi repetido na linha 12", "52|Ano do modelo em branco"]) expect(t, l).toContain(l);
    expect(t).toContain("Corrigir aqui");
    expect(t).toContain("Importar os 83");
    expect(t).toContain("Trocar a planilha");
  });

  it("só o administrador vê o passo (CA-027-16)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await pagina())).toContain("Só o administrador importa dados.");
    expect(rotaPermitida(sessao.eu as Eu, "/implantacao/importar")).toBe(false);
    await entrar("mariana@motorapida.com.br");
    expect(rotaPermitida(sessao.eu as Eu, "/implantacao/importar")).toBe(true);
  });
});

describe("fluxo na API falsa (importacao.md)", () => {
  const planilha = (nome = "frota-moto-rapida.xlsx") => new File(["x"], nome);

  it("enviar valida e fica 83 + 3; corrigir a placa deixa a linha pronta e muda as contagens", async () => {
    const imp = await importacao.enviar({ tipo: "veiculos", arquivo: planilha(), filial_id: 1 });
    expect(imp.contagens).toMatchObject({ linhas: 86, prontas: 83, com_erro: 3 });
    const linha = await importacao.corrigir(imp.id, 14, { placa: "QXA4B21" });
    expect(linha.status).toBe("pronta");
    expect((await importacao.obter(imp.id)).contagens).toMatchObject({ prontas: 84, com_erro: 2 });
  });

  it("caso do seed: 83 importados, depois as 3 corrigidas e importadas dão 86 veículos", async () => {
    const imp = await importacao.enviar({ tipo: "veiculos", arquivo: planilha() });
    const primeira = await importacao.importar(imp.id);
    expect(primeira).toMatchObject({ status: "concluida", contagens: { importadas: 83, com_erro: 3 } });
    await importacao.corrigir(imp.id, 14, { placa: "QXA4B21" });
    await importacao.corrigir(imp.id, 37, { chassi: "9C2KC2210PR004499" });
    await importacao.corrigir(imp.id, 52, { ano_modelo: "2024" });
    const segunda = await importacao.importar(imp.id);
    expect(segunda.contagens.importadas).toBe(86);
  });

  it("IMP-03: acima do limite do plano importa até o limite e devolve o aviso como veio", async () => {
    reiniciarImportacaoFalso({ limite: 30 });
    const imp = await importacao.enviar({ tipo: "veiculos", arquivo: planilha() });
    expect(imp.plano).toMatchObject({ limite: 30, cabem: 30 });
    const r = await importacao.importar(imp.id);
    expect(r.contagens).toMatchObject({ importadas: 30, acima_do_limite: 53 });
    expect(r.aviso?.codigo).toBe("IMP-03");
    expect(r.aviso?.mensagem).toContain("53 ficaram de fora");
  });

  it("ignorar tira a linha; sem linha pronta, importar responde nada_para_importar", async () => {
    const imp = await importacao.enviar({ tipo: "clientes", arquivo: planilha("clientes.csv") });
    expect(imp.contagens).toMatchObject({ prontas: 10, com_erro: 0 });
    for (let n = 1; n <= 10; n++) await importacao.ignorar(imp.id, n);
    await expect(importacao.importar(imp.id)).rejects.toMatchObject({ codigo: "nada_para_importar" });
  });

  it("recusa arquivo de outro tipo, importação repetida em andamento e cancelamento só da validada", async () => {
    await expect(importacao.enviar({ tipo: "veiculos", arquivo: planilha("frota.pdf") })).rejects.toMatchObject({ status: 400 });
    const imp = await importacao.enviar({ tipo: "veiculos", arquivo: planilha() });
    await importacao.cancelar(imp.id);
    await expect(importacao.cancelar(imp.id)).rejects.toMatchObject({ status: 409 });
    expect(atualDoTipo(await importacao.listar(), "veiculos")).toBeNull();
  });

  it("o modelo é um arquivo e o envio vai em multipart com tipo, arquivo e filial", async () => {
    expect((await importacao.modelo("veiculos")).size).toBeGreaterThan(0);
    const { importacaoApi } = await import("@/lib/api/importacao");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 1 }), { status: 202, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    try {
      await importacaoApi.enviar({ tipo: "veiculos", arquivo: planilha("a.xlsx"), filial_id: 1 });
      const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit & { headers: Record<string, string> }];
      expect(url).toBe("/api/importacoes/");
      const f = init.body as FormData;
      expect(f.get("tipo")).toBe("veiculos");
      expect(f.get("filial_id")).toBe("1");
      expect((f.get("arquivo") as File).name).toBe("a.xlsx");
      expect(init.headers["Content-Type"]).toBeUndefined();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

describe("apoio da tela", () => {
  it("em andamento, plural e resumo do arquivo", () => {
    expect(emAndamento({ status: "validando" })).toBe(true);
    expect(emAndamento({ status: "validada" })).toBe(false);
    expect(plural(1, "linha", "linhas")).toBe("1 linha");
    expect(resumoDoArquivo({ arquivo: "frota.xlsx", contagens: { linhas: 86, prontas: 83, com_erro: 3, importadas: 0, acima_do_limite: 0 } })).toBe("frota.xlsx · 86 linhas");
  });
});
