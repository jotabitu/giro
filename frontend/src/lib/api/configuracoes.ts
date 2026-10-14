// Resumo de Configurações na API real (docs/api/configuracoes.md): os cartões e a faixa da implantação.
import { http } from "./http";
import type { Configuracoes } from "./tipos-configuracoes";

export const configuracoesApi = {
  /** Só o administrador (403 `permissao` para os outros). Cartão de área sem tela não vem. */
  resumo(): Promise<Configuracoes> {
    return http.get("/api/configuracoes/");
  },
};
