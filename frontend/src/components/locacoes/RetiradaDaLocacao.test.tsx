// T-451 e T-452 · "Para retirar", "Registrar retirada", "Pendências da retirada" e "Registrar pagamento" na ficha da locação
// (LOC-17, FIN-18; docs/api/locacoes.md, docs/qa/criterios/T-451-T-452.md). A tela só mostra os textos e as ações que a API manda.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, locacoes, type LocacaoCompleta, type ParaRetirar } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/locacoes", useSearchParams: () => new URLSearchParams() }));

import { DetalheDaLocacao } from "./DetalheDaLocacao";
import { ConfirmarRetirada } from "./RetiradaDaLocacao";

// O falso limita 10 entradas por minuto por e-mail: entra de novo só ao trocar de perfil.
let quem: string | null = null;
async function entrarComo(email: string) {
  if (quem === email) return;
  quem = email;
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

function render(l: LocacaoCompleta): { desktop: string; celular: string } {
  const cache = new QueryClient();
  cache.setQueryData(["locacao", l.id], l);
  cache.setQueryData(["locacao", l.id, "historico"], { resultados: [] });
  const html = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <DetalheDaLocacao id={l.id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = html.match(/^<div class="hidden flex-col gap-6 md:flex">(.*)<\/div><div class="flex flex-col gap-4 md:hidden">(.*)<\/div>$/s) ?? [];
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
/** O botão com este texto, ou undefined. */
const botao = (h: string, rotulo: string) => [...h.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].find((m) => texto(m[1] ?? "").replace(/\|/g, "") === rotulo)?.[0];

// O exemplo de docs/api/locacoes.md: tudo faltando, com o botão desligado por falta da vistoria.
const TUDO_FALTANDO: ParaRetirar = {
  passos: [
    { codigo: "vistoria_saida", feito: false, texto: "Falta a vistoria de saída", acoes: [{ codigo: "continuar_vistoria", rotulo: "Fazer vistoria de saída" }] },
    { codigo: "contrato", feito: false, texto: "Falta enviar o contrato", acoes: [{ codigo: "gerar_contrato", rotulo: "Enviar contrato" }] },
    { codigo: "pagamento", feito: false, texto: "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00", acoes: [] },
  ],
  prazo: "Retire até 10 out. Sem retirada, a locação é cancelada em 11 out.",
  registrar_retirada: {
    rotulo: "Registrar retirada",
    disponivel: false,
    aviso: "Faça a vistoria de saída antes da retirada.",
    titulo: "Registrar retirada?",
    faltas: ["Falta enviar o contrato", "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00"],
    motivo_obrigatorio: "Informe o motivo.",
  },
};

async function lucas(): Promise<LocacaoCompleta> {
  return locacoes.obter(2856);
}

describe("LOC-17 · Para retirar (CA-451-01, CA-451-02)", () => {
  it("test_loc_17_para_retirar_mostra_os_tres_passos_o_prazo_e_as_acoes_da_api", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const l = { ...(await lucas()), para_retirar: TUDO_FALTANDO };
    const { desktop, celular } = render(l);
    for (const h of [desktop, celular]) {
      const t = texto(h);
      ordem(t, ["Para retirar", "Retire até 10 out. Sem retirada, a locação é cancelada em 11 out.", "Falta a vistoria de saída", "Fazer vistoria de saída", "Falta enviar o contrato", "Enviar contrato", "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00"]);
      expect(h).toContain(`href="/locacoes/2856/vistoria"`);
    }
  });

  it("test_loc_17_passo_feito_mostra_o_texto_da_api_sem_acao", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const passos = TUDO_FALTANDO.passos.map((p) => (p.codigo === "vistoria_saida" ? { ...p, feito: true, texto: "Feita em 07 out, 09:20", acoes: [] } : p));
    const l = { ...(await lucas()), para_retirar: { ...TUDO_FALTANDO, passos } };
    const t = texto(render(l).desktop);
    ordem(t, ["Para retirar", "Feita em 07 out, 09:20", "(feito)", "Falta enviar o contrato"]);
    const secao = t.slice(t.indexOf("Para retirar"), t.indexOf("Pagamentos"));
    expect(secao).not.toContain("Fazer vistoria de saída");
  });

  it("test_loc_17_contrato_enviado_tem_reenviar_e_copiar_link", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const t = texto(render(await lucas()).desktop);
    // O falso imita a API: a LOC-2856 tem o contrato enviado e a caução em aberto.
    ordem(t, ["Para retirar", "Falta a assinatura do cliente", "Reenviar", "Copiar link para assinar", "Falta receber R$ 300,00: caução R$ 300,00"]);
  });

  it("test_loc_17_sem_para_retirar_a_secao_nao_aparece", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = render(await locacoes.obter(2836));
    expect(texto(desktop + celular)).not.toContain("Para retirar");
  });
});

describe("LOC-17 · Registrar retirada (CA-451-04, CA-451-09, CA-451-10)", () => {
  it("test_loc_17_registrar_retirada_desligado_com_o_aviso_sem_vistoria", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = render({ ...(await lucas()), para_retirar: TUDO_FALTANDO });
    for (const h of [desktop, celular]) {
      const b = botao(h, "Registrar retirada");
      expect(b).toBeDefined();
      expect(b).toMatch(/disabled=""/);
      expect(texto(h)).toContain("Faça a vistoria de saída antes da retirada.");
    }
  });

  it("test_loc_17_registrar_retirada_ligado_com_a_vistoria_feita", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const r = { ...TUDO_FALTANDO.registrar_retirada!, disponivel: true, aviso: null };
    const { desktop } = render({ ...(await lucas()), para_retirar: { ...TUDO_FALTANDO, registrar_retirada: r } });
    const b = botao(desktop, "Registrar retirada");
    expect(b).toBeDefined();
    expect(b).not.toMatch(/disabled=""/);
    expect(texto(desktop)).not.toContain("Faça a vistoria de saída antes da retirada.");
  });

  it("test_loc_17_sem_registrar_retirada_quem_nao_pode_nao_ve_o_botao", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const l = await lucas();
    expect(l.para_retirar?.registrar_retirada).toBeNull();
    const { desktop, celular } = render(l);
    expect(texto(desktop)).toContain("Para retirar");
    expect(botao(desktop + celular, "Registrar retirada")).toBeUndefined();
  });

  it("test_loc_17_confirmacao_mostra_as_faltas_e_o_campo_motivo", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const l = await lucas();
    const cache = new QueryClient();
    const t = texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <ConfirmarRetirada l={l} r={TUDO_FALTANDO.registrar_retirada!} aoFechar={() => {}} aoConcluir={() => {}} />
        </QueryClientProvider>,
      ),
    );
    ordem(t, ["Registrar retirada?", "Falta enviar o contrato", "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00", "Motivo", "Voltar", "Registrar retirada"]);
  });

  it("test_loc_17_falso_registrar_retirada_exige_motivo_e_vistoria", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    await expect(locacoes.registrarRetirada(2856, { motivo: "  " })).rejects.toMatchObject({ status: 400 });
    await expect(locacoes.registrarRetirada(2856, { motivo: "Cliente paga amanhã, combinado com a gerência" })).rejects.toMatchObject({ status: 409, codigo: "vistoria_saida_pendente" });
  });
});

describe("LOC-17 · Pendências da retirada (CA-451-13)", () => {
  it("test_loc_17_pendencias_da_retirada_so_com_o_que_falta", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const ativa = await locacoes.obter(2836);
    const l: LocacaoCompleta = {
      ...ativa,
      pendencias_retirada: {
        passos: [
          { codigo: "contrato", feito: false, texto: "Falta a assinatura do cliente", acoes: [{ codigo: "reenviar_contrato", rotulo: "Reenviar" }, { codigo: "copiar_link_contrato", rotulo: "Copiar link para assinar" }] },
          { codigo: "pagamento", feito: false, texto: "Falta receber R$ 300,00: caução R$ 300,00", acoes: [] },
        ],
      },
    };
    const { desktop, celular } = render(l);
    for (const h of [desktop, celular]) {
      const t = texto(h);
      ordem(t, ["Pendências da retirada", "Falta a assinatura do cliente", "Reenviar", "Copiar link para assinar", "Falta receber R$ 300,00: caução R$ 300,00"]);
      expect(t).not.toContain("Para retirar");
    }
    expect(texto(render({ ...l, pendencias_retirada: null }).desktop)).not.toContain("Pendências da retirada");
  });
});

describe("FIN-18 · Registrar pagamento em cada conta (CA-452-01, CA-452-03)", () => {
  it("test_fin_18_registrar_pagamento_so_nas_contas_com_acoes_receber", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const l = await lucas();
    // Na LOC-2856, a 1ª parcela está paga e a caução, aberta: só a caução tem "Registrar pagamento".
    expect(l.parcelas?.map((p) => [p.rotulo, p.acoes.receber])).toEqual([
      ["Parcela 1", false],
      ["Caução", true],
    ]);
    const { desktop, celular } = render(l);
    for (const h of [desktop, celular]) {
      const botoes = [...h.matchAll(/aria-label="Registrar pagamento: ([^"]+)"/g)].map((m) => m[1]);
      expect(botoes).toEqual(["Caução"]);
    }
  });

  it("test_fin_18_sem_conta_a_receber_nao_ha_coluna_nem_botao", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const { desktop, celular } = render(await locacoes.obter(2836));
    expect(desktop + celular).not.toContain("Registrar pagamento");
    // A referência do celular não tem a tabela de pagamentos: sem nada a receber, ela continua fora.
    expect(texto(celular)).not.toContain("|Vencimento|");
  });
});
