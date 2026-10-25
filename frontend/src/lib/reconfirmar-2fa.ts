import { ErroApi } from "@/lib/api";

// Reconfirmação das 2 etapas no meio de uma ação (USR-02, USR-06, PLT-06; docs/api/contas.md, "Como a tela trata o 403 `2fa_recente`").

export type CorpoDoCodigo = { codigo: string } | { codigo_recuperacao: string };

/** A pessoa fechou o diálogo com "Cancelar": nada foi enviado e a ação não roda. */
export class ReconfirmacaoCancelada extends Error {
  constructor() {
    super("Reconfirmação cancelada.");
    this.name = "ReconfirmacaoCancelada";
  }
}

export const ehDeDoisFatoresRecentes = (e: unknown): e is ErroApi => e instanceof ErroApi && e.status === 403 && e.codigo === "2fa_recente";

/**
 * Roda a ação. No 403 `2fa_recente`, pede a reconfirmação (`pedir` recebe a `mensagem` do 403 e só resolve depois
 * de o access ter sido trocado) e repete a ação uma vez, com o mesmo corpo. Se a repetição recusar de novo, o erro
 * sobe como está e não há outra volta.
 */
export async function comReconfirmacao<T>(acao: () => Promise<T>, pedir: (mensagem: string) => Promise<void>): Promise<T> {
  try {
    return await acao();
  } catch (e) {
    if (!ehDeDoisFatoresRecentes(e)) throw e;
    await pedir(e.message);
    return acao();
  }
}

export type ResultadoDaConfirmacao =
  | { tipo: "ok" }
  /** 400: o erro vai no campo e o diálogo continua aberto. */
  | { tipo: "campo"; mensagem: string }
  /** 429, 409 `2fa_inativo` e o resto: o diálogo fecha e a tela mostra o erro. */
  | { tipo: "encerrar"; erro: unknown };

/** Chama a reconfirmação e diz o que o diálogo faz com a resposta. O código só vive nesta chamada. */
export async function confirmarCodigo(reconfirmar: (corpo: CorpoDoCodigo) => Promise<void>, corpo: CorpoDoCodigo): Promise<ResultadoDaConfirmacao> {
  try {
    await reconfirmar(corpo);
    return { tipo: "ok" };
  } catch (e) {
    if (e instanceof ErroApi && e.status === 400) {
      const campo = "codigo" in corpo ? "codigo" : "codigo_recuperacao";
      return { tipo: "campo", mensagem: e.campos?.[campo] ?? Object.values(e.campos ?? {})[0] ?? e.message };
    }
    return { tipo: "encerrar", erro: e };
  }
}
