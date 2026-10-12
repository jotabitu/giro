// Detalhe do cliente (T-108) contra docs/telas/html/Cliente-Detalhe-Desktop.dc.html e Cliente-Detalhe-Mobile.dc.html.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { clientes, contas, type Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { DetalheDoCliente } from "./DetalheDoCliente";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
  sessao.eu = await contas.eu();
}

async function pagina(id: number): Promise<{ desktop: string; celular: string }> {
  const [c, locacoes] = await Promise.all([clientes.obter(id), clientes.locacoes(id)]);
  const cache = new QueryClient();
  cache.setQueryData(["cliente", id], c);
  cache.setQueryData(["cliente", id, "locacoes"], locacoes);
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDoCliente id={id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = html.match(/^<div class="hidden md:block">(.*)<\/div><div class="md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop, celular };
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

describe("detalhe do cliente, gerente: Juliana Rocha", () => {
  let desktop = "";
  let celular = "";
  beforeAll(async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    ({ desktop, celular } = await pagina(1201));
  });

  it("desktop e celular são duas árvores; hidden e md:hidden ficam em div comum, nunca em elemento wl-", () => {
    expect(desktop).not.toBe("");
    expect(celular).not.toBe("");
    for (const m of (desktop + celular).matchAll(/class="([^"]*)"/g)) {
      const classes = m[1] ?? "";
      if (/\bwl-/.test(classes)) expect(classes, "wl- com hidden").not.toMatch(/(^|\s)(md:)?hidden(\s|$)/);
    }
  });

  it("desktop: seções e rótulos na ordem da referência", () => {
    const t = texto(desktop);
    ordem(t, ["Clientes", "Juliana Rocha", "Em dia", "Cadastro completo", "Pessoa física · cliente desde mar 2026", "WhatsApp", "Editar", "Iniciar locação"]);
    ordem(t, ["Total pago", "R$ 2.674", "em 3 locações", "Em aberto", "R$ 0", "nenhuma parcela vencida", "Caução em garantia", "R$ 300", "LOC-2836", "Atrasos", "0", "em pagamentos e devoluções"]);
    ordem(t, ["Locação atual", "Devolução em 14 out às 18:00", "Yamaha Factor 150", "PNB-7C04", "LOC-2836 · Semanal R$ 329,00 · 30 set → 14 out 18:00 · 2 de 2 semanas pagas", "Ver locação", "Receber devolução"]);
    ordem(t, ["Locações", "3 no total · nenhuma com atraso", "Contrato", "Veículo", "Situação", "Pago", "LOC-2760", "Mensal · 01 ago → 31 ago", "R$ 890,00", "LOC-2701", "Honda CG 160 Fan · QXA-4B21"]);
    ordem(t, ["Documentos", "4 de 4 enviados", "CNH · frente", "CNH · verso", "Selfie com documento", "Comprovante de residência"]);
    expect(t).not.toContain("Histórico");
    ordem(t, ["Dados pessoais", "Mostrar", "CPF", "***.218.330-**", "Nascimento", "02/07/1994 · 32 anos", "Celular", "(85) 98114-2290", "E-mail", "Profissão", "Entregadora", "Endereço", "Rua Monsenhor Bruno, 1120", "Aldeota · Fortaleza, CE", "Referência", "Sandra Rocha · mãe", "(85) 98822-4410"]);
    ordem(t, ["Pode alugar", "CPF válido", "CNH categoria A", "Fora da lista de bloqueio", "Carteira de motorista", "Número", "0381•••••62", "Categoria", "Validade", "18/11/2030", "Dados do cliente (LGPD)", "Só o administrador exporta ou anonimiza."]);
    expect(t).not.toContain("Exportar dados do cliente");
  });

  it("LOC-2836 segue a regra: ativa, devolução em 14 out, sem Devolve hoje (LOC-01, LOC-05)", () => {
    for (const h of [desktop, celular]) {
      expect(h).not.toMatch(/devolve hoje/i);
      expect(h).toContain("Devolução em 14 out");
    }
    expect(texto(desktop)).toContain("|Ativa|");
  });

  it("desktop: Editar, Receber devolução e Exportar ficam desativados (sem tela ou endpoint); Iniciar locação é link", () => {
    for (const nome of ["Editar", "Receber devolução"]) expect(desktop).toMatch(new RegExp(`<button[^>]*disabled[^>]*>(<svg.*?</svg>)?${nome}</button>`));
    expect(desktop).toContain('href="/locacoes/nova?cliente=1201"');
    expect(desktop).toContain('href="https://wa.me/5585981142290"');
  });

  it("celular: cabeçalho, cartão, KPIs, locação atual, dados, locações, documentos e botão, nessa ordem", () => {
    ordem(celular, ['aria-label="Voltar"', 'aria-label="Editar"', "Juliana Rocha", "Em dia", "WhatsApp", "Total pago", "Em aberto", "Locação atual", "Dados pessoais", "Locações", "Documentos", "Iniciar locação"]);
    const t = texto(celular);
    ordem(t, ["(85) 98114-2290 · cliente desde mar 2026", "R$ 2.674", "3 locações", "R$ 0", "sem atrasos"]);
    ordem(t, ["Devolução em 14 out 18:00", "Yamaha Factor 150", "PNB-7C04", "LOC-2836", "R$ 329,00/sem", "2 de 2 semanas pagas · caução R$ 300,00"]);
    ordem(t, ["CPF", "***.218.330-**", "Nascimento", "02/07/1994", "E-mail", "Endereço", "Rua Monsenhor Bruno, 1120 · Aldeota", "CNH", "A · até 18/11/2030"]);
    ordem(t, ["LOC-2836", "Semanal · 30 set → 14 out 18:00", "R$ 658,00", "LOC-2760", "R$ 890,00", "LOC-2701", "R$ 526,00"]);
    ordem(t, ["CNH", "frente e verso", "Selfie", "Comprovante", "Termo LGPD"]);
    expect(t).not.toContain("Histórico");
    expect(t).not.toContain("Pode alugar");
    expect(celular).not.toContain("<table");
  });

  it("celular: alvos de toque de 44px no voltar e no editar", () => {
    expect(celular.match(/width:44px;height:44px/g)).toHaveLength(2);
  });
});

describe("detalhe do cliente: outros estados", () => {
  it("administrador vê Exportar dados do cliente, desativado (fase 2, AUD-06)", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    sessao.eu = { ...(sessao.eu as Eu), perfil: "administrador" }; // o administrador entra com 2FA; aqui só importa o perfil
    const { desktop } = await pagina(1201);
    expect(desktop).toMatch(/<button[^>]*disabled[^>]*>(<svg.*?<\/svg>)?Exportar dados do cliente<\/button>/);
  });

  it("cliente incompleto lista o que falta e deixa enviar o documento", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop } = await pagina(1206);
    expect(desktop).toContain("Faltam selfie com documento e comprovante de residência para liberar a locação.");
    expect(desktop).toContain("2 de 4 enviados");
    expect(desktop).toContain("Toque para enviar");
    expect(desktop).toContain("Não informado");
  });

  it("cliente bloqueado mostra o motivo e não oferece Iniciar locação", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop } = await pagina(1203);
    expect(desktop).toContain("Bloqueado");
    expect(desktop).toContain("Conta com 15 dias de atraso");
    expect(desktop).not.toContain("Iniciar locação");
    expect(texto(desktop)).toContain("parcelas vencidas");
  });

  it("sem locação atual mostra o estado vazio", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = await pagina(1208);
    expect(desktop).toContain("Nenhuma locação em andamento. A última foi a LOC-2702, encerrada em 29 set.");
    expect(desktop).toContain("Nada por aqui ainda.");
    expect(celular).not.toContain("Locação atual");
  });

  it("perfil sem permissão de cadastro vê só o resumo", async () => {
    await entrarComo("joao@motorapida.com.br");
    const cache = new QueryClient();
    cache.setQueryData(["cliente", 1201], await clientes.obter(1201));
    const h = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <DetalheDoCliente id={1201} />
      </QueryClientProvider>,
    );
    expect(h).toContain("Seu perfil vê só o resumo do cliente.");
    expect(h).not.toContain("Dados pessoais");
    expect(h).not.toContain("Documentos");
  });
});
