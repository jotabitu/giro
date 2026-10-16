// Cópia do link do convite (USR-01, T-252): a gravação começa no clique, antes da resposta da API.
import { afterEach, describe, expect, it, vi } from "vitest";
import { copiarQuandoChegar } from "./area-de-transferencia";

class ItemFalso {
  constructor(readonly conteudo: { "text/plain": Promise<Blob> }) {}
}

function adiado<T>() {
  let resolver!: (v: T) => void;
  let rejeitar!: (e: unknown) => void;
  const promessa = new Promise<T>((r, j) => {
    resolver = r;
    rejeitar = j;
  });
  return { promessa, resolver, rejeitar };
}

afterEach(() => vi.unstubAllGlobals());

describe("copiarQuandoChegar", () => {
  it("com ClipboardItem, grava na hora do clique, antes de o texto chegar (Safari)", async () => {
    const gravados: ItemFalso[] = [];
    const write = vi.fn(async (itens: ItemFalso[]) => {
      gravados.push(...itens);
      await Promise.all(itens.map((i) => i.conteudo["text/plain"]));
    });
    vi.stubGlobal("navigator", { clipboard: { write, writeText: vi.fn() } });
    vi.stubGlobal("ClipboardItem", ItemFalso);
    const link = adiado<string>();

    const copia = copiarQuandoChegar(link.promessa);
    expect(write).toHaveBeenCalledTimes(1); // síncrono: ainda dentro do toque

    link.resolver("https://motorapida.giro.example/convite#tok");
    await copia;
    expect(gravados).toHaveLength(1);
    const blob = await gravados[0]!.conteudo["text/plain"];
    expect(await blob.text()).toBe("https://motorapida.giro.example/convite#tok");
  });

  it("sem ClipboardItem, espera o texto e usa writeText", async () => {
    const writeText = vi.fn(async () => {});
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    vi.stubGlobal("ClipboardItem", undefined);
    await copiarQuandoChegar(Promise.resolve("link"));
    expect(writeText).toHaveBeenCalledWith("link");
  });

  it("sem área de transferência (página fora de HTTPS), rejeita sem expor o texto", async () => {
    vi.stubGlobal("navigator", {});
    await expect(copiarQuandoChegar(Promise.resolve("segredo"))).rejects.toThrow("Sem área de transferência.");
  });

  it("se a API falhar, a cópia também falha e nada é gravado", async () => {
    const writeText = vi.fn(async () => {});
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    vi.stubGlobal("ClipboardItem", undefined);
    const link = adiado<string>();
    const copia = copiarQuandoChegar(link.promessa);
    link.rejeitar(new Error("429"));
    await expect(copia).rejects.toThrow("429");
    expect(writeText).not.toHaveBeenCalled();
  });
});
