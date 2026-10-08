import { describe, expect, it } from "vitest";
import type { Veiculo } from "./api";
import { VALORES_INICIAIS, paraCorpo, rotaDaAcao, textoDePendencias } from "./clientes";
import { fatoDoVeiculo, situacaoDoDocumento } from "./frota";
import { iniciais, nomeCurto } from "./formatos";

describe("clientes", () => {
  it("test_cli_01_corpo_manda_so_digitos_e_omite_blocos_vazios", () => {
    const corpo = paraCorpo({ ...VALORES_INICIAIS, nome: " Lucas ", documento: "123.456.789-09", celular: "(85) 98877-1203" });
    expect(corpo).toEqual({ tipo: "pf", nome: "Lucas", documento: "12345678909", celular: "85988771203" });
  });

  it("test_cli_03_pj_manda_responsavel_e_nao_manda_nascimento", () => {
    const corpo = paraCorpo({
      ...VALORES_INICIAIS,
      tipo: "pj",
      nome: "Veloz Ltda",
      documento: "11.222.333/0001-81",
      celular: "85984410077",
      nascimento: "1990-01-01",
      responsavel: { nome: "Ana", cpf: "123.456.789-09", celular: "" },
    });
    expect(corpo.nascimento).toBeUndefined();
    expect(corpo.responsavel).toEqual({ nome: "Ana", cpf: "12345678909" });
  });

  it("test_cli_07_rota_da_acao_principal", () => {
    expect(rotaDaAcao({ codigo: "completar_cadastro", rotulo: "Completar cadastro", alvo: { tipo: "cliente", id: 7 } })).toBe("/clientes/7");
    expect(rotaDaAcao({ codigo: "nova_locacao", rotulo: "Nova locação", alvo: { tipo: "cliente", id: 7 } })).toBe("/locacoes/nova?cliente=7");
  });

  it("test_cli_03_pendencias_em_texto", () => {
    expect(textoDePendencias(["selfie_documento", "comprovante_residencia"])).toBe("Faltam selfie com documento e comprovante de residência para liberar a locação.");
    expect(textoDePendencias(["cnh"])).toBe("Falta dados da CNH para liberar a locação.");
    expect(textoDePendencias([])).toBeNull();
  });

  it("nome curto e iniciais", () => {
    expect(nomeCurto("Carlos Menezes")).toBe("Carlos M.");
    expect(nomeCurto("Maria")).toBe("Maria");
    expect(iniciais("Lucas Ferreira da Silva")).toBe("LS");
  });
});

describe("frota", () => {
  it("test_vei_01_documento_mostra_dias_para_vencer", () => {
    expect(situacaoDoDocumento("vence_em_breve", 18)).toEqual({ rotulo: "Vence em 18 dias", tom: "alerta" });
    expect(situacaoDoDocumento("em_dia", 85).rotulo).toBe("Em dia");
  });

  it("fato do cartão segue a situação", () => {
    const base = { filial: { id: 1, nome: "Filial Centro" }, status: "disponivel", locacao_atual: null, manutencao: { proxima: { servico: "Revisão", km: 5000 }, os_aberta: null } } as unknown as Veiculo;
    expect(fatoDoVeiculo(base)).toEqual({ rotulo: "Revisão", valor: "5.000 km" });
    expect(fatoDoVeiculo({ ...base, manutencao: { proxima: null, os_aberta: { id: 1, codigo: "OS-0193", status: "aberta" } } }).valor).toBe("OS-0193");
  });
});
