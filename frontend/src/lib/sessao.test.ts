import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { Eu } from "@/lib/api";

const api = vi.hoisted(() => ({ eu: vi.fn(), renovar: vi.fn() }));
vi.mock("@/lib/api", async (original) => ({ ...(await original<typeof import("@/lib/api")>()), contas: { eu: api.eu, renovar: api.renovar } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace() {} }) }));

import { registrarConsulta } from "./sessao";

describe("sessão: consulta do usuário (T-137)", () => {
  it("a leitura de ['eu'] depois do login tem queryFn, sem 'No queryFn was passed'", async () => {
    const usuario = { id: 1 } as unknown as Eu;
    api.eu.mockResolvedValue({ id: 2 });
    api.renovar.mockResolvedValue({ access: "novo" });
    const cliente = new QueryClient();
    registrarConsulta(cliente);
    cliente.setQueryData(["eu"], usuario);
    await cliente.refetchQueries({ queryKey: ["eu"] });
    expect(cliente.getQueryState(["eu"])?.error).toBeNull();
    expect(cliente.getQueryData(["eu"])).toEqual({ id: 2 });
  });
});
