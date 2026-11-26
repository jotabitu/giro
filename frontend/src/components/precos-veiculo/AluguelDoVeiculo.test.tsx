// T-507: voltar para a ficha, o bloco de aluguel recolhível e o "Oferecer aluguel" do veículo (VEI-21, VEI-12).
// O ligado e desligado e o texto da Nova locação vêm da API (`aluguel_ligado`, `aviso_aluguel`); a tela só mostra.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { PrecosDoVeiculo as Precos, Veiculo } from "@/lib/api";
import { PRECOS_POP } from "@/testes/falsos/falso-precos-veiculo";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/900/precos", useSearchParams: () => new URLSearchParams() }));

import { AluguelDesativado } from "@/components/frota/AluguelDesativado";
import { AVISO_ALUGUEL_DESATIVADO } from "./PlanosDeAluguel";
import { PrecosDoVeiculo, TEXTOS_DO_ALUGUEL } from "./PrecosDoVeiculo";
import { AVISO_ALUGUEL_NA_FICHA, PrecosNaFicha } from "./PrecosNaFicha";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

function render(d: Precos, el: React.ReactElement): string {
  const cache = new QueryClient();
  cache.setQueryData(["veiculo-precos", 900], d);
  return renderToStaticMarkup(<QueryClientProvider client={cache}>{el}</QueryClientProvider>);
}

const desligado: Precos = { ...PRECOS_POP, aluguel_ligado: false, aviso_aluguel: "O aluguel desta moto está desativado. O administrador ativa em Planos e preços." };

describe("Planos e preços (T-507)", () => {
  it("t507_voltar_para_a_ficha_no_topo", () => {
    const h = render(PRECOS_POP, <PrecosDoVeiculo id={900} />);
    // No celular, o ícone; no desktop, o botão "Voltar". Os dois levam à ficha do veículo.
    const voltar = h.match(/<a[^>]*aria-label="Voltar para o veículo"[^>]*>/g) ?? [];
    expect(voltar).toHaveLength(2);
    for (const a of voltar) expect(a).toContain('href="/veiculos/900"');
    expect(texto(h)).toContain("|Voltar|");
  });

  it("t507_bloco_de_aluguel_aberto_por_padrao_com_a_seta", () => {
    const h = render(PRECOS_POP, <PrecosDoVeiculo id={900} />);
    expect(h).toMatch(/aria-label="Recolher os planos de aluguel" aria-expanded="true" aria-controls="planos-de-aluguel"/);
    expect(h).not.toMatch(/id="planos-de-aluguel" hidden/);
    expect(h).toContain('aria-label="Oferecer aluguel"');
    expect(texto(h)).not.toContain(AVISO_ALUGUEL_DESATIVADO);
  });

  it("vei_21_aluguel_desligado_recolhe_e_avisa", () => {
    const h = render(desligado, <PrecosDoVeiculo id={900} />);
    expect(texto(h)).toContain(AVISO_ALUGUEL_DESATIVADO);
    expect(h).toMatch(/aria-label="Abrir os planos de aluguel" aria-expanded="false"/);
    expect(h).toMatch(/id="planos-de-aluguel" hidden/);
    // Os planos ficam guardados e editáveis: continuam na página, só recolhidos.
    expect(h).toContain('value="R$ 269,00"');
    expect(h).toMatch(/aria-label="Oferecer aluguel"[^>]*aria-checked="false"|aria-checked="false"[^>]*aria-label="Oferecer aluguel"/);
  });

  it("vei_21_textos_dos_dialogos_do_produto", () => {
    expect(TEXTOS_DO_ALUGUEL.desligar).toEqual({
      titulo: "Desativar o aluguel desta moto?",
      texto: "Os planos de aluguel ficam guardados como estão e voltam quando você ativar o aluguel de novo. A moto deixa de aparecer para aluguel na Nova locação. As locações já confirmadas continuam com o preço delas.",
      confirmar: "Desativar aluguel",
      cancelar: "Continuar com aluguel",
    });
    expect(TEXTOS_DO_ALUGUEL.ligar).toEqual({
      titulo: "Ativar o aluguel desta moto?",
      texto: "Os planos de aluguel voltam como estavam, e os ligados passam a aparecer na Nova locação.",
      confirmar: "Ativar aluguel",
      cancelar: "Continuar desativado",
    });
  });

  it("vei_21_so_o_administrador_liga_e_desliga", () => {
    const h = render({ ...PRECOS_POP, pode_editar: false }, <PrecosDoVeiculo id={900} />);
    expect(h).toMatch(/<button[^>]*aria-label="Oferecer aluguel"[^>]*disabled|<button[^>]*disabled[^>]*aria-label="Oferecer aluguel"/);
  });
});

describe("ficha e Frota com o aluguel desligado (VEI-21)", () => {
  it("vei_21_ficha_sem_os_planos_de_aluguel_com_a_compra", () => {
    const t = texto(render(desligado, <PrecosNaFicha id={900} />));
    expect(t).toContain(AVISO_ALUGUEL_NA_FICHA);
    expect(AVISO_ALUGUEL_NA_FICHA).toBe("Aluguel desativado. Os planos ficam guardados em Planos e preços.");
    for (const plano of ["Diária", "Semanal", "Mensal", "Entregador"]) expect(t).not.toContain(`|${plano}|`);
    expect(t).toContain("Locação com compra");
    const ligado = texto(render(PRECOS_POP, <PrecosNaFicha id={900} />));
    expect(ligado).not.toContain(AVISO_ALUGUEL_NA_FICHA);
    expect(ligado).toContain("Semanal");
  });

  it("vei_21_selo_neutro_ao_lado_do_status", () => {
    const selo = (v: Pick<Veiculo, "aluguel_ligado">) => renderToStaticMarkup(<AluguelDesativado v={v} />);
    expect(texto(selo({ aluguel_ligado: false }))).toContain("Aluguel desativado");
    expect(selo({ aluguel_ligado: true })).toBe("");
    expect(selo({})).toBe("");
  });
});
