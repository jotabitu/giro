// T-363 · Modelos de contrato (IMP-04, S-09, LOC-15): a tela só monta o texto do marcador e os rótulos.
import { describe, expect, it } from "vitest";
import { inserirMarcador, podePublicar, rotuloDePublicar, rotuloDeUso, rotuloDoModelo } from "./contratos";

const publicado = { status: "publicado", versao_publicada: 3, tem_rascunho: false, arquivado: false } as const;

describe("lib/contratos", () => {
  it("s_09_inserir_marcador: entra no cursor e o cursor vai para depois dele", () => {
    expect(inserirMarcador("Olá , tudo bem", "cliente.nome", 4, 4)).toEqual({ texto: "Olá {{cliente.nome}}, tudo bem", cursor: 4 + "{{cliente.nome}}".length });
  });

  it("s_09_inserir_marcador: troca o trecho selecionado e aceita cursor fora do texto", () => {
    expect(inserirMarcador("abc XXX def", "veiculo.placa", 4, 7).texto).toBe("abc {{veiculo.placa}} def");
    expect(inserirMarcador("abc", "empresa.nome", 99, 99).texto).toBe("abc{{empresa.nome}}");
  });

  it("loc_15_rotulos: publicado com versão, rascunho e arquivado", () => {
    expect(rotuloDoModelo(publicado)).toBe("Publicado · v3");
    expect(rotuloDoModelo({ ...publicado, status: "rascunho", versao_publicada: null })).toBe("Rascunho");
    expect(rotuloDoModelo({ ...publicado, arquivado: true })).toBe("Arquivado");
  });

  it("loc_15_publicar: o botão traz a versão seguinte e só aparece se há o que publicar", () => {
    expect(rotuloDePublicar({ versao_publicada: 3 })).toBe("Publicar versão 4");
    expect(rotuloDePublicar({ versao_publicada: null })).toBe("Publicar versão 1");
    expect(podePublicar(publicado)).toBe(false);
    expect(podePublicar({ ...publicado, tem_rascunho: true })).toBe(true);
    expect(podePublicar({ ...publicado, status: "rascunho", versao_publicada: null, tem_rascunho: true })).toBe(true);
    expect(podePublicar({ ...publicado, tem_rascunho: true, arquivado: true })).toBe(false);
  });

  it("rotuloDeUso: locações, vendas e sem uso", () => {
    expect(rotuloDeUso({ finalidade: "venda", contratos_gerados: 3 })).toBe("usado em 3 vendas");
    expect(rotuloDeUso({ finalidade: "locacao", contratos_gerados: 1 })).toBe("usado em 1 locação");
    expect(rotuloDeUso({ finalidade: "locacao", contratos_gerados: 0 })).toBe("ainda sem uso");
  });
});
