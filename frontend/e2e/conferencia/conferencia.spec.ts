// T-425 · Conferência lado a lado: abre a tela de `docs/telas/html` e a página do app com o seed, a 1440 e a 390 px,
// e grava uma imagem com as duas lado a lado, mais um `resumo.md` com o que dá para medir sem olho (respostas de erro,
// erro de console, rolagem lateral). Não compara pixel: os números e os componentes mudam de propósito. Quem olha é a
// revisão do design-system, e o frontend anexa a pasta no handoff.
//
// Uso (na pasta frontend, com a stack no ar e o seed de 07 out):
//   npm run conferencia                              todas as telas de e2e/conferencia/telas.ts
//   TELA=Frota,Caixa npm run conferencia             só as telas citadas
//   CONFERENCIA_PASTA=../tarefas/handoffs/anexos/T-410 npm run conferencia
// Stack isolada: E2E_PORTA_FRONTEND=3100 E2E_PORTA_BACKEND=8100 npm run conferencia (nunca o `npm run e2e` no banco `giro`).
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Browser, type BrowserContext } from "@playwright/test";
import { executarNoBackend } from "../suporte/ambiente";
import { SENHA } from "../suporte/tela";
import { EMAIL_DO_PERFIL, TELAS, type Perfil, type TelaDeConferencia } from "./telas";

const RAIZ = path.resolve(__dirname, "../../..");
const HTML = path.join(RAIZ, "docs", "telas", "html");
const PASTA = path.resolve(process.cwd(), process.env.CONFERENCIA_PASTA ?? path.join(RAIZ, "tarefas", "handoffs", "anexos", "conferencia"));
const FILTRO = (process.env.TELA ?? "").split(",").map((t) => t.trim().toLowerCase()).filter(Boolean);

const LARGURAS = [
  { largura: 1440, altura: 900, sufixo: "Desktop", movel: false },
  { largura: 390, altura: 844, sufixo: "Mobile", movel: true },
] as const;

const escolhidas = TELAS.filter((t) => FILTRO.length === 0 || FILTRO.includes(t.nome.toLowerCase()));

type Linha = { tela: string; largura: number; situacao: string; achados: string[] };

test("referência e app lado a lado", async ({ browser, baseURL }) => {
  test.setTimeout(30 * 60_000);
  expect(escolhidas.length, `TELA=${process.env.TELA ?? ""} não bate com nenhuma tela de telas.ts`).toBeGreaterThan(0);
  mkdirSync(PASTA, { recursive: true });
  const linhas: Linha[] = [];

  const perfis = [...new Set(escolhidas.map((t) => t.perfil))];
  for (const perfil of perfis) {
    for (const v of LARGURAS) {
      // Um login por perfil e por tamanho: o refresh do token é de uso único, então a sessão não se reaproveita entre contextos.
      const estado = await entrarEGuardar(browser, baseURL!, perfil, v);
      const contexto = await browser.newContext({
        baseURL: baseURL!,
        storageState: estado,
        viewport: { width: v.largura, height: v.altura },
        isMobile: v.movel,
        hasTouch: v.movel,
        deviceScaleFactor: v.movel ? 2 : 1,
        locale: "pt-BR",
        timezoneId: "America/Sao_Paulo",
      });
      for (const tela of escolhidas.filter((t) => t.perfil === perfil)) {
        linhas.push(await conferir(browser, contexto, tela, v));
      }
      await contexto.close();
    }
  }

  const md = [
    "# Conferência lado a lado (T-425)",
    "",
    `Gerada por \`npm run conferencia\` em ${new Date().toISOString().slice(0, 16).replace("T", " ")} UTC, com o seed em 07 out 2026. Esquerda: tela de referência. Direita: página do app.`,
    "Sem comparação por pixel. A coluna \"Medido\" traz só o que dá para medir: respostas de erro da API, erro de console e rolagem lateral. A diferença visual quem aponta é a revisão do design-system.",
    "",
    "| Tela | Largura | Imagem | Medido |",
    "| --- | --- | --- | --- |",
    ...linhas.map((l) => `| ${l.tela} | ${l.largura} px | ${l.situacao === "ok" ? `[${l.tela}-${l.largura}.png](${l.tela}-${l.largura}.png)` : l.situacao} | ${l.achados.length ? l.achados.join("; ") : "sem achados"} |`),
    "",
  ].join("\n");
  writeFileSync(path.join(PASTA, "resumo.md"), md, { encoding: "utf8" });
  console.log(`Conferência gravada em ${PASTA} (${linhas.length} imagens).`);
});

const ultimoCodigo = new Map<Perfil, string>();

/** O código de 2 etapas só vale uma vez por janela de 30 s: no segundo login do mesmo perfil, espera o código mudar. */
async function codigoNovo(perfil: Perfil): Promise<string> {
  for (let i = 0; i < 12; i++) {
    const codigo = executarNoBackend(`
from seed.moto_rapida import codigo_de_2fa
print("CODIGO=" + codigo_de_2fa("${EMAIL_DO_PERFIL[perfil]}"))
`).CODIGO as string;
    if (codigo !== ultimoCodigo.get(perfil)) {
      ultimoCodigo.set(perfil, codigo);
      return codigo;
    }
    await new Promise((r) => setTimeout(r, 5000));
  }
  throw new Error(`O código de 2 etapas de ${perfil} não mudou em 60 s.`);
}

async function entrarEGuardar(browser: Browser, baseURL: string, perfil: Perfil, v: (typeof LARGURAS)[number]) {
  const contexto = await browser.newContext({ baseURL, locale: "pt-BR", timezoneId: "America/Sao_Paulo", viewport: { width: v.largura, height: v.altura } });
  const page = await contexto.newPage();
  await page.goto("/entrar");
  await page.locator("input[name=email]").fill(EMAIL_DO_PERFIL[perfil]);
  await page.locator("input[name=senha]").fill(SENHA);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  if (perfil === "mariana" || perfil === "lucia") {
    const codigo = await codigoNovo(perfil);
    await page.getByLabel("Dígito 1 de 6").click();
    await page.keyboard.type(codigo);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
  }
  await expect(page).toHaveURL(/\/inicio/, { timeout: 30_000 });
  const estado = await contexto.storageState();
  await contexto.close();
  return estado;
}

async function conferir(browser: Browser, contexto: BrowserContext, tela: TelaDeConferencia, v: (typeof LARGURAS)[number]): Promise<Linha> {
  const linha: Linha = { tela: tela.nome, largura: v.largura, situacao: "ok", achados: [] };
  const arquivoRef = path.join(HTML, `${tela.referencia}-${v.sufixo}.dc.html`);
  if (!existsSync(arquivoRef)) {
    linha.situacao = `sem tela de referência ${v.sufixo.toLowerCase()}`;
    return linha;
  }

  // Referência: o HTML estático abre direto do disco (os estilos vêm de docs/design-system).
  const ref = await browser.newContext({ viewport: { width: v.largura, height: v.altura }, deviceScaleFactor: v.movel ? 2 : 1 });
  const paginaRef = await ref.newPage();
  await paginaRef.goto(`file:///${arquivoRef.replace(/\\/g, "/")}`);
  await paginaRef.waitForTimeout(1500);
  const imagemRef = await paginaRef.screenshot({ fullPage: true });
  await ref.close();

  // App: a mesma largura, com a rota do seed. Quem mede é a resposta e o console, não o olho.
  const pagina = await contexto.newPage();
  const respostas: string[] = [];
  const erros: string[] = [];
  pagina.on("response", (r) => {
    if (r.status() >= 400) respostas.push(`${r.status()} ${new URL(r.url()).pathname}`);
  });
  pagina.on("console", (m) => {
    if (m.type() === "error" && !m.text().startsWith("Failed to load resource")) erros.push(m.text().slice(0, 120));
  });
  pagina.on("pageerror", (e) => erros.push(`pageerror: ${e.message.slice(0, 120)}`));
  await pagina.goto(tela.rota);
  await pagina.waitForLoadState("networkidle").catch(() => undefined);
  await pagina.waitForTimeout(1200);
  const { larguraDoConteudo, janela } = await pagina.evaluate(() => ({ larguraDoConteudo: document.documentElement.scrollWidth, janela: window.innerWidth }));
  const imagemApp = await pagina.screenshot({ fullPage: true });
  const url = pagina.url();
  await pagina.close();

  if (larguraDoConteudo > janela) linha.achados.push(`rolagem lateral (${larguraDoConteudo} px numa janela de ${janela} px)`);
  if (respostas.length) linha.achados.push(`respostas de erro: ${[...new Set(respostas)].slice(0, 4).join(", ")}`);
  if (erros.length) linha.achados.push(`erro no console: ${erros[0]}`);
  if (!url.includes(tela.rota.split("?")[0]!)) linha.achados.push(`a rota abriu em ${new URL(url).pathname}`);

  await compor(browser, tela.nome, v, imagemRef, imagemApp, path.join(PASTA, `${tela.nome}-${v.largura}.png`));
  return linha;
}

/** Junta as duas capturas numa imagem só, com a referência à esquerda e o app à direita. */
async function compor(browser: Browser, nome: string, v: (typeof LARGURAS)[number], ref: Buffer, app: Buffer, saida: string) {
  const dado = (b: Buffer) => `data:image/png;base64,${b.toString("base64")}`;
  const contexto = await browser.newContext({ viewport: { width: v.largura * 2 + 48, height: 600 } });
  const pagina = await contexto.newPage();
  await pagina.setContent(`<!doctype html><meta charset="utf-8"><body style="margin:0;padding:16px;background:#fff;font:600 14px system-ui">
<div style="display:flex;gap:16px;align-items:flex-start">
  <figure style="margin:0;width:${v.largura}px"><figcaption style="padding:0 0 8px">Referência · ${nome} · ${v.largura} px</figcaption><img style="width:${v.largura}px;display:block;border:1px solid #ccc" src="${dado(ref)}"></figure>
  <figure style="margin:0;width:${v.largura}px"><figcaption style="padding:0 0 8px">App · ${nome} · ${v.largura} px</figcaption><img style="width:${v.largura}px;display:block;border:1px solid #ccc" src="${dado(app)}"></figure>
</div></body>`);
  await pagina.screenshot({ path: saida, fullPage: true });
  await contexto.close();
}
