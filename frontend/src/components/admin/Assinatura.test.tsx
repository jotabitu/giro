// Administração › Assinatura (T-170, T-187, T-198) contra docs/telas/html/Admin-Assinatura-*.dc.html, só com o que o contrato entrega (PLT-01, PLT-03, PLT-06, PLT-07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { assinatura, contas, type Eu } from "@/lib/api";
import { avisoDeUso, nomeConfere, percentualDeUso, precoDoPlano, situacaoDaAssinatura } from "@/lib/assinatura";
import { definirAssinaturaFalsa } from "@/testes/falsos/falso-assinatura";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { AssinaturaDaEmpresa } from "./AssinaturaDaEmpresa";

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
  cache.setQueryData(["assinatura"], await assinatura.obter());
  cache.setQueryData(["assinatura", "faturas"], await assinatura.faturas());
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <AssinaturaDaEmpresa />
    </QueryClientProvider>,
  );
}

afterEach(() => definirAssinaturaFalsa(null));

describe("assinatura (Admin-Assinatura)", () => {
  it("plano em teste: nome, selo, preço e dias que faltam", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    for (const trecho of ["Administração", "Assinatura", "Seu plano", "Teste grátis até 21 out", "Profissional", "R$ 449,00 por mês, a partir de 22 out", "Faltam 14 dias de teste grátis."]) {
      expect(t, trecho).toContain(trecho);
    }
  });

  it("uso do plano: 86 de 150 veículos, 1 de 3 filiais, 5 de 10 usuários, sem aviso", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await pagina();
    const t = texto(html);
    expect(t).toContain("Uso do plano");
    expect(t).toContain("86|de 150 veículos");
    expect(t).toContain("1|de 3 filiais");
    expect(t).toContain("5|de 10 usuários");
    expect(t).toContain("Veículos|86 de 150");
    expect(t).toContain("Avisamos quando chegar a 90% de qualquer limite.");
    expect(t).not.toContain("Perto do limite");
    expect(html).toContain('aria-valuenow="57"');
    expect(html).toContain('aria-valuenow="33"');
    expect(html).toContain('aria-valuenow="50"');
  });

  it("T-187/T-198: blocos na ordem da referência, cada um pelo que a API manda", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await pagina();
    const t = texto(html);
    ordem(t, ["Seu plano", "Mudar de plano", "Escolher forma de pagamento", "Uso do plano", "Forma de pagamento", "Nenhuma cadastrada. Escolha até 21 out para não perder o acesso.", "Cartão de crédito", "Cobrança automática todo mês", "Pix automático", "Autoriza uma vez no app do banco", "Boleto", "Enviado por e-mail 5 dias antes", "Faturas", "Vencimento", "Descrição", "Valor", "Situação", "22 out", "Plano Profissional · 22 out a 21 nov", "R$ 449,00", "Sem forma de pagamento", "07 out", "Teste grátis de 14 dias", "R$ 0,00", "Ativo", "Dados da nota fiscal", "Editar", "Moto Rápida Locações Ltda", "CNPJ 12.345.678/0001-95", "financeiro@motorapida.com.br", "Av. Bezerra de Menezes, 1200"]);
    ordem(t, ["Precisa de mais veículos ou filiais?", "O plano Completo inclui:", "Veículos, filiais e usuários sem limite", "Implantação acompanhada por chamada", "Suporte prioritário", "Comparar planos", "Cancelar assinatura", "Exportar dados antes"]);
    expect(t).toContain("R$ 449,00 por mês, a partir de 22 out");
    expect(t).not.toMatch(/NF-e|domínio|portal|integraç/i);
    expect(html).toContain('href="/admin/assinatura/cancelar"');
    expect(t).toContain("Exportar baixa a auditoria em CSV. O resto dos seus dados você pede à equipe Giro.");
  });

  it("T-187: sem acoes da API, não há botão de mudar, escolher forma, editar, pagar, pausar nem cancelar", async () => {
    await entrar("mariana@motorapida.com.br");
    const seed = await assinatura.obter();
    definirAssinaturaFalsa({
      acoes: {
        mudar_plano: false,
        desfazer_mudanca_plano: false,
        escolher_forma_pagamento: false,
        editar_dados_fiscais: false,
        cancelar: false,
        desfazer_cancelamento: false,
        pausar: false,
        voltar_pausa: false,
        desistir_pausa: false,
      },
      oferta: null,
    });
    const t = texto(await pagina());
    for (const fora of ["Mudar de plano", "Escolher forma de pagamento", "Editar", "Comparar planos", "Pagar", "Cancelar assinatura", "Pausar assinatura"]) expect(t, fora).not.toContain(fora);
    expect(t).toContain("Forma de pagamento");
    expect(seed.acoes?.mudar_plano).toBe(true);
  });

  it("T-187: downgrade agendado mostra para qual plano muda e o Desfazer, só com acoes.desfazer_mudanca_plano", async () => {
    await entrar("mariana@motorapida.com.br");
    const seed = await assinatura.obter();
    definirAssinaturaFalsa({
      status: "ativa",
      teste: null,
      plano_proximo: { id: 1, nome: "Essencial", ciclo: "mensal", vale_em: "2026-11-22" },
      proxima_fatura: { vencimento: "2026-11-22", valor_centavos: 19900, descricao: "Plano Essencial · 22 nov a 21 dez" },
      acoes: { ...(seed.acoes as NonNullable<typeof seed.acoes>), desfazer_mudanca_plano: true },
    });
    const t = texto(await pagina());
    expect(t).toContain("Muda para Essencial em 22 nov, a R$ 199,00.");
    expect(t).toContain("Desfazer mudança");
    definirAssinaturaFalsa({ plano_proximo: { id: 1, nome: "Essencial", ciclo: "mensal", vale_em: "2026-11-22" } });
    expect(texto(await pagina())).not.toContain("Desfazer mudança");
  });

  it("T-198: cancelamento agendado, pausa agendada e empresa pausada mostram os rótulos e ações da API (CA-ASS-35, 36, 43, 55)", async () => {
    await entrar("mariana@motorapida.com.br");
    const seed = await assinatura.obter();
    definirAssinaturaFalsa({
      status: "ativa",
      teste: null,
      cancelamento: { pedido_em: "2026-10-10T13:00:00Z", acesso_ate: "2026-11-21", motivo: "preco_alto", rotulo: "Assinatura cancelada. Você tem acesso até 21 nov." },
      acoes: { ...(seed.acoes as NonNullable<typeof seed.acoes>), cancelar: false, desfazer_cancelamento: true, pausar: false },
    });
    const tCanc = texto(await pagina());
    expect(tCanc).toContain("Assinatura cancelada. Você tem acesso até 21 nov. Depois disso, a empresa fica sem acesso e nada mais é cobrado.");
    expect(tCanc).toContain("Desfazer cancelamento");
    expect(tCanc).not.toContain("Cancelar assinatura");

    definirAssinaturaFalsa({
      status: "pausada",
      teste: null,
      somente_leitura: true,
      pausa: { situacao: "em_andamento", meses: 2, inicio: "2026-10-10", ate: "2026-12-09", volta_em: "2026-12-10", rotulo: "Assinatura pausada até 09 dez. Volta sozinha em 10 dez." },
      acoes: { ...(seed.acoes as NonNullable<typeof seed.acoes>), voltar_pausa: true, pausar: false },
    });
    const tPausa = texto(await pagina());
    expect(tPausa).toContain("Assinatura pausada até 09 dez. Volta sozinha em 10 dez.");
    expect(tPausa).toContain("Voltar da pausa");
    expect(tPausa).toContain("Sua empresa está só para consulta no momento.");
  });

  it("limite perto e no limite aparecem por escrito (PLT-03)", async () => {
    await entrar("mariana@motorapida.com.br");
    definirAssinaturaFalsa({
      uso: {
        veiculos: { usado: 140, limite: 150, aviso: true, bloqueado: false },
        filiais: { usado: 3, limite: 3, aviso: true, bloqueado: true },
        usuarios: { usado: 5, limite: 10, aviso: false, bloqueado: false },
      },
    });
    const t = texto(await pagina());
    expect(t).toContain("Perto do limite.");
    expect(t).toContain("No limite: não dá para cadastrar mais. O que já existe continua funcionando.");
  });

  it("empresa inadimplente mostra a faixa da API e somente leitura avisa", async () => {
    await entrar("mariana@motorapida.com.br");
    definirAssinaturaFalsa({ status: "inadimplente", teste: null, proxima_fatura: null, faixa_aviso: "Sua fatura está atrasada.", somente_leitura: true });
    const t = texto(await pagina());
    expect(t).toContain("Sua fatura está atrasada.");
    expect(t).toContain("Fatura em atraso");
    expect(t).toContain("Sua empresa está só para consulta no momento.");
    expect(t).toContain("R$ 449,00 por mês");
    expect(t).not.toContain("a partir de");
  });

  it("só o administrador acessa", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await pagina())).toContain("Só o administrador acessa a Assinatura.");
  });
});

describe("apoio da tela", () => {
  it("situação, preço e confirmação do nome (CA-ASS-31)", () => {
    const plano = { id: 2, nome: "Profissional", preco_contratado_centavos: 44900, ciclo: "mensal" };
    const prox = { vencimento: "2026-10-22", valor_centavos: 44900, descricao: "Plano Profissional" };
    expect(situacaoDaAssinatura({ status: "ativa", teste: null })).toEqual({ rotulo: "Ativa", tom: "sucesso" });
    expect(situacaoDaAssinatura({ status: "suspensa", teste: null }).tom).toBe("critico");
    expect(situacaoDaAssinatura({ status: "algo_novo", teste: null }).rotulo).toBe("algo_novo");
    expect(precoDoPlano({ plano, proxima_fatura: null })).toBe("R$ 449,00 por mês");
    expect(precoDoPlano({ plano, proxima_fatura: prox })).toBe("R$ 449,00 por mês, a partir de 22 out");
    expect(precoDoPlano({ plano: { ...plano, ciclo: "anual" }, proxima_fatura: null })).toBe("R$ 449,00 por ano");
    expect(nomeConfere("  moto   rápida ", "Moto Rápida")).toBe(true);
    expect(nomeConfere("Moto Rapida", "Moto Rápida")).toBe(false);
    expect(nomeConfere("", "Moto Rápida")).toBe(false);
  });

  it("barra: proporção do limite, vazia sem limite, nunca passa de 100", () => {
    expect(percentualDeUso({ usado: 86, limite: 150 })).toBeCloseTo(57.33, 1);
    expect(percentualDeUso({ usado: 5, limite: null })).toBe(0);
    expect(percentualDeUso({ usado: 12, limite: 10 })).toBe(100);
    expect(avisoDeUso({ aviso: false, bloqueado: false })).toBeNull();
  });
});
