// T-420 · Início do gerente: as transferências no Detran pendentes (LOC-16, VEN-11) aparecem em `pendencias`, como no administrador.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu, InicioDe } from "@/lib/api";
import { InicioGerente } from "./InicioGerente";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

const base = { variante: "gerente", saudacao: "Bom dia, Rodrigo", atualizado_em: "2026-10-07T12:00:00Z", aprovacoes: { total: 0, mais_antigo: null, itens: [] }, kpis: [], equipe_hoje: [], frota_filial: { total: 0, segmentos: [] } };
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

describe("início do gerente: pendências", () => {
  sessao.eu = { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { locacoes_criar: true } };

  it("test_loc_16_transferencia_pendente_aparece_com_o_texto_da_api_e_leva_a_locacao", () => {
    const d = { ...base, pendencias: { titulo: "1 transferência no Detran pendente", itens: [{ texto: "Transferência no Detran · RTA-2C55 · Lucas Ferreira · LOC-2901 quitada em 10/10/2028", gravidade: "alerta", destino: { chave: "locacoes", id: 2901 } }] } } as unknown as InicioDe<"gerente">;
    const html = renderToStaticMarkup(<InicioGerente d={d} />);
    const t = texto(html);
    expect(t).toContain("1 transferência no Detran pendente");
    expect(t).toContain("Transferência no Detran · RTA-2C55 · Lucas Ferreira · LOC-2901 quitada em 10/10/2028");
    expect(t).toContain("Ver pendências");
    expect(html).toContain('href="/locacoes/2901"');
  });

  it("test_loc_16_sem_pendencia_nao_mostra_o_cartao", () => {
    const d = { ...base, pendencias: { titulo: "Nenhuma transferência no Detran pendente", itens: [] } } as unknown as InicioDe<"gerente">;
    const t = texto(renderToStaticMarkup(<InicioGerente d={d} />));
    expect(t).not.toContain("Nenhuma transferência no Detran pendente");
    expect(t).not.toContain("Ver pendências");
  });
});
