import { describe, expect, it } from "vitest";
import { ErroApi } from "@/lib/api/tipos";
import { mensagemDaLeitura } from "./PreencherPeloCrlv";

describe("mensagemDaLeitura (VEI-08)", () => {
  it("422 e 503 mostram a mensagem da API como veio", () => {
    expect(mensagemDaLeitura(new ErroApi(422, "VEI-08", "Não conseguimos ler este documento. Preencha os campos à mão."))).toBe("Não conseguimos ler este documento. Preencha os campos à mão.");
    expect(mensagemDaLeitura(new ErroApi(503, "leitura_ocupada", "Muitas leituras ao mesmo tempo. Tente de novo em instantes."))).toBe("Muitas leituras ao mesmo tempo. Tente de novo em instantes.");
  });

  it("400 mostra o texto do campo arquivo", () => {
    expect(mensagemDaLeitura(new ErroApi(400, "validacao", "Confira os campos", undefined, { arquivo: "Envie o PDF do CRLV-e." }))).toBe("Envie o PDF do CRLV-e.");
  });

  it("429 diz quanto esperar", () => {
    const e = new ErroApi(429, "muitas_requisicoes", "Muitas tentativas", { tentar_de_novo_em_segundos: 120 });
    expect(mensagemDaLeitura(e)).toBe("Muitas tentativas seguidas. Espere 2 minutos e tente de novo.");
  });
});
