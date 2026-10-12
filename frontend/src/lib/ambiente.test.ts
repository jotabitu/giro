import { afterEach, describe, expect, it } from "vitest";
import { agoraDaTela, agoraNoDia, definirAmbiente, escopoDaRota } from "./ambiente";
import { diaDe } from "./formatos";
import { periodoDaLocacao } from "./locacoes";
import { horarioDaAgenda } from "./painel";

afterEach(() => definirAmbiente(null));

describe("ambiente (ADR 0021)", () => {
  it("agoraNoDia troca o dia e mantém a hora de Brasília", () => {
    const real = new Date("2026-10-12T15:30:45-03:00");
    const a = agoraNoDia("2026-10-07", real);
    expect(a.toISOString()).toBe("2026-10-07T18:30:45.000Z");
    expect(diaDe(a.toISOString())).toBe("2026-10-07");
  });

  it("sem resposta da API, o agora da tela é o relógio do navegador", () => {
    const real = new Date("2026-10-12T10:00:00-03:00");
    expect(agoraDaTela(real)).toBe(real);
  });

  it("com a data simulada, o 'hoje' das telas é o da API e não o do navegador", () => {
    definirAmbiente({ hoje: "2026-10-07", data_simulada: true });
    const real = new Date("2026-10-12T10:00:00-03:00");
    expect(diaDe(agoraDaTela(real).toISOString())).toBe("2026-10-07");
    const l = { inicio: "2026-10-07T09:00:00-03:00", fim_previsto: "2026-10-14T18:00:00-03:00", sinais: { devolve_hoje: false } } as Parameters<typeof periodoDaLocacao>[0];
    expect(periodoDaLocacao(l)).toBe("hoje → 14 out");
    expect(horarioDaAgenda("2026-10-07T09:30:00-03:00")).toBe("09:30");
  });

  it("rotas da plataforma leem o ambiente da plataforma", () => {
    expect(escopoDaRota("/plataforma")).toBe("plataforma");
    expect(escopoDaRota("/plataforma/empresas")).toBe("plataforma");
    expect(escopoDaRota("/plataformas")).toBe("empresa");
    expect(escopoDaRota("/entrar")).toBe("empresa");
  });
});
