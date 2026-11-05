import { describe, expect, it } from "vitest";
import type { LeituraCrlv } from "@/lib/api";
import { centavosDoTexto, esquemaVeiculo, NOME_DO_CAMPO_DA_API, paraCorpoEdicao, paraCorpoVeiculo, valoresDaLeitura, VALORES_INICIAIS_VEICULO } from "./veiculos";

describe("centavosDoTexto", () => {
  it.each([
    ["13.490,00", 1349000],
    ["R$ 13.490,00", 1349000],
    ["44,9", 4490],
    ["300", 30000],
  ])("%s", (texto, centavos) => expect(centavosDoTexto(texto)).toBe(centavos));

  it("texto que não é valor volta null", () => expect(centavosDoTexto("abc")).toBeNull());
});

describe("paraCorpoVeiculo (VEI-01)", () => {
  const v = { ...VALORES_INICIAIS_VEICULO, placa: "tbc-5h21", marca: " Honda ", modelo: "Pop 110i ES", ano_fabricacao: "2026", ano_modelo: "2026", chassi: "9c2jc7500tr012345", cor: "Preta", km_atual: "0", filial_id: "1", categoria_id: "1" };

  it("manda placa e chassi limpos e em maiúsculas, números como número", () => {
    expect(paraCorpoVeiculo(v)).toEqual({ placa: "TBC5H21", chassi: "9C2JC7500TR012345", marca: "Honda", modelo: "Pop 110i ES", ano_fabricacao: 2026, ano_modelo: 2026, cor: "Preta", km_atual: 0, categoria_id: 1, filial_id: 1 });
  });

  it("opcionais preenchidos entram; valor de compra vira centavos", () => {
    const c = paraCorpoVeiculo({ ...v, renavam: "013.987.654-32", valor_compra: "R$ 13.490,00", data_compra: "2026-10-08", capacidade_tanque_litros: "12,5" });
    expect(c).toMatchObject({ renavam: "01398765432", valor_compra_centavos: 1349000, data_compra: "2026-10-08", capacidade_tanque_litros: "12.5" });
  });
});

describe("corpo com os campos da VEI-09 (T-421)", () => {
  const v = { ...VALORES_INICIAIS_VEICULO, placa: "TBC5H21", marca: "Honda", modelo: "Pop 110i ES", ano_fabricacao: "2026", ano_modelo: "2026", chassi: "9C2JC7500TR012345", cor: "Preta", km_atual: "0", filial_id: "1", categoria_id: "1" };

  it("test_vei_09_cadastro_sem_nada_nao_manda_blocos (CA-421-06)", () => {
    const c = paraCorpoVeiculo(v);
    for (const chave of ["combustivel", "documento", "rastreador", "anotacoes"]) expect(chave in c).toBe(false);
  });

  it("test_vei_09_cadastro_manda_so_o_que_tem_valor_com_inteiro_e_maiusculas (CA-421-05)", () => {
    const c = paraCorpoVeiculo({ ...v, combustivel: "gasolina", potencia_cv: "8", lotacao: "1", especie: "passageiro", tipo_documento: " Motocicleta ", numero_motor: "jc75 e1s123456", rastreador_numero: "356938035643810", rastreador_empresa: "Rastreia Fácil", anotacoes: "Retrovisor trocado" });
    expect(c).toMatchObject({
      combustivel: "gasolina",
      documento: { potencia_cv: 8, lotacao: 1, especie: "passageiro", tipo: "Motocicleta", numero_motor: "JC75E1S123456" },
      rastreador: { numero: "356938035643810", empresa: "Rastreia Fácil" },
      anotacoes: "Retrovisor trocado",
    });
    expect(Object.keys(c.documento ?? {}).sort()).toEqual(["especie", "lotacao", "numero_motor", "potencia_cv", "tipo"]);
  });

  it("test_vei_09_texto_que_nao_e_inteiro_vai_como_veio_e_a_api_recusa_no_campo (CA-421-07)", () => {
    const c = paraCorpoVeiculo({ ...v, peso_bruto_kg: "abc", potencia_cv: "1500" });
    expect(c.documento).toEqual({ peso_bruto_kg: "abc", potencia_cv: 1500 });
  });

  it("test_vei_09_editar_apaga_com_null_e_manda_cada_chave (CA-421-08)", () => {
    const c = paraCorpoEdicao({ ...v, combustivel: "", potencia_cv: "", lotacao: "1", anotacoes: "", rastreador_numero: "" }, { comMotorEObservacoes: true });
    expect(c.combustivel).toBeNull();
    expect(c.documento).toMatchObject({ potencia_cv: null, lotacao: 1, numero_motor: null, observacoes: null });
    expect(c.rastreador).toEqual({ numero: null, empresa: null });
    expect(c.anotacoes).toBeNull();
  });

  it("test_vei_09_editar_sem_permissao_para_motor_nao_manda_motor_nem_observacoes (CA-421-12)", () => {
    const c = paraCorpoEdicao({ ...v, numero_motor: "", observacoes_crlv: "" });
    expect(c.documento).toBeDefined();
    expect("numero_motor" in (c.documento ?? {})).toBe(false);
    expect("observacoes" in (c.documento ?? {})).toBe(false);
  });

  it("test_vei_08_editar_leva_o_comprovante_da_leitura (CA-421-10)", () => {
    expect(paraCorpoEdicao(v, { leitura: "assinado" }).leitura).toBe("assinado");
    expect("leitura" in paraCorpoEdicao(v)).toBe(false);
  });

  it("test_vei_09_erro_da_chave_pontuada_cai_no_campo_da_tela", () => {
    expect(NOME_DO_CAMPO_DA_API["documento.potencia_cv"]).toBe("potencia_cv");
    expect(NOME_DO_CAMPO_DA_API["documento.tipo"]).toBe("tipo_documento");
    expect(NOME_DO_CAMPO_DA_API["documento.observacoes"]).toBe("observacoes_crlv");
    expect(NOME_DO_CAMPO_DA_API["rastreador.numero"]).toBe("rastreador_numero");
    expect(NOME_DO_CAMPO_DA_API.anotacoes).toBe("anotacoes");
  });
});

describe("esquemaVeiculo", () => {
  it("exige os campos obrigatórios e deixa o formato para a API", () => {
    const r = esquemaVeiculo.safeParse(VALORES_INICIAIS_VEICULO);
    expect(r.success).toBe(false);
    const campos = r.success ? [] : r.error.issues.map((i) => i.path[0]);
    expect(campos).toEqual(expect.arrayContaining(["placa", "marca", "modelo", "chassi", "cor", "filial_id", "categoria_id"]));
    expect(esquemaVeiculo.safeParse({ ...VALORES_INICIAIS_VEICULO, placa: "x", marca: "x", modelo: "x", ano_fabricacao: "1", ano_modelo: "1", chassi: "curto", cor: "x", filial_id: "1", categoria_id: "1" }).success).toBe(true);
  });

  it("valor de compra que não é valor é recusado no campo", () => {
    const r = esquemaVeiculo.safeParse({ ...VALORES_INICIAIS_VEICULO, valor_compra: "muito" });
    expect(!r.success && r.error.issues.some((i) => i.path[0] === "valor_compra")).toBe(true);
  });
});

describe("valoresDaLeitura (VEI-08)", () => {
  const leitura = (campos: Partial<LeituraCrlv["campos"]>, lidos: string[]): LeituraCrlv => ({
    documento: "crlv",
    campos: { placa: null, chassi: null, renavam: null, marca: null, modelo: null, ano_fabricacao: null, ano_modelo: null, cor: null, combustivel: null, "documento.potencia_cv": null, "documento.cilindrada_cc": null, "documento.especie": null, "documento.tipo": null, "documento.carroceria": null, "documento.lotacao": null, "documento.peso_bruto_kg": null, "documento.numero_motor": null, "documento.observacoes": null, ...campos },
    lidos,
    quantidade: lidos.length,
    rotulo: "CRLV-e lido",
    exercicio: 2026,
    dicas: { marca_modelo: null, candidatos: [] },
    leitura: "c",
  });

  it("copia só o que está em lidos, como texto, e deixa o resto da tela como está", () => {
    const r = valoresDaLeitura(leitura({ placa: "TBC5H21", ano_fabricacao: 2025, ano_modelo: 2026, cor: "vermelha", combustivel: "gasolina" }, ["placa", "ano_fabricacao", "ano_modelo", "cor", "combustivel"]));
    // O combustível agora é campo da tela (VEI-09).
    expect(r.valores).toEqual({ placa: "TBC5H21", ano_fabricacao: "2025", ano_modelo: "2026", cor: "vermelha", combustivel: "gasolina" });
    expect(r.lidos).toEqual(["placa", "ano_fabricacao", "ano_modelo", "cor", "combustivel"]);
  });

  it("test_vei_08_le_os_campos_da_vei_09_pela_chave_pontuada_e_ignora_o_que_nao_esta_em_lidos (CA-421-01)", () => {
    const r = valoresDaLeitura(
      leitura(
        { "documento.potencia_cv": 8, "documento.cilindrada_cc": 109, "documento.especie": "passageiro", "documento.tipo": "Motocicleta", "documento.lotacao": 2, "documento.peso_bruto_kg": 240, "documento.numero_motor": "JC75E1S123456", "documento.carroceria": "NÃO APLICAVEL" },
        ["documento.potencia_cv", "documento.cilindrada_cc", "documento.especie", "documento.tipo", "documento.lotacao", "documento.peso_bruto_kg", "documento.numero_motor"],
      ),
    );
    expect(r.valores).toEqual({ potencia_cv: "8", cilindrada_cc: "109", especie: "passageiro", tipo_documento: "Motocicleta", lotacao: "2", peso_bruto_kg: "240", numero_motor: "JC75E1S123456" });
    // Rastreador e anotações nunca vêm da leitura (CA-421-04).
    expect(Object.keys(r.valores).some((k) => k.startsWith("rastreador") || k === "anotacoes")).toBe(false);
  });

  it("marca e modelo fora de lidos não entram, mesmo com texto", () => {
    const r = valoresDaLeitura(leitura({ placa: "TBC5H21", marca: "Honda", modelo: "Pop" }, ["placa"]));
    expect(r.valores).toEqual({ placa: "TBC5H21" });
  });
});
