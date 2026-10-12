import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu } from "@/lib/api";
import { InicioGeral } from "./InicioGeral";
import { InicioGerente } from "./InicioGerente";
import { InicioImplantacao } from "./InicioImplantacao";
import { InicioVendedor } from "./InicioVendedor";
import { InicioVistoriador } from "./InicioVistoriador";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

// Campo de bloco ou lista `null` (módulo sem fonte ainda) não pode derrubar a página.
const vazio = (variante: string) => ({ variante, saudacao: "Bom dia, Teste", atualizado_em: "2026-10-07T12:00:00Z" });
const tudoNulo = (variante: string, campos: string[]) => ({ ...vazio(variante), ...Object.fromEntries(campos.map((c) => [c, null])) }) as never;

describe("início: blocos null renderizam sem quebrar", () => {
  sessao.eu = { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { locacoes_criar: true } };
  it("geral", () => {
    const d = tudoNulo("geral", ["atencao", "kpis", "frota", "devolucoes_semana", "pendencias", "caixa_hoje"]);
    expect(() => renderToStaticMarkup(<InicioGeral d={d} periodo="7d" aoMudarPeriodo={() => {}} />)).not.toThrow();
  });
  it("gerente", () => {
    const d = tudoNulo("gerente", ["aprovacoes", "kpis", "equipe_hoje", "frota_filial"]);
    expect(() => renderToStaticMarkup(<InicioGerente d={d} />)).not.toThrow();
  });
  it("vendedor", () => {
    const d = tudoNulo("vendedor", ["kpis", "parcelas_atrasadas", "precisam_acao", "meta", "funil", "comissao_prevista", "propostas"]);
    expect(() => renderToStaticMarkup(<InicioVendedor d={d} />)).not.toThrow();
  });
  it("vistoriador", () => {
    const d = tudoNulo("vistoriador", ["agenda"]);
    expect(() => renderToStaticMarkup(<InicioVistoriador d={d} />)).not.toThrow();
  });
  it("implantacao", () => {
    const d = tudoNulo("implantacao", ["teste", "primeiros_passos", "convites", "indicadores"]);
    expect(() => renderToStaticMarkup(<InicioImplantacao d={d} />)).not.toThrow();
  });
});
