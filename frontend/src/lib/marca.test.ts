import { describe, expect, it } from "vitest";
import type { MarcaEmpresa } from "@/lib/api";
import { cssDaMarcaDaApi, MARCA_NEUTRA, marcaDaTela } from "./marca";

const MOTO_RAPIDA: MarcaEmpresa = {
  nome_exibicao: "Moto Rápida",
  iniciais: "MR",
  logo: { url: "/api/marca/logo/?v=5c1e9a2b", largura: 120, altura: 36 },
  cor: "#C8F04A",
  cor_sobre: "#111114",
  cor_suave: "#EEF9CC",
  cor_suave_escuro: "#2B3510",
  personalizada: true,
  versao: "5c1e9a2b",
};

describe("marca da locadora (docs/api/empresas.md)", () => {
  it("aplica as cores que a API mandou, sem recalcular", () => {
    const css = cssDaMarcaDaApi(MOTO_RAPIDA) ?? "";
    expect(css).toContain("--brand: #C8F04A; --on-brand: #111114; --brand-soft: #EEF9CC;");
    expect(css).toContain('[data-theme="dark"] { --brand: #C8F04A; --on-brand: #111114; --brand-soft: #2B3510; }');
  });

  it("usa a cor suave do tema escuro só no tema escuro", () => {
    const claro = (cssDaMarcaDaApi(MOTO_RAPIDA) ?? "").split('[data-theme="dark"]')[0] ?? "";
    expect(claro).not.toContain("#2B3510");
  });

  it("cor fora do formato descarta o conjunto e não injeta CSS", () => {
    expect(cssDaMarcaDaApi({ ...MOTO_RAPIDA, cor: "red; } body { display: none" })).toBeNull();
    expect(cssDaMarcaDaApi({ ...MOTO_RAPIDA, cor_suave: "#EEF9C" })).toBeNull();
  });

  it("nome, iniciais e logo vêm da API", () => {
    expect(marcaDaTela(MOTO_RAPIDA)).toEqual({ nome: "Moto Rápida", iniciais: "MR", logo: MOTO_RAPIDA.logo });
  });

  it("sem marca (host sem empresa ou ainda carregando) vale o texto neutro, sem logo", () => {
    expect(marcaDaTela(null)).toBe(MARCA_NEUTRA);
    expect(MARCA_NEUTRA.nome).toBe("Sua locadora");
    expect(MARCA_NEUTRA.logo).toBeNull();
  });
});
