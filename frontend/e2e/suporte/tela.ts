// Apoio comum aos testes: sessões, vigia de erros do navegador, arquivos de foto e a hora de agora em São Paulo.
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { expect, type Browser, type BrowserContext, type Locator, type Page, type TestInfo } from "@playwright/test";

/** Senha de desenvolvimento do seed (backend/seed/moto_rapida.py, `SENHA_DEV`). Não é segredo: só vale no compose local. */
export const SENHA = process.env.E2E_SENHA ?? "giro-dev-2026";
export const EMAIL = {
  bruna: "bruna@motorapida.com.br",
  joao: "joao@motorapida.com.br",
  rodrigo: "rodrigo@motorapida.com.br",
} as const;
export type Quem = keyof typeof EMAIL;

// PNG de 1 x 1 pixel. A API só confere tipo e tamanho do arquivo; o conteúdo da foto não importa para o fluxo.
const PNG_1X1 = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", "base64");

let pastaDasFotos: string | undefined;
/** Caminho de uma foto de teste (criada uma vez por execução, na pasta temporária do sistema). */
export function fotoDeTeste(): string {
  if (!pastaDasFotos) {
    pastaDasFotos = mkdtempSync(path.join(tmpdir(), "giro-e2e-"));
    writeFileSync(path.join(pastaDasFotos, "foto.png"), PNG_1X1);
  }
  return path.join(pastaDasFotos, "foto.png");
}

/** "HH:MM" de agora em São Paulo. O relógio do backend só fixa o dia; a hora anda com a real (ADR 0021). */
export function horaDeAgora(): string {
  const partes = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date());
  const valor = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? "00";
  return `${valor("hour")}:${valor("minute")}`;
}

/**
 * O fluxo atravessa 07 e 14 out com a hora real. À meia-noite o dia simulado volta para 00:00 e a devolução
 * cairia antes do fim previsto, então o teste não começa perto dela, nem com menos de uma hora de folga
 * (tolerância de 1 hora da LOC-10).
 */
export function exigirHoraSegura() {
  const [h, m] = horaDeAgora().split(":").map(Number) as [number, number];
  if (h * 60 + m > 22 * 60 + 30) {
    throw new Error(`São ${horaDeAgora()}: rode o E2E antes das 22:30. O relógio simulado volta a 00:00 à meia-noite e a devolução cairia antes do fim previsto.`);
  }
}

export type Vigia = {
  erros: string[];
  respostas5xx: string[];
  respostas4xx: string[];
  /** Declara que a próxima resposta com esse status e esse caminho é esperada (passo que provoca o erro de propósito). */
  esperar: (status: number, caminho: RegExp) => void;
  verificar: () => void;
};

/**
 * Junta erros do console e respostas de erro de uma página. `verificar()` falha se sobrou erro de console, resposta 5xx
 * ou resposta 4xx que nenhum passo declarou com `esperar`. A linha "Failed to load resource" do console só repete o status
 * da resposta, então quem decide é a resposta.
 */
export function vigiar(page: Page): Vigia {
  const esperadas: { status: number; caminho: RegExp }[] = [];
  const vigia: Vigia = {
    erros: [],
    respostas5xx: [],
    respostas4xx: [],
    esperar(status, caminho) {
      esperadas.push({ status, caminho });
    },
    verificar() {
      expect.soft(vigia.respostas5xx, "respostas 5xx durante o fluxo").toEqual([]);
      expect.soft(vigia.respostas4xx, "respostas 4xx que nenhum passo esperava").toEqual([]);
      expect.soft(vigia.erros, "erros no console do navegador").toEqual([]);
    },
  };
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const texto = m.text();
    if (texto.startsWith("Failed to load resource")) return;
    vigia.erros.push(texto);
  });
  page.on("pageerror", (e) => vigia.erros.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    const status = r.status();
    const descricao = `${status} ${r.request().method()} ${new URL(r.url()).pathname}`;
    if (status >= 500) vigia.respostas5xx.push(descricao);
    else if (status >= 400) {
      const i = esperadas.findIndex((e) => e.status === status && e.caminho.test(new URL(r.url()).pathname));
      if (i >= 0) esperadas.splice(i, 1);
      else vigia.respostas4xx.push(descricao);
    }
  });
  return vigia;
}

export type Sessao = { contexto: BrowserContext; page: Page; vigia: Vigia };

/** Um navegador isolado (cookies próprios) com as mesmas opções do projeto: desktop 1440 ou celular 390. */
export async function novaSessao(browser: Browser, info: TestInfo): Promise<Sessao> {
  const { viewport, isMobile, hasTouch, deviceScaleFactor, userAgent, baseURL, locale, timezoneId } = info.project.use;
  const contexto = await browser.newContext({ viewport, isMobile, hasTouch, deviceScaleFactor, userAgent, baseURL, locale, timezoneId });
  const page = await contexto.newPage();
  return { contexto, page, vigia: vigiar(page) };
}

/** Login por e-mail e senha. Devolve com a tela de início aberta. */
export async function entrar(page: Page, quem: Quem) {
  await page.goto("/entrar");
  await page.locator("input[name=email]").fill(EMAIL[quem]);
  await page.locator("input[name=senha]").fill(SENHA);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/inicio/);
}

/** Nenhuma tela do fluxo rola para o lado (CA-025-10). */
export async function semRolagemLateral(page: Page, onde: string) {
  const { largura, janela } = await page.evaluate(() => ({ largura: document.documentElement.scrollWidth, janela: window.innerWidth }));
  expect.soft(largura, `${onde}: rolagem lateral (conteúdo ${largura} px numa janela de ${janela} px)`).toBeLessThanOrEqual(janela);
}

/** O primeiro elemento visível: várias telas repetem um bloco (um para o desktop, outro para o celular) e um deles fica escondido. */
export const visivel = (l: Locator): Locator => l.filter({ visible: true }).first();

/** Aguarda a rede ficar quieta: as telas buscam dados depois de montar. */
export async function aquietar(page: Page) {
  await page.waitForLoadState("networkidle");
}
