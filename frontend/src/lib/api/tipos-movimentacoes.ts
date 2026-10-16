// PROVISÓRIO (T-289): tipos escritos à mão a partir de docs/api/movimentacoes.md, porque as rotas ainda não estão no OpenAPI
// (T-288, backend). Quando a T-288 entregar e `npm run api:gerar` trouxer os schemas, trocar tudo isto pelos tipos gerados
// (`components["schemas"][...]`) e apagar este arquivo. Não importe este arquivo fora de lib/api: use `@/lib/api`.
import type { CategoriaDaDespesa } from "./tipos-financeiro";
import type { Combustivel } from "./tipos-vistorias";

export type StatusDaMovimentacao = "agendada" | "em_transito" | "no_local" | "concluida" | "cancelada";
export type TipoDoLocalDeApoio = "lava_jato" | "oficina" | "despachante" | "outro";
export type PosicaoDaFotoDaChegada = "frente" | "traseira" | "lado_esquerdo" | "lado_direito";

export type LocalDeApoio = { id: number; nome: string; tipo: TipoDoLocalDeApoio; ativo: boolean };

export type ParadaDaMovimentacao = {
  id: number;
  ordem: number;
  local: LocalDeApoio;
  servico: string;
  categoria: CategoriaDaDespesa;
  /** Ausente para o vistoriador (USR-09). */
  valor_previsto_centavos?: number;
  chegou_em: string | null;
  saiu_em: string | null;
  valor_pago_centavos?: number | null;
  despesa: { id: number; status: string; sem_nota: boolean } | null;
};

export type FotoDaChegada = { posicao: PosicaoDaFotoDaChegada; url: string; url_expira_em: string };

export type ChegadaDaMovimentacao = {
  km: number;
  combustivel: Combustivel | null;
  recebido_por: { id: number; nome: string } | null;
  fotos: FotoDaChegada[];
};

/** O que a tela mostra como botão: a API decide pelo perfil, pela filial, por quem leva, pelo status e pela próxima etapa. */
export type AcoesDaMovimentacao = {
  editar: boolean;
  iniciar: boolean;
  cancelar: boolean;
  chegar_parada: boolean;
  sair_parada: boolean;
  registrar_chegada: boolean;
};

export type Movimentacao = {
  id: number;
  codigo: string;
  status: StatusDaMovimentacao;
  veiculo: { id: number; placa: string; modelo: string; status: string };
  filial_saida: { id: number; nome: string };
  destino: { id: number; nome: string };
  transferencia: boolean;
  categoria_destino?: { id: number; nome: string } | null;
  rota: string;
  levado_por: { id: number; nome: string };
  agendada_para: string | null;
  iniciada_em: string | null;
  concluida_em: string | null;
  duracao_minutos: number | null;
  vistoria_rapida: boolean;
  km_saida: number | null;
  paradas: ParadaDaMovimentacao[];
  /** `parada:<id>`, `destino` ou `null` (agendada, concluída, cancelada). */
  proxima_etapa: string | null;
  chegada: ChegadaDaMovimentacao | null;
  /** As fotos já enviadas, para a tela contar "Fotos · 2 de 4". */
  fotos_chegada?: FotoDaChegada[];
  /** Ausente para o vistoriador. */
  custo_centavos?: number;
  acoes: AcoesDaMovimentacao;
};

/** Linha do quadro e da lista: a representação sem `paradas` e sem `chegada`, mais o total de paradas e o resumo pronto. */
export type LinhaDaMovimentacao = Omit<Movimentacao, "paradas" | "chegada"> & { paradas_total: number; resumo: string };

export type ColunaDoQuadro = { status: Exclude<StatusDaMovimentacao, "cancelada">; rotulo: string; total: number; itens: LinhaDaMovimentacao[] };
export type QuadroDeMovimentacoes = { colunas: ColunaDoQuadro[] };

export type FiltroDeMovimentacoes = { filial?: number; busca?: string; levando?: "eu" };

/** `categoria` fica de fora: a API aplica o padrão (`outros`, e `manutencao` na oficina, MOV-04). */
export type NovaParada = { local_id: number; servico: string; valor_previsto_centavos: number; categoria?: CategoriaDaDespesa };

export type NovaMovimentacao = {
  veiculo_id: number;
  paradas: NovaParada[];
  destino_filial_id: number;
  categoria_destino_id: number | null;
  levado_por_id: number;
  sair_agora: boolean;
  /** ISO em UTC; obrigatório e no futuro quando `sair_agora` é falso. */
  agendada_para: string | null;
  vistoria_rapida: boolean;
};

export type ChegadaNoDestino = { km: number; combustivel?: Combustivel; recebido_por_id?: number };

export type NovoLocalDeApoio = { nome: string; tipo: TipoDoLocalDeApoio };

/** `pode.movimentacoes` de GET /api/auth/eu/ (docs/api/contas.md): `gerir` (administrador e gerente), `levar` (vendedor e vistoriador), `nao`. */
export type PodeMovimentacoes = "gerir" | "levar" | "nao";
