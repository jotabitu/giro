import type { Combustivel, PodeMovimentacoes, PosicaoDaFotoDaChegada, StatusDaMovimentacao, TipoDoLocalDeApoio } from "@/lib/api";

// Textos fixos das Movimentações (T-289, docs/api/movimentacoes.md). Estado, ações, rota e resumo vêm prontos da API.

export const ROTULO_DO_TIPO_DE_LOCAL: Record<TipoDoLocalDeApoio, string> = { lava_jato: "lava-jato", oficina: "oficina", despachante: "despachante", outro: "outro" };

export const TIPOS_DE_LOCAL: { valor: TipoDoLocalDeApoio; rotulo: string }[] = [
  { valor: "lava_jato", rotulo: "Lava-jato" },
  { valor: "oficina", rotulo: "Oficina" },
  { valor: "despachante", rotulo: "Despachante" },
  { valor: "outro", rotulo: "Outro" },
];

/** Ponto de cor de cada coluna do quadro (tokens do design system). */
export const COR_DA_COLUNA: Record<Exclude<StatusDaMovimentacao, "cancelada">, string> = {
  agendada: "bg-ink-muted",
  em_transito: "bg-info",
  no_local: "bg-warning",
  concluida: "bg-success",
};

export const MENSAGEM_DA_COLUNA_VAZIA: Record<Exclude<StatusDaMovimentacao, "cancelada">, string> = {
  agendada: "Nenhuma movimentação agendada.",
  em_transito: "Nenhum veículo em trânsito.",
  no_local: "Nenhum veículo em local de apoio.",
  concluida: "Nenhuma movimentação concluída hoje.",
};

export const POSICOES_DA_CHEGADA: { valor: PosicaoDaFotoDaChegada; rotulo: string }[] = [
  { valor: "frente", rotulo: "Frente" },
  { valor: "traseira", rotulo: "Traseira" },
  { valor: "lado_esquerdo", rotulo: "Esquerda" },
  { valor: "lado_direito", rotulo: "Direita" },
];

export const COMBUSTIVEIS_DA_CHEGADA: { valor: Combustivel; rotulo: string }[] = [
  { valor: "reserva", rotulo: "Res." },
  { valor: "um_quarto", rotulo: "1/4" },
  { valor: "meio", rotulo: "1/2" },
  { valor: "tres_quartos", rotulo: "3/4" },
  { valor: "cheio", rotulo: "Cheio" },
];

/** "MOV-0002" na URL de chegada: a rota usa o id. */
export const rotaDaChegada = (id: number) => `/veiculos/movimentacoes/${id}/chegada`;
export const ROTA_DAS_MOVIMENTACOES = "/veiculos/movimentacoes";
export const ROTA_DA_NOVA_MOVIMENTACAO = "/veiculos/movimentacoes/nova";

/** Quem cria e agenda: `pode.movimentacoes` = `gerir` (docs/api/contas.md). Provisório até o OpenAPI trazer o campo em `Pode`. */
export const podeGerirMovimentacoes = (eu: { pode: object }): boolean => (eu.pode as { movimentacoes?: PodeMovimentacoes }).movimentacoes === "gerir";
