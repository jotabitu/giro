// DADOS FALSOS de docs/api/plataforma.md ("Recebimentos da empresa"). Só api-falsa.ts importa este arquivo.
import { ErroApi } from "@/lib/api/tipos";
import type { CorpoDosRecebimentos, Recebimentos, SituacaoDosRecebimentos, SugestaoDeRecebimentos } from "@/lib/api/tipos-recebimentos";
import { pausa } from "./falso";

export const SUGESTAO_MOTO_RAPIDA: SugestaoDeRecebimentos = {
  nome: "Moto Rápida Locadora LTDA",
  documento: "12345678000195",
  email: "mariana@motorapida.com.br",
  celular: "85998124410",
  cep: "60110000",
  logradouro: "Av. Santos Dumont",
  numero: "1500",
  complemento: "",
  bairro: "Aldeota",
};

const TEXTOS: Record<SituacaoDosRecebimentos, { rotulo: string; mensagem: string }> = {
  desconectado: { rotulo: "Não conectado", mensagem: "Conecte para gerar Pix e boleto e dar baixa sozinho." },
  pendente: { rotulo: "Em análise pelo parceiro", mensagem: "O parceiro está conferindo o cadastro. Enquanto isso, registre os pagamentos à mão em Contas a receber." },
  aprovada: { rotulo: "Recebimentos ligados", mensagem: "Pix e boleto saem pelo parceiro, e a baixa é feita sozinha." },
  recusada: { rotulo: "Cadastro recusado", mensagem: "O parceiro recusou o cadastro. Fale com a equipe Giro." },
};

export function recebimentosEm(situacao: SituacaoDosRecebimentos): Recebimentos {
  const desconectado = situacao === "desconectado";
  return {
    situacao,
    ...TEXTOS[situacao],
    conectado_em: desconectado ? null : "2026-10-07T13:20:00Z",
    sugestao: desconectado ? SUGESTAO_MOTO_RAPIDA : null,
    acoes: { conectar: desconectado },
  };
}

let atual: Recebimentos = recebimentosEm("desconectado");
/** O erro que o próximo `conectar` devolve (409, 422, 503 e 429 do contrato). */
let falha: ErroApi | null = null;
export const corposEnviados: CorpoDosRecebimentos[] = [];

export function definirRecebimentosFalsos(situacao: SituacaoDosRecebimentos = "desconectado", erro: ErroApi | null = null) {
  atual = recebimentosEm(situacao);
  falha = erro;
  corposEnviados.length = 0;
}

export const recebimentosFalso = {
  async obter(): Promise<Recebimentos> {
    await pausa();
    return atual;
  },
  async conectar(corpo: CorpoDosRecebimentos): Promise<Recebimentos> {
    await pausa();
    corposEnviados.push(corpo);
    if (falha) throw falha;
    if (corpo.faturamento_mensal_centavos <= 0) throw new ErroApi(400, "validacao", "Confira os campos.", undefined, { faturamento_mensal_centavos: "Informe um valor maior que zero." });
    atual = recebimentosEm("pendente");
    return atual;
  },
};
