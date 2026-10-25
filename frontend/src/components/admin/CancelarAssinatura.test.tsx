// T-198 · Cancelar assinatura e pausa (docs/api/cancelamento.md, CA-ASS-30, 31, 35 a 38, 43 a 45, 54 a 56, 69).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { assinatura, contas, type Eu } from "@/lib/api";
import { assinaturaApi } from "@/lib/api/assinatura";
import { definirAccess } from "@/lib/api/http";
import { definirAssinaturaFalsa, definirCancelamentoFalso } from "@/testes/falsos/falso-assinatura";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

import { DialogoReconfirmar2fa } from "@/components/acesso/DialogoReconfirmar2fa";
import { CancelarAssinatura } from "./CancelarAssinatura";
import { DialogoPausarAssinatura } from "./DialogoPausarAssinatura";

const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};
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
  cache.setQueryData(["assinatura", "cancelamento"], await assinatura.telaCancelamento());
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <CancelarAssinatura />
    </QueryClientProvider>,
  );
}

beforeEach(() => definirAssinaturaFalsa(null));
afterEach(() => definirAssinaturaFalsa(null));

describe("Admin-Cancelar (CA-ASS-30, 31, 35, 37, 38, 69)", () => {
  it("em teste: mostra motivos, oferta do Essencial sem pausa, O que acontece e confirmação desabilitada (CA-ASS-30, 37, 38)", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await pagina();
    const t = texto(html);
    ordem(t, [
      "Administração",
      "Cancelar assinatura",
      "Plano Profissional · em teste até 21 out",
      "Voltar",
      "Por que você quer cancelar?",
      "Ajuda a gente a melhorar. Não muda nada no cancelamento.",
      "Preço alto para o meu tamanho",
      "Faltou alguma função",
      "Vou usar outro sistema",
      "Vou fechar ou pausar a locadora",
      "Outro motivo",
      "Antes de ir, que tal…",
      "Mudar para o Essencial",
      "Até 30 veículos, 1 filial e 3 usuários.",
      "Ver plano",
      "O que acontece",
      "Acesso",
      "continua até 21 out",
      "Cobranças futuras",
      "nenhuma",
      "Seus dados",
      "guardados por 90 dias",
      "Depois de 90 dias",
      "apagados de vez",
      "Contratos dos seus clientes",
      "continuam válidos",
      "Para confirmar, digite o nome da empresa",
      "Exportar dados antes",
      "Cancelar assinatura",
      "Exportar baixa a auditoria em CSV. O resto dos seus dados você pede à equipe Giro.",
    ]);
    expect(t).not.toContain("Pausar por até 3 meses");
    expect(html).toContain('placeholder="Moto Rápida"');
    expect(html).toContain('href="/admin/exportar"');
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Cancelar assinatura<\/button>/);
  });

  it("na ativa sem pausa no histórico: oferece pausar por até 3 meses e mostra continua até 21 nov (CA-ASS-35, 37, 69)", async () => {
    await entrar("mariana@motorapida.com.br");
    const seed = await assinatura.obter();
    definirAssinaturaFalsa({
      status: "ativa",
      teste: null,
      proxima_fatura: { vencimento: "2026-11-22", valor_centavos: 44900, descricao: "Plano Profissional" },
      acoes: { ...(seed.acoes as NonNullable<typeof seed.acoes>), pausar: true },
    });
    const t = texto(await pagina());
    expect(t).toContain("Plano Profissional · mensal");
    expect(t).toContain("Pausar por até 3 meses");
    expect(t).toContain("A pausa começa em 22 nov, no fim do período pago.");
    expect(t).toContain("Acesso|continua até 21 nov");
  });

  it("inadimplente, suspensa ou pausada: não oferece pausar e acesso termina agora (CA-ASS-37, 69)", async () => {
    await entrar("mariana@motorapida.com.br");
    for (const status of ["inadimplente", "suspensa", "pausada"] as const) {
      definirAssinaturaFalsa({ status, teste: null });
      const t = texto(await pagina());
      expect(t, status).not.toContain("Pausar por até 3 meses");
      expect(t, status).toContain("Acesso|termina agora");
    }
  });

  it("diálogo de pausa oferece 1 mês, 2 meses e 3 meses (CA-ASS-54)", () => {
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <DialogoPausarAssinatura aberto inicio="2026-11-22" aoFechar={() => {}} aoConcluir={() => {}} />
      </QueryClientProvider>,
    );
    const t = texto(html);
    for (const trecho of ["Pausar assinatura", "Começa em 22 nov.", "1 mês", "2 meses", "3 meses", "Confirmar pausa"]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("só o administrador acessa Admin-Cancelar", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await pagina())).toContain("Só o administrador acessa a Assinatura.");
  });
});

describe("Contrato de cancelamento e pausa (CA-ASS-31, 35, 36, 43 a 45, 54 a 56)", () => {
  it("nome_confirmacao errado ou sem acento: 422 nome_nao_confere (CA-ASS-31)", async () => {
    await expect(assinatura.cancelar({ motivo: "preco_alto", nome_confirmacao: "Moto Rapida" })).rejects.toMatchObject({
      status: 422,
      codigo: "nome_nao_confere",
    });
  });

  it("cancelar em inadimplente encerra na hora e bloqueia a área da empresa com 403 empresa_cancelada (CA-ASS-34, 35)", async () => {
    definirAssinaturaFalsa({ status: "inadimplente", teste: null });
    const r = await assinatura.cancelar({ motivo: "fechar_ou_pausar", nome_confirmacao: "  moto   rápida " });
    expect(r.status).toBe("cancelada");
    expect(r.acoes?.cancelar).toBe(false);
    await expect(assinatura.obter()).rejects.toMatchObject({
      status: 403,
      codigo: "empresa_cancelada",
      message: "Esta assinatura foi cancelada. Para pedir seus dados ou voltar, fale com a equipe Giro.",
    });
  });

  it("cancelar na ativa agenda para o fim do ciclo e permite desfazer (CA-ASS-35, 43, 44)", async () => {
    const seed = await assinatura.obter();
    definirAssinaturaFalsa({ status: "ativa", teste: null, acoes: { ...(seed.acoes as NonNullable<typeof seed.acoes>), pausar: true } });
    const agendado = await assinatura.cancelar({ motivo: "preco_alto", nome_confirmacao: "Moto Rápida" });
    expect(agendado.status).toBe("ativa");
    expect(agendado.cancelamento).toMatchObject({ acesso_ate: "2026-11-21", motivo: "preco_alto", rotulo: "Assinatura cancelada. Você tem acesso até 21 nov." });
    expect(agendado.acoes).toMatchObject({ cancelar: false, desfazer_cancelamento: true, pausar: false });
    await expect(assinatura.telaCancelamento()).rejects.toMatchObject({ status: 409, codigo: "transicao_empresa" });

    const desfeito = await assinatura.desfazerCancelamento();
    expect(desfeito.cancelamento).toBeNull();
    expect(desfeito.acoes).toMatchObject({ cancelar: true, desfazer_cancelamento: false, pausar: true });
    await expect(assinatura.desfazerCancelamento()).rejects.toMatchObject({ status: 409, codigo: "transicao_empresa" });
  });

  it("pausar na ativa agenda para o fim do período pago e permite desistir (CA-ASS-54, 55)", async () => {
    const seed = await assinatura.obter();
    definirAssinaturaFalsa({ status: "ativa", teste: null, acoes: { ...(seed.acoes as NonNullable<typeof seed.acoes>), pausar: true } });
    const agendada = await assinatura.pausar({ meses: 2 });
    expect(agendada.pausa).toMatchObject({
      situacao: "agendada",
      meses: 2,
      inicio: "2026-11-22",
      ate: "2027-01-21",
      volta_em: "2027-01-22",
      rotulo: "Pausa marcada de 22 nov a 21 jan. Até lá, tudo continua.",
    });
    expect(agendada.acoes).toMatchObject({ pausar: false, desistir_pausa: true });
    await expect(assinatura.pausar({ meses: 1 })).rejects.toMatchObject({ status: 409, codigo: "transicao_empresa" });

    const desfeita = await assinatura.encerrarPausa();
    expect(desfeita.pausa).toBeNull();
    expect(desfeita.acoes?.pausar).toBe(true);
  });

  it("voltar da pausa reativa a assinatura (CA-ASS-36, 55)", async () => {
    const seed = await assinatura.obter();
    definirAssinaturaFalsa({
      status: "pausada",
      teste: null,
      somente_leitura: true,
      pausa: { situacao: "em_andamento", meses: 1, inicio: "2026-10-10", ate: "2026-11-09", volta_em: "2026-11-10", rotulo: "Assinatura pausada até 09 nov." },
      acoes: { ...(seed.acoes as NonNullable<typeof seed.acoes>), voltar_pausa: true, pausar: false },
    });
    const reativada = await assinatura.encerrarPausa();
    expect(reativada.status).toBe("ativa");
    expect(reativada.somente_leitura).toBe(false);
    expect(reativada.pausa).toBeNull();
    expect(reativada.acoes).toMatchObject({ voltar_pausa: false });
  });

  it("definirCancelamentoFalso sobrescreve a tela quando necessário", async () => {
    definirCancelamentoFalso({ plano_resumo: "Plano Completo · anual até 30 dez 2027" });
    expect((await assinatura.telaCancelamento()).plano_resumo).toBe("Plano Completo · anual até 30 dez 2027");
  });
});

describe("cliente HTTP real de cancelamento e pausa", () => {
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
    await assinaturaApi.telaCancelamento();
    await assinaturaApi.cancelar({ motivo: "preco_alto", nome_confirmacao: "Moto Rápida" });
    await assinaturaApi.desfazerCancelamento();
    await assinaturaApi.pausar({ meses: 2 });
    await assinaturaApi.encerrarPausa();
    expect(chamada(0)).toMatchObject({ url: "/api/assinatura/cancelamento/", metodo: "GET" });
    expect(chamada(1)).toMatchObject({ url: "/api/assinatura/cancelamento/", metodo: "POST", corpo: { motivo: "preco_alto", nome_confirmacao: "Moto Rápida" } });
    expect(chamada(2)).toMatchObject({ url: "/api/assinatura/cancelamento/", metodo: "DELETE" });
    expect(chamada(3)).toMatchObject({ url: "/api/assinatura/pausa/", metodo: "POST", corpo: { meses: 2 } });
    expect(chamada(4)).toMatchObject({ url: "/api/assinatura/pausa/", metodo: "DELETE" });
  });
});

describe("Diálogo das 2 etapas recentes (T-348, USR-02, PLT-06)", () => {
  it("usr_02_dialogo: mostra a mensagem do 403, o campo de 6 dígitos e o link do código de recuperação", () => {
    const html = renderToStaticMarkup(
      <DialogoReconfirmar2fa mensagem="Confirme o código do autenticador para cancelar a assinatura." aoConfirmar={async () => null} aoCancelar={() => {}} />,
    );
    const t = texto(html);
    ordem(t, [
      "Código de verificação",
      "Confirme o código do autenticador para cancelar a assinatura.",
      "Digite os 6 números que aparecem no aplicativo autenticador.",
      "Código do aplicativo",
      "Usar um código de recuperação",
      "Cancelar",
      "Confirmar",
    ]);
    expect(html.match(/inputmode="numeric"/gi)).toHaveLength(6);
    expect(html).toMatch(/<button[^>]*disabled[^>]*>Confirmar<\/button>/);
  });
});
