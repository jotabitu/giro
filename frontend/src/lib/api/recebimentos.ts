// Recebimentos pelo parceiro na API real (docs/api/plataforma.md): só o administrador, só com `recebimento_parceiro` (PLT-12).
import { http } from "./http";
import type { CorpoDosRecebimentos, Recebimentos } from "./tipos-recebimentos";

export const recebimentosApi = {
  /** 403 `PLT-12` no Essencial; em `pendente` a API consulta o parceiro no máximo uma vez por minuto. */
  obter(): Promise<Recebimentos> {
    return http.get("/api/recebimentos/");
  },

  /** 201 com `situacao: "pendente"`. 400 `validacao` por campo; 409 `recebimentos_conectados`; 422 `parceiro_recusou`; 503 `parceiro_indisponivel`; 429 `muitas_requisicoes`. */
  conectar(corpo: CorpoDosRecebimentos): Promise<Recebimentos> {
    return http.post("/api/recebimentos/", corpo);
  },
};
