// Administração › Assinatura (T-170) contra docs/telas/html/Admin-Assinatura-*.dc.html, só com o que o contrato entrega (PLT-01, PLT-03).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { assinatura, contas, type Eu } from "@/lib/api";
import { avisoDeUso, percentualDeUso, precoDoPlano, situacaoDaAssinatura } from "@/lib/assinatura";
import { definirAssinaturaFalsa } from "@/testes/falsos/falso-assinatura";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { AssinaturaDaEmpresa } from "./AssinaturaDaEmpresa";

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
    for (const trecho of ["Administração", "Assinatura", "Seu plano", "Teste grátis até 21 out", "Profissional", "R$ 449,00 por mês, depois do teste", "Faltam 14 dias de teste grátis."]) {
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

  it("sem rota na API: nada de pagamento, faturas, nota fiscal nem trocar de plano; cancelar fica desabilitado com aviso", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await pagina();
    const t = texto(html);
    for (const fora of ["Mudar de plano", "Escolher forma de pagamento", "Forma de pagamento", "Faturas", "Dados da nota fiscal", "Comparar planos"]) expect(t, fora).not.toContain(fora);
    expect(t).toContain("Cancelar assinatura");
    expect(html).toMatch(/<button[^>]*disabled[^>]*>[^<]*Cancelar assinatura/);
    expect(t).toContain("O cancelamento por aqui chega em uma próxima versão.");
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
    definirAssinaturaFalsa({ status: "inadimplente", teste: null, faixa_aviso: "Sua fatura está atrasada.", somente_leitura: true });
    const t = texto(await pagina());
    expect(t).toContain("Sua fatura está atrasada.");
    expect(t).toContain("Fatura em atraso");
    expect(t).toContain("Sua empresa está só para consulta no momento.");
    expect(t).toContain("R$ 449,00 por mês");
    expect(t).not.toContain("depois do teste");
  });

  it("só o administrador acessa", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await pagina())).toContain("Só o administrador acessa a Assinatura.");
  });
});

describe("apoio da tela", () => {
  it("situação e preço", () => {
    const base = { plano: { id: 2, nome: "Profissional", preco_contratado_centavos: 44900, ciclo: "mensal" }, teste: null };
    expect(situacaoDaAssinatura({ status: "ativa", teste: null })).toEqual({ rotulo: "Ativa", tom: "sucesso" });
    expect(situacaoDaAssinatura({ status: "suspensa", teste: null }).tom).toBe("critico");
    expect(situacaoDaAssinatura({ status: "algo_novo", teste: null }).rotulo).toBe("algo_novo");
    expect(precoDoPlano({ ...base, status: "ativa" })).toBe("R$ 449,00 por mês");
    expect(precoDoPlano({ plano: { ...base.plano, ciclo: "anual" }, status: "ativa" })).toBe("R$ 449,00 por ano");
  });

  it("barra: proporção do limite, vazia sem limite, nunca passa de 100", () => {
    expect(percentualDeUso({ usado: 86, limite: 150 })).toBeCloseTo(57.33, 1);
    expect(percentualDeUso({ usado: 5, limite: null })).toBe(0);
    expect(percentualDeUso({ usado: 12, limite: 10 })).toBe(100);
    expect(avisoDeUso({ aviso: false, bloqueado: false })).toBeNull();
  });
});
