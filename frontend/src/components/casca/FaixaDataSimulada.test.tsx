import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { FaixaDataSimulada } from "./FaixaDataSimulada";

describe("FaixaDataSimulada", () => {
  it("com data simulada, mostra o aviso com a data e sem botão de fechar", () => {
    const html = renderToStaticMarkup(<FaixaDataSimulada ambiente={{ hoje: "2026-10-07", data_simulada: true }} />);
    expect(html).toContain("Data simulada: 07/10/2026. Ambiente de desenvolvimento.");
    expect(html).not.toContain("<button");
  });

  it("sem data simulada, não mostra nada", () => {
    expect(renderToStaticMarkup(<FaixaDataSimulada ambiente={{ hoje: "2026-10-12", data_simulada: false }} />)).toBe("");
  });

  it("sem resposta da API (rota inexistente), segue sem faixa e sem erro", () => {
    expect(renderToStaticMarkup(<FaixaDataSimulada ambiente={null} />)).toBe("");
  });
});
