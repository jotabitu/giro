import { describe, expect, it } from "vitest";
import { contas, ErroApi } from "@/lib/api";
import { mensagemDoErro, tempoDeEspera } from "./erros";

describe("mensagem do 429 (PLT-08, USR-06)", () => {
  it("bloqueio diz até que horas, em horário de Brasília", () => {
    const e = new ErroApi(429, "PLT-08", "Acesso bloqueado por 15 minutos depois de 5 senhas erradas", { tentar_de_novo_em: "2026-10-09T17:32:00Z" });
    expect(mensagemDoErro(e)).toBe("Acesso bloqueado por 15 minutos depois de 5 senhas erradas. Você pode tentar de novo às 14:32.");
  });

  it("bloqueio sem horário válido mostra só a mensagem da API", () => {
    expect(mensagemDoErro(new ErroApi(429, "USR-06", "Acesso bloqueado por 15 minutos depois de 5 tentativas erradas"))).toBe(
      "Acesso bloqueado por 15 minutos depois de 5 tentativas erradas.",
    );
  });

  it("muitas_requisicoes diz quanto esperar", () => {
    const e = new ErroApi(429, "muitas_requisicoes", "Muitas tentativas seguidas. Espere um pouco e tente de novo.", { tentar_de_novo_em_segundos: 42 });
    expect(mensagemDoErro(e)).toBe("Muitas tentativas seguidas. Espere 42 segundos e tente de novo.");
  });

  it("muitas_requisicoes sem segundos usa a mensagem da API", () => {
    const e = new ErroApi(429, "muitas_requisicoes", "Muitas tentativas seguidas. Espere um pouco e tente de novo.");
    expect(mensagemDoErro(e)).toBe("Muitas tentativas seguidas. Espere um pouco e tente de novo.");
  });

  it("401 credenciais_invalidas não diz qual dado errou", () => {
    expect(mensagemDoErro(new ErroApi(401, "credenciais_invalidas", "E-mail ou senha incorretos"))).toBe("E-mail ou senha incorretos");
  });

  it("erro que não é da API vira texto genérico", () => {
    expect(mensagemDoErro(new Error("x"))).toBe("Não foi possível concluir agora. Tente de novo.");
  });
});

describe("tempo de espera", () => {
  it("usa segundos até 59 e minutos arredondados para cima depois", () => {
    expect([tempoDeEspera(1), tempoDeEspera(42), tempoDeEspera(60), tempoDeEspera(61)]).toEqual(["1 segundo", "42 segundos", "1 minuto", "2 minutos"]);
  });
});

describe("dados falsos do login", () => {
  it("5 senhas erradas bloqueiam com 429 e horário", async () => {
    let erro: unknown;
    for (let i = 0; i < 5; i++) {
      try {
        await contas.entrar({ email: "bloqueio@motorapida.com.br", senha: "errada", aparelho: "desktop" });
      } catch (e) {
        erro = e;
      }
    }
    expect(erro).toBeInstanceOf(ErroApi);
    expect((erro as ErroApi).status).toBe(429);
    expect(mensagemDoErro(erro)).toMatch(/às \d{2}:\d{2}\.$/);
  });

  it("11 entradas no mesmo minuto respondem 429 muitas_requisicoes", async () => {
    let erro: unknown;
    for (let i = 0; i < 11; i++) {
      try {
        await contas.entrar({ email: "pressa@motorapida.com.br", senha: "errada", aparelho: "desktop" });
      } catch (e) {
        erro = e;
      }
    }
    expect((erro as ErroApi).codigo).toBe("muitas_requisicoes");
    expect(mensagemDoErro(erro)).toMatch(/Espere \d+ segundos? e tente de novo\.$/);
  });
});
