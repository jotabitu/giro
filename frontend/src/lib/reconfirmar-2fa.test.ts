// T-348 · Reconfirmar as 2 etapas no meio da ação (USR-02, USR-06, PLT-06; docs/api/contas.md, "Como a tela trata o 403 `2fa_recente`").
import { describe, expect, it, vi } from "vitest";
import { ErroApi } from "@/lib/api";
import { comReconfirmacao, confirmarCodigo, ehDeDoisFatoresRecentes } from "./reconfirmar-2fa";

const MSG = "Confirme o código do autenticador para cancelar a assinatura.";
const recente = () => new ErroApi(403, "2fa_recente", MSG);

describe("comReconfirmacao", () => {
  it("usr_02_caminho_feliz: 403, pede o código, repete uma vez com o mesmo corpo e conclui", async () => {
    const corpo = { motivo: "preco_alto", nome_confirmacao: "Moto Rápida" };
    const acao = vi.fn(async (c: typeof corpo) => {
      if (acao.mock.calls.length === 1) throw recente();
      return { ok: true, c };
    });
    const pedir = vi.fn(async () => {});
    const r = await comReconfirmacao(() => acao(corpo), pedir);
    expect(pedir).toHaveBeenCalledExactlyOnceWith(MSG);
    expect(acao).toHaveBeenCalledTimes(2);
    expect(acao.mock.calls[1]![0]).toBe(corpo);
    expect(r).toEqual({ ok: true, c: corpo });
  });

  it("sem 403 não pede nada", async () => {
    const pedir = vi.fn(async () => {});
    await expect(comReconfirmacao(async () => 7, pedir)).resolves.toBe(7);
    expect(pedir).not.toHaveBeenCalled();
  });

  it("outros erros passam direto, inclusive 403 de outro código", async () => {
    const pedir = vi.fn(async () => {});
    const outro = new ErroApi(403, "PLT-07", "Acesso de suporte.");
    await expect(comReconfirmacao(() => Promise.reject(outro), pedir)).rejects.toBe(outro);
    expect(pedir).not.toHaveBeenCalled();
  });

  it("cancelar o diálogo não repete a ação", async () => {
    const acao = vi.fn(async () => {
      throw recente();
    });
    const cancelada = new Error("cancelada");
    await expect(comReconfirmacao(acao, async () => Promise.reject(cancelada))).rejects.toBe(cancelada);
    expect(acao).toHaveBeenCalledTimes(1);
  });

  it("usr_02_segunda_recusa_sem_laco: se a repetição volta 2fa_recente, sobe o erro e pede uma vez só", async () => {
    const acao = vi.fn(async () => {
      throw recente();
    });
    const pedir = vi.fn(async () => {});
    const erro = await comReconfirmacao(acao, pedir).catch((e: unknown) => e);
    expect(ehDeDoisFatoresRecentes(erro)).toBe(true);
    expect((erro as ErroApi).message).toBe(MSG);
    expect(acao).toHaveBeenCalledTimes(2);
    expect(pedir).toHaveBeenCalledTimes(1);
  });
});

describe("confirmarCodigo", () => {
  it("ok: manda só o código e devolve ok", async () => {
    const reconfirmar = vi.fn(async () => {});
    await expect(confirmarCodigo(reconfirmar, { codigo: "123456" })).resolves.toEqual({ tipo: "ok" });
    expect(reconfirmar).toHaveBeenCalledWith({ codigo: "123456" });
  });

  it("usr_02_codigo_errado: 400 vira erro do campo e o diálogo fica aberto", async () => {
    const e = new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { codigo: "Código incorreto. Confira o horário do celular e tente de novo." });
    await expect(confirmarCodigo(async () => Promise.reject(e), { codigo: "000000" })).resolves.toEqual({
      tipo: "campo",
      mensagem: "Código incorreto. Confira o horário do celular e tente de novo.",
    });
  });

  it("400 do código de recuperação lê o campo `codigo_recuperacao`", async () => {
    const e = new ErroApi(400, "validacao", "x", undefined, { codigo_recuperacao: "Código de recuperação inválido." });
    await expect(confirmarCodigo(async () => Promise.reject(e), { codigo_recuperacao: "AAAA-BBBB" })).resolves.toEqual({
      tipo: "campo",
      mensagem: "Código de recuperação inválido.",
    });
  });

  it("usr_06_429: encerra com o erro, que carrega o horário do bloqueio", async () => {
    const e = new ErroApi(429, "USR-06", "Acesso bloqueado por 15 minutos depois de 5 tentativas erradas", { tentar_de_novo_em: "2026-10-25T17:30:00Z" });
    await expect(confirmarCodigo(async () => Promise.reject(e), { codigo: "000000" })).resolves.toEqual({ tipo: "encerrar", erro: e });
  });

  it("409 2fa_inativo: encerra com o erro", async () => {
    const e = new ErroApi(409, "2fa_inativo", "Ative a verificação em 2 etapas primeiro.");
    await expect(confirmarCodigo(async () => Promise.reject(e), { codigo: "123456" })).resolves.toEqual({ tipo: "encerrar", erro: e });
  });
});
