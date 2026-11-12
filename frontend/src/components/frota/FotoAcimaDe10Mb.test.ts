import { describe, expect, it } from "vitest";
import { ErroApi } from "@/lib/api";
import nextConfig from "../../../next.config";
import { FOTO_INVALIDA, fotoCabe, mensagemDaRecusa } from "./GaleriaDoEditar";
import { enviarEmSequencia, itensDoEnvio, escolherFotos } from "./FotosDoCadastro";

// T-450, VEI-10: foto acima de 10 MB.
const arquivo = (nome: string, bytes: number) => new File([new Uint8Array(1)], nome, { type: "image/jpeg" }) && Object.defineProperty(new File(["x"], nome, { type: "image/jpeg" }), "size", { value: bytes });
const grande = arquivo("grande.jpg", 11 * 1024 * 1024) as File;
const normal = arquivo("moto.jpg", 2 * 1024 * 1024) as File;

describe("foto acima de 10 MB (T-450)", () => {
  it("test_vei_10_next_aceita_12mb_como_o_proxy", () => {
    expect(nextConfig.experimental?.middlewareClientMaxBodySize).toBe("12mb");
  });
  it("test_vei_10_editar_recusa_na_escolha: 11 MB não cabe, 2 MB cabe", () => {
    expect(fotoCabe(grande)).toBe(false);
    expect(fotoCabe(normal)).toBe(true);
  });
  it("test_vei_10_413_e_queda_de_conexao_dizem_a_frase_do_formato", () => {
    expect(mensagemDaRecusa(new ErroApi(413, "x", "x"), grande)).toBe(FOTO_INVALIDA);
    expect(mensagemDaRecusa(new ErroApi(0, "sem_conexao", "Sem conexão."), grande)).toBe(FOTO_INVALIDA);
    expect(mensagemDaRecusa(new ErroApi(500, "x", "Erro."), grande)).toBe(FOTO_INVALIDA);
    // foto dentro do limite com a conexão caída continua sendo falha de conexão
    expect(mensagemDaRecusa(new ErroApi(0, "sem_conexao", "Sem conexão."), normal)).toBe("Sem conexão.");
  });
  it("test_vei_10_cadastro_foto_grande_sem_conexao_vira_recusa_e_nao_para_a_fila", async () => {
    const { lista } = escolherFotos([], [normal]);
    const itens = itensDoEnvio(lista, null);
    itens[0]!.arquivo = grande;
    const fim = await enviarEmSequencia(itens, async () => Promise.reject(new ErroApi(0, "sem_conexao", "x")), () => {});
    expect(fim[0]?.estado).toBe("recusada");
    expect(fim[0]?.mensagem).toBe(FOTO_INVALIDA);
  });
});
