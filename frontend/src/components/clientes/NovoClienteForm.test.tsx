// Novo cliente (T-209, CLI-01): fotos escolhidas antes do primeiro "Salvar cliente".
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { filiais } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {} }) }));

import { NovoClienteForm } from "./NovoClienteForm";

describe("novo cliente", () => {
  it("as quatro fotos já aceitam arquivo antes do cadastro existir", () => {
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <NovoClienteForm />
      </QueryClientProvider>,
    );
    expect(html).not.toContain("Salve o cadastro para enviar");
    expect(html.match(/Toque para enviar/g)).toHaveLength(4);
    for (const rotulo of ["CNH · frente", "CNH · verso", "Selfie com documento", "Comprovante de residência"]) expect(html).toContain(rotulo);
  });

  it("T-514: Cancelar, Salvar cliente e Salvar e iniciar locação ficam na barra flutuante, sem repetir no painel", () => {
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <NovoClienteForm />
      </QueryClientProvider>,
    );
    expect(html).toContain("sticky bottom-[88px]");
    for (const t of ["Cancelar", "Salvar cliente", "Salvar e iniciar locação"]) expect(html.match(new RegExp(`>${t}<`, "g")), t).toHaveLength(1);
    expect(html.indexOf("Salvar cliente")).toBeGreaterThan(html.indexOf("sticky bottom-[88px]"));
  });

  it("CEP: a busca devolve rua, bairro, cidade e UF; desconhecido cai no preenchimento à mão", async () => {
    expect(await filiais.cep("60840280")).toMatchObject({ logradouro: "Av. Frei Cirilo", bairro: "Messejana", cidade: "Fortaleza", uf: "CE" });
    await expect(filiais.cep("11111111")).rejects.toMatchObject({ codigo: "cep_nao_encontrado" });
  });
});
