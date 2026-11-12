// T-243 · Editar veículo (VEI-01): o formulário abre com os dados da API, placa, chassi, km e filial só para leitura, e grava com PATCH.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, veiculos, type Eu } from "@/lib/api";
import { definirAccess } from "@/lib/api/http";
import { veiculosApi } from "@/lib/api/veiculos";
import { categoriaAoTrocarTipo, esquemaVeiculo, paraCorpoEdicao, semCategoriaDoTipo, textoDeCentavos, valoresDoVeiculo } from "@/lib/veiculos";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/501/editar", useSearchParams: () => new URLSearchParams() }));

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { EditarVeiculo } from "./EditarVeiculo";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
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

  it("test_vei_11_tipo_antes_da_categoria_e_livre_fora_da_locacao (CA-438-04)", async () => {
    const html = await pagina(504);
    const campo = html.match(/<label[^>]*>Tipo de veículo<\/label>.*?<\/select>/s)?.[0] ?? "";
    expect(campo).not.toContain("disabled");
    expect(campo).toMatch(/<option value="moto" selected="">Moto<\/option>/);
    expect(html.indexOf(">Tipo de veículo</label>")).toBeLessThan(html.indexOf(">Categoria de preço</label>"));
  });

  it("test_vei_11_tipo_travado_com_locacao_aberta (CA-438-08)", async () => {
    const html = await pagina(501);
    const campo = html.match(/<label[^>]*>Tipo de veículo<\/label>.*?<\/span>/s)?.[0] ?? "";
    expect(campo).toContain("disabled");
    expect(campo).toContain("Este veículo está na LOC-2841. Troque o tipo depois da devolução.");
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

  it("erro da API volta no campo: renavam curto", async () => {
    await expect(veiculos.atualizar(504, { renavam: "12" })).rejects.toMatchObject({ status: 400, campos: { renavam: expect.any(String) } });
  });

  it("test_vei_11_tipo_vem_da_categoria_e_recusa_com_locacao_aberta (CA-438-04, 07, 08)", async () => {
    const categorias = await veiculos.categorias({});
    const carro = categorias.find((c) => c.tipo_veiculo === "carro")!;
    // QXA-4B21 alugado na LOC-2841: 409 com a frase, e continua moto.
    await expect(veiculos.atualizar(501, { categoria_id: carro.id })).rejects.toMatchObject({ status: 409, codigo: "tipo_com_locacao_aberta", message: "Este veículo está na LOC-2841. Troque o tipo depois da devolução." });
    expect((await veiculos.obter(501)).tipo_veiculo).toBe("moto");
    // SAK-1D39 disponível: o tipo vem da categoria nova.
    const sak = await veiculos.atualizar(504, { categoria_id: carro.id });
    expect(sak.tipo_veiculo).toBe("carro");
    const moto = categorias.find((c) => c.tipo_veiculo === "moto")!;
    expect((await veiculos.atualizar(504, { categoria_id: moto.id })).tipo_veiculo).toBe("moto");
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

  it("test_vei_11_trocar_o_tipo_esvazia_a_categoria_e_voltar_devolve (CA-438-03, 05)", () => {
    const ida = categoriaAoTrocarTipo({}, "moto", "2", "carro");
    expect(ida.categoria).toBe("");
    const volta = categoriaAoTrocarTipo(ida.guardadas, "carro", "", "moto");
    expect(volta.categoria).toBe("2");
    // Escolhida uma categoria de carro, ela também volta quando a pessoa marca Carro de novo.
    const deNovo = categoriaAoTrocarTipo(volta.guardadas, "moto", "2", "carro");
    expect(categoriaAoTrocarTipo(deNovo.guardadas, "carro", "4", "moto").guardadas.carro).toBe("4");
    expect(categoriaAoTrocarTipo({}, "moto", "2", "moto").categoria).toBe("2");
  });

  it("test_vei_11_sem_categoria_do_tipo_e_categoria_obrigatoria (CA-438-06, 12)", () => {
    expect(semCategoriaDoTipo("carro")).toBe("Nenhuma categoria de carro nesta filial. Cadastre uma em Preços.");
    expect(semCategoriaDoTipo("moto")).toBe("Nenhuma categoria de moto nesta filial. Cadastre uma em Preços.");
    const vazio = esquemaVeiculo.shape.categoria_id.safeParse("");
    expect(vazio.success).toBe(false);
    expect(vazio.error?.issues[0]?.message).toBe("Escolha a categoria de preço.");
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

describe("editar veículo, campos da VEI-09 e leitura do CRLV-e (T-421)", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("test_vei_09_gerente_ve_combustivel_dados_do_documento_motor_observacoes_rastreador_e_anotacoes (CA-421-08, CA-421-09)", async () => {
    const t = texto(await pagina(501));
    for (const rotulo of ["Combustível", "Espécie", "Tipo", "Carroceria", "Potência (cv)", "Cilindrada (cc)", "Lotação (pessoas)", "Peso bruto total (kg)", "Número do motor", "Observações do CRLV-e", "Rastreador · número ou IMEI", "Rastreador · empresa", "Anotações"]) expect(t, rotulo).toContain(rotulo);
    const ficha = await veiculos.obter(501);
    const valores = valoresDoVeiculo(ficha);
    expect(valores).toMatchObject({ combustivel: "flex", potencia_cv: "15", cilindrada_cc: "162", especie: "passageiro", tipo_documento: "Motocicleta", lotacao: "2", peso_bruto_kg: "290", numero_motor: "KC22E1P004401", observacoes_crlv: "ALIENACAO FIDUCIARIA", rastreador_numero: "356938035643809", rastreador_empresa: "Rastreia Fácil", anotacoes: "Risco no tanque, lado esquerdo" });
  });

  it("test_vei_08_editar_oferece_preencher_pelo_documento_sem_placa_e_chassi (CA-421-10)", async () => {
    const t = texto(await pagina(502));
    expect(t).toContain("Preencher pelo documento");
    expect(t).toContain("Enviar CRLV-e");
    expect(t).toContain("Placa e chassi não mudam.");
  });

  it("test_vei_09_veiculo_antigo_abre_o_editar_com_campos_vazios (CA-421-14)", async () => {
    const valores = valoresDoVeiculo(await veiculos.obter(502));
    expect(valores).toMatchObject({ combustivel: "", potencia_cv: "", especie: "", numero_motor: "", rastreador_numero: "", anotacoes: "" });
  });

  it("test_vei_09_combustivel_muda_no_editar (CA-421-08)", async () => {
    expect((await veiculos.obter(509)).combustivel).toBeNull();
    const depois = await veiculos.atualizar(509, { combustivel: "gasolina", documento: { lotacao: 2, peso_bruto_kg: 1400 }, rastreador: { numero: "356938035643810", empresa: "Rastreia Fácil" }, anotacoes: "Retrovisor trocado" });
    expect(depois).toMatchObject({ combustivel: "gasolina", documento: { lotacao: 2, peso_bruto_kg: 1400 }, rastreador: { numero: "356938035643810" }, anotacoes: "Retrovisor trocado" });
    // Chave enviada substitui, ausente não muda, null apaga.
    const apos = await veiculos.atualizar(509, { documento: { lotacao: 1 }, anotacoes: null });
    expect(apos.documento).toMatchObject({ lotacao: 1, peso_bruto_kg: 1400 });
    expect(apos.anotacoes).toBeNull();
  });

  it("test_vei_09_formato_recusado_volta_na_chave_pontuada (CA-421-07)", async () => {
    await expect(veiculos.atualizar(509, { documento: { potencia_cv: 1500, lotacao: 0 }, anotacoes: "x".repeat(501) })).rejects.toMatchObject({
      status: 400,
      campos: { "documento.potencia_cv": "Informe a potência em cv, de 1 a 999.", "documento.lotacao": "Informe a lotação em pessoas, de 1 a 99.", anotacoes: "Use até 500 caracteres." },
    });
  });

  it("test_vei_08_leitura_no_editar_do_proprio_veiculo_nao_traz_placa_nem_chassi (CA-421-10)", async () => {
    const leitura = await veiculos.lerCrlvDoVeiculo(502, new File(["%PDF-"], "crlv-pnb7c04.pdf"));
    expect("placa" in leitura.campos).toBe(false);
    expect("chassi" in leitura.campos).toBe(false);
    expect(leitura.lidos).not.toContain("placa");
    expect(leitura.lidos).toContain("documento.potencia_cv");
    expect(leitura.quantidade).toBe(leitura.lidos.length);
    // Nada foi gravado: só o PATCH grava.
    expect((await veiculos.obter(502)).documento.potencia_cv).toBeNull();
  });

  it("test_vei_08_leitura_no_editar_de_outro_veiculo_recusa_com_a_mensagem_da_api (CA-421-10)", async () => {
    await expect(veiculos.lerCrlvDoVeiculo(502, new File(["%PDF-"], "crlv-tbc5h21.pdf"))).rejects.toMatchObject({ status: 422, codigo: "crlv_outro_veiculo", message: "Este CRLV-e é de outro veículo." });
  });

  it("test_vei_08_cadastro_le_16_campos_com_os_9_novos (CA-421-01)", async () => {
    const leitura = await veiculos.lerCrlv(new File(["%PDF-"], "crlv-tbc5h21.pdf"));
    expect(leitura.quantidade).toBe(16);
    expect(leitura.rotulo).toBe("CRLV-e lido · 16 campos preenchidos");
    expect(leitura.lidos).not.toContain("documento.carroceria");
    expect(leitura.lidos).not.toContain("documento.observacoes");
    expect(leitura.campos).toMatchObject({ "documento.potencia_cv": 8, "documento.cilindrada_cc": 109, "documento.lotacao": 2, "documento.peso_bruto_kg": 240, "documento.numero_motor": "JC75E1S123456" });
  });

  it("test_vei_09_quem_edita_vendedor_recebe_403 (CA-421-09)", async () => {
    await entrarComo("bruna@motorapida.com.br");
    await expect(veiculos.atualizar(509, { anotacoes: "x" })).rejects.toMatchObject({ status: 403 });
    await entrarComo("rodrigo@motorapida.com.br");
  });
});
