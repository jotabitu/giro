// T-508: o bloco "Locação com compra" ganha a mesma seta de recolher e abrir do aluguel (T-507), pela peça comum SetaDoBloco.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { isValidElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { PrecosDoVeiculo as Precos } from "@/lib/api";
import { PRECOS_POP } from "@/testes/falsos/falso-precos-veiculo";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/900/precos", useSearchParams: () => new URLSearchParams() }));

import { PrecosDoVeiculo } from "./PrecosDoVeiculo";
import { SetaDoBloco, estadoDoBloco } from "./SetaDoBloco";

function render(d: Precos): string {
  const cache = new QueryClient();
  cache.setQueryData(["veiculo-precos", 900], d);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <PrecosDoVeiculo id={900} />
    </QueryClientProvider>,
  );
}

const compra = PRECOS_POP.plano_compra as NonNullable<Precos["plano_compra"]>;
const compraDesligada: Precos = { ...PRECOS_POP, plano_compra: { ...compra, ligado: false } };

describe("Locação com compra recolhível (T-508)", () => {
  it("t508_compra_ligada_comeca_aberta_com_a_seta", () => {
    const h = render(PRECOS_POP);
    expect(h).toMatch(/aria-label="Recolher a locação com compra" aria-expanded="true" aria-controls="locacao-com-compra"/);
    expect(h).toContain('id="locacao-com-compra"');
    expect(h).not.toMatch(/id="locacao-com-compra" hidden/);
  });

  it("t508_compra_desligada_comeca_recolhida", () => {
    const h = render(compraDesligada);
    expect(h).toMatch(/aria-label="Abrir a locação com compra" aria-expanded="false" aria-controls="locacao-com-compra"/);
    expect(h).toMatch(/id="locacao-com-compra" hidden/);
    // O interruptor continua no cabeçalho, fora do que recolhe.
    expect(h).toContain('aria-label="Oferecer locação com compra"');
  });

  it("t508_aluguel_segue_igual_com_a_peca_comum", () => {
    const h = render(compraDesligada);
    expect(h).toMatch(/aria-label="Recolher os planos de aluguel" aria-expanded="true" aria-controls="planos-de-aluguel"/);
    expect(h).not.toMatch(/id="planos-de-aluguel" hidden/);
  });

  it("t508_seta_recolhe_e_abre", () => {
    // Começa aberto (ligado): o toque recolhe; recolhido, o toque abre de novo.
    let recolhido = false;
    let e = estadoDoBloco(recolhido, false);
    expect(e.aberto).toBe(true);
    recolhido = e.recolhidoDepoisDoToque;
    e = estadoDoBloco(recolhido, false);
    expect(e.aberto).toBe(false);
    recolhido = e.recolhidoDepoisDoToque;
    expect(estadoDoBloco(recolhido, false).aberto).toBe(true);
  });

  it("t508_erro_no_bloco_mantem_aberto", () => {
    expect(estadoDoBloco(true, true).aberto).toBe(true);
    // Com erro, o toque não esconde o campo errado.
    expect(estadoDoBloco(estadoDoBloco(false, true).recolhidoDepoisDoToque, true).aberto).toBe(true);
  });

  it("t508_seta_chama_o_alternar_e_troca_rotulo_e_icone", () => {
    const aoAlternar = vi.fn();
    const aberta = SetaDoBloco({ aberto: true, oQue: "a locação com compra", controla: "locacao-com-compra", aoAlternar });
    expect(isValidElement(aberta)).toBe(true);
    const props = aberta.props as { onClick: () => void; "aria-label": string; "aria-expanded": boolean };
    props.onClick();
    expect(aoAlternar).toHaveBeenCalledTimes(1);
    expect(props["aria-label"]).toBe("Recolher a locação com compra");
    expect(props["aria-expanded"]).toBe(true);
    const fechada = renderToStaticMarkup(<SetaDoBloco aberto={false} oQue="a locação com compra" controla="locacao-com-compra" aoAlternar={aoAlternar} />);
    expect(fechada).toMatch(/aria-label="Abrir a locação com compra" aria-expanded="false"/);
  });
});
