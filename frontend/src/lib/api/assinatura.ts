// Assinatura da empresa na API real (docs/api/assinatura.md). Só o administrador usa as rotas de escrita.
import { http } from "./http";
import type {
  Assinatura,
  CorrecaoDeDadosFiscais,
  DadosFiscais,
  ConfirmacaoDeMudanca,
  CobrancaDaFatura,
  FaturaDetalhada,
  FormaDaAssinatura,
  ListaDeFaturas,
  MeioDePagarFatura,
  PedidoDeCancelamentoDaAssinatura,
  PedidoDeMudancaDePlano,
  PedidoDePausa,
  PlanosParaMudar,
  RespostaDaForma,
  SimulacaoDeMudanca,
  TelaDoCancelamento,
} from "./tipos-assinatura";

export const assinaturaApi = {
  obter(): Promise<Assinatura> {
    return http.get("/api/assinatura/");
  },

  /** Mudar de plano e Comparar planos abrem a mesma lista; `cabe` e `excede` vêm da API (PLT-04). */
  planos(): Promise<PlanosParaMudar> {
    return http.get("/api/assinatura/planos/");
  },

  /** Não grava nada: devolve o que vale, a diferença e a mensagem. 422 `PLT-04` quando o uso não cabe. */
  simularMudanca(corpo: PedidoDeMudancaDePlano): Promise<SimulacaoDeMudanca> {
    return http.post("/api/assinatura/mudanca-plano/simular/", corpo);
  },

  /** `confirmar_valor_centavos` é a diferença do simular; 409 `valor_mudou` se ela mudou. Devolve a assinatura já atualizada. */
  mudarPlano(corpo: ConfirmacaoDeMudanca): Promise<Assinatura> {
    return http.post("/api/assinatura/mudanca-plano/", corpo);
  },

  desfazerMudanca(): Promise<Assinatura> {
    return http.delete("/api/assinatura/mudanca-plano/");
  },

  /** Nenhum dado de cartão passa por aqui (ADR 0023): o cartão é digitado na página do parceiro. */
  escolherForma(forma: FormaDaAssinatura): Promise<RespostaDaForma> {
    return http.put("/api/assinatura/forma-pagamento/", { forma });
  },

  faturas(f: { status?: "aberta" | "paga" | "atrasada" | "cancelada"; cursor?: string } = {}): Promise<ListaDeFaturas> {
    return http.get("/api/assinatura/faturas/", { status: f.status, cursor: f.cursor });
  },

  fatura(codigo: string): Promise<FaturaDetalhada> {
    return http.get(`/api/assinatura/faturas/${codigo}/`);
  },

  /** Sem `meio`, paga pela forma cadastrada; com `meio`, por outro meio sem trocar a forma. */
  pagarFatura(codigo: string, meio?: MeioDePagarFatura): Promise<CobrancaDaFatura> {
    return http.post(`/api/assinatura/faturas/${codigo}/pagar/`, meio ? { meio } : {});
  },

  /** O CNPJ não muda por aqui; o endereço vai inteiro. */
  editarDadosFiscais(corpo: CorrecaoDeDadosFiscais): Promise<{ dados_fiscais: DadosFiscais }> {
    return http.patch("/api/assinatura/dados-fiscais/", corpo);
  },

  /** O que a Admin-Cancelar mostra hoje: motivos, alternativas, o_que_acontece, datas e nome (PLT-06, AUD-08). */
  telaCancelamento(): Promise<TelaDoCancelamento> {
    return http.get("/api/assinatura/cancelamento/");
  },

  /** Cancela a assinatura (PLT-06); 422 `nome_nao_confere` se o nome digitado divergir. */
  cancelar(corpo: PedidoDeCancelamentoDaAssinatura): Promise<Assinatura> {
    return http.post("/api/assinatura/cancelamento/", corpo);
  },

  /** Desfaz o cancelamento até o último dia de acesso (`acesso_ate`, PLT-06). */
  desfazerCancelamento(): Promise<Assinatura> {
    return http.delete("/api/assinatura/cancelamento/");
  },

  /** Pausa de 1 a 3 meses no fim do período pago (só a `ativa`, PLT-06). */
  pausar(corpo: PedidoDePausa): Promise<Assinatura> {
    return http.post("/api/assinatura/pausa/", corpo);
  },

  /** Volta da pausa (`pausada`) ou desiste da pausa agendada (`ativa` antes de `pausa_inicio`, PLT-06). */
  encerrarPausa(): Promise<Assinatura> {
    return http.delete("/api/assinatura/pausa/");
  },
};
