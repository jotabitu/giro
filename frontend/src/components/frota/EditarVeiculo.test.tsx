// T-243 · Editar veículo (VEI-01): o formulário abre com os dados da API, placa, chassi, km e filial só para leitura, e grava com PATCH.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, veiculos } from "@/lib/api";
import { definirAccess } from "@/lib/api/http";
import { veiculosApi } from "@/lib/api/veiculos";
import { paraCorpoEdicao, textoDeCentavos, valoresDoVeiculo } from "@/lib/veiculos";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/501/editar", useSearchParams: () => new URLSearchParams() }));

import { EditarVeiculo } from "./EditarVeiculo";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
}

const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function pagina(id: number): Promise<string> {
  const ficha = await veiculos.obter(id);
  const cliente = new QueryClient();
  cliente.setQueryData(["veiculo", id], ficha);
  cliente.setQueryData(["categorias", { filial: String(ficha.filial.id), tipo: ficha.tipo_veiculo }], await veiculos.categorias({ filial: ficha.filial.id, tipo_veiculo: ficha.tipo_veiculo }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cliente}>
      <EditarVeiculo id={id} />
    </QueryClientProvider>,
  );
}

describe("editar veículo, gerente", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("abre preenchido com os dados da API e com placa, chassi, km e filial só para leitura", async () => {
    const html = await pagina(501);
    const t = texto(html);
    expect(t).toContain("Editar veículo");
    // Os campos livres são não controlados (sem `value` na marcação do servidor): os valores iniciais aparecem no cartão ao lado e em `valoresDoVeiculo`.
    ordem(t, ["Honda CG 160 Fan", "QXA-4B21 · 2023 · 18.950 km", "Street 150–160", "Filial Centro"]);
    for (const rotulo of ["Placa", "Chassi", "Km atual", "Filial"]) {
      const campo = html.match(new RegExp(`<label[^>]*>${rotulo}</label>.*?<input[^>]*>`, "s"))?.[0] ?? "";
      expect(campo, rotulo).toContain("readOnly");
      expect(campo, rotulo).not.toContain("name=");
    }
    expect(t).toContain("QXA-4B21");
    expect(t).toContain("A filial só muda por transferência");
    expect(t).toContain("Salvar alterações");
    expect(t).toContain("Cancelar");
  });

  it("perfil sem acoes.editar recebe o aviso, sem formulário", async () => {
    await entrarComo("bruna@motorapida.com.br");
    const html = await pagina(501);
    expect(texto(html)).toContain("Seu perfil não edita veículos.");
    expect(html).not.toContain("<form");
    await entrarComo("rodrigo@motorapida.com.br");
  });
});

describe("PATCH /api/veiculos/{id}/ no falso (VEI-01)", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("grava os campos e devolve a ficha; placa, chassi, km e filial não mudam", async () => {
    const antes = await veiculos.obter(504);
    const depois = await veiculos.atualizar(504, { cor: "preta", renavam: "01289934499", valor_compra_centavos: 1250000, data_compra: "2025-01-10", capacidade_tanque_litros: "14.5" });
    expect(depois.cor).toBe("preta");
    expect(depois.renavam).toBe("01289934499");
    expect(depois.valor_compra_centavos).toBe(1250000);
    expect(depois.capacidade_tanque_litros).toBe("14.5");
    expect([depois.placa, depois.chassi, depois.km_atual, depois.filial.id]).toEqual([antes.placa, antes.chassi, antes.km_atual, antes.filial.id]);
  });

  it("erro da API volta no campo: categoria de outro tipo e renavam curto", async () => {
    const categorias = await veiculos.categorias({});
    const carro = categorias.find((c) => c.tipo_veiculo === "carro");
    await expect(veiculos.atualizar(504, { categoria_id: carro?.id ?? 999, renavam: "12" })).rejects.toMatchObject({
      status: 400,
      campos: { renavam: expect.any(String), categoria_id: expect.any(String) },
    });
  });

  it("vendedor recebe 403", async () => {
    await entrarComo("bruna@motorapida.com.br");
    await expect(veiculos.atualizar(504, { cor: "azul" })).rejects.toMatchObject({ status: 403 });
    await entrarComo("rodrigo@motorapida.com.br");
  });
});

describe("corpo do PATCH", () => {
  it("ficha → campos → corpo: só o que a API aceita, e opcional apagado vai como null", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const ficha = await veiculos.obter(501);
    const valores = valoresDoVeiculo(ficha);
    expect(valores.valor_compra).toBe("13.900,00");
    const corpo = paraCorpoEdicao({ ...valores, renavam: "", data_compra: "", valor_compra: "", capacidade_tanque_litros: "" });
    expect(corpo).toMatchObject({ renavam: null, data_compra: null, valor_compra_centavos: null, capacidade_tanque_litros: null, marca: "Honda", categoria_id: ficha.categoria.id });
    for (const fora of ["placa", "chassi", "km_atual", "filial_id", "status"]) expect(fora in corpo, fora).toBe(false);
  });

  it("textoDeCentavos", () => {
    expect(textoDeCentavos(1349000)).toBe("13.490,00");
    expect(textoDeCentavos(5)).toBe("0,05");
  });
});

describe("cliente HTTP real: PATCH /api/veiculos/{id}/", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: 501 }), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    definirAccess("abc");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    definirAccess(null);
  });

  it("manda PATCH na rota da ficha com o corpo", async () => {
    await veiculosApi.atualizar(501, { cor: "preta" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/veiculos/501/");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toEqual({ cor: "preta" });
  });
});
