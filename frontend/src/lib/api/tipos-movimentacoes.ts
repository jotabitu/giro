// Tipos das Movimentações a partir do cliente gerado do OpenAPI (schema.d.ts, `npm run api:gerar`) e de docs/api/movimentacoes.md.
// O gerador deixa alguns campos soltos; aqui eles ganham os valores fechados do contrato. Não importe este arquivo fora de lib/api: use `@/lib/api`.
import type { components } from "./schema";
import type { CategoriaDaDespesa } from "./tipos-financeiro";
import type { Combustivel } from "./tipos-vistorias";

type S = components["schemas"];

export type StatusDaMovimentacao = S["MovimentacaoStatusEnum"];
export type TipoDoLocalDeApoio = "lava_jato" | "oficina" | "despachante" | "outro";
export type PosicaoDaFotoDaChegada = "frente" | "traseira" | "lado_esquerdo" | "lado_direito";

export type LocalDeApoio = Omit<S["Local"], "tipo"> & { tipo: TipoDoLocalDeApoio };

export type ParadaDaMovimentacao = Omit<S["Parada"], "local" | "categoria"> & { local: LocalDeApoio; categoria: CategoriaDaDespesa };

export type FotoDaChegada = Omit<S["FotoDaMovimentacao"], "posicao"> & { posicao: PosicaoDaFotoDaChegada };

export type ChegadaDaMovimentacao = Omit<S["Chegada"], "combustivel" | "fotos"> & { combustivel: Combustivel | null; fotos: FotoDaChegada[] };

/** O que a tela mostra como botão: a API decide pelo perfil, pela filial, por quem leva, pelo status e pela próxima etapa. */
export type AcoesDaMovimentacao = S["AcoesDaMovimentacao"];

export type VeiculoDaMovimentacao = S["VeiculoDaMovimentacao"];

export type Movimentacao = Omit<S["Movimentacao"], "veiculo" | "paradas" | "chegada" | "fotos_chegada"> & {
  veiculo: VeiculoDaMovimentacao;
  paradas: ParadaDaMovimentacao[];
  chegada: ChegadaDaMovimentacao | null;
  /** As fotos já enviadas, para a tela contar "Fotos · 2 de 4". */
  fotos_chegada: FotoDaChegada[];
};

/** Linha do quadro e da lista: a representação sem `paradas` e sem `chegada`, mais o total de paradas e o resumo pronto (docs/api/movimentacoes.md, "Quadro"). */
export type LinhaDaMovimentacao = S["LinhaDaMovimentacao"];

export type ColunaDoQuadro = { status: Exclude<StatusDaMovimentacao, "cancelada">; rotulo: string; total: number; itens: LinhaDaMovimentacao[] };
export type QuadroDeMovimentacoes = { colunas: ColunaDoQuadro[] };

export type FiltroDeMovimentacoes = { filial?: number; busca?: string; levando?: "eu" };

/** `categoria` fica de fora: a API aplica o padrão (`outros`, e `manutencao` na oficina, MOV-04). */
export type NovaParada = { local_id: number; servico: string; valor_previsto_centavos: number; categoria?: CategoriaDaDespesa };

export type NovaMovimentacao = Omit<S["NovaMovimentacao"], "paradas" | "categoria_destino_id" | "agendada_para"> & {
  paradas: NovaParada[];
  categoria_destino_id: number | null;
  /** ISO em UTC; obrigatório e no futuro quando `sair_agora` é falso. */
  agendada_para: string | null;
};

export type ChegadaNoDestino = { km: number; combustivel?: Combustivel; recebido_por_id?: number };

export type NovoLocalDeApoio = { nome: string; tipo: TipoDoLocalDeApoio };

/** Saída da parada (`MOV-04`): o valor pago e, se houver, a nota. */
export type SaidaDaParada = { valor_pago_centavos: number; nota?: File };

/** Quem pode levar (`/pessoas/`) e quem pode receber (`/{id}/recebedores/`): só o necessário para escolher, sem e-mail nem celular. */
export type PessoaParaEscolher = S["Pessoa"];

/** `pode.movimentacoes` de GET /api/auth/eu/ (docs/api/contas.md): `gerir` (administrador e gerente), `levar` (vendedor e vistoriador), `nao`. */
export type PodeMovimentacoes = S["MovimentacoesEnum"];
