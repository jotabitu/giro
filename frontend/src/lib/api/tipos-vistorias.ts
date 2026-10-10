// Tipos de vistorias, devolução e acerto, a partir do cliente gerado do OpenAPI (src/lib/api/schema.d.ts, `npm run api:gerar`).
// O gerador deixa alguns campos como `string`; aqui eles ganham os valores fechados do contrato (docs/api/vistorias.md).
import type { components } from "./schema";
import type { TomApi } from "./tipos-frota";

type S = components["schemas"];

export type TipoVistoria = "saida" | "devolucao";
export type StatusVistoria = "rascunho" | "concluida";
export type Combustivel = "reserva" | "um_quarto" | "meio" | "tres_quartos" | "cheio";
export type PosicaoFoto = S["Foto"]["posicao"];
export type FormaDevolucaoAcerto = S["FormaDevolucaoAcertoEnum"];
export type TipoItemAcerto = S["ItemAcertoEntradaTipoEnum"];

export type FotoDaVistoria = S["Foto"];
export type ItemDaVistoria = S["ItemVistoria"];
export type AvariaDaVistoria = S["Avaria"];

export type Vistoria = Omit<S["Vistoria"], "tipo" | "status" | "combustivel" | "pendencias"> & {
  tipo: TipoVistoria;
  status: StatusVistoria;
  combustivel: Combustivel | null;
  pendencias: string[];
};

export type EdicaoDaVistoria = { km?: number | null; combustivel?: Combustivel | null; itens?: { codigo: string; ok: boolean | null; observacao?: string | null }[]; observacoes?: string | null };
export type NovaAvaria = { descricao: string; foto_id: number; vai_para_oficina?: boolean; valor_centavos?: number | null };

export type PendenciaDaVistoria = { codigo: string; mensagem: string; [chave: string]: unknown };

export type ItemDoAcerto = Omit<S["ItemAcerto"], "tipo" | "modo"> & { tipo: TipoItemAcerto; modo: "calculado" | "informado"; natureza?: "cobranca" | "credito" };
export type AcertoDaDevolucao = Omit<S["Acerto"], "status" | "itens" | "creditos" | "resultado" | "forma_devolucao"> & {
  status: "rascunho" | "concluido";
  itens: ItemDoAcerto[];
  creditos: ItemDoAcerto[];
  resultado: { tipo: "devolver" | "cobrar" | "zerado"; valor_centavos: number; texto: string; botao: string };
  forma_devolucao: FormaDevolucaoAcerto | null;
};

export type DevolucaoCompleta = Omit<S["Devolucao"], "status" | "vistoria" | "acerto"> & {
  status: "rascunho" | "concluida";
  vistoria: Vistoria;
  /** Ausente para o vistoriador. */
  acerto?: AcertoDaDevolucao;
};

export type NovoItemDoAcerto = { tipo: "avaria" | "multa_transito"; descricao: string; valor_centavos: number };

export type ItemDaAgenda = {
  id: string;
  tipo: TipoVistoria;
  horario: string;
  veiculo: { id: number; placa: string; modelo: string };
  cliente: { nome: string };
  locacao: { id: number; codigo: string };
  situacao: { codigo: string; rotulo: string; tom: TomApi };
  vistoria_id: number | null;
  acao: { codigo: "iniciar" | "continuar" | "abrir"; rotulo: string };
};
export type DiaDaAgenda = "hoje" | "amanha" | "semana";
export type AgendaDoDia = { resumo: string; proxima: { item_id: string; em_minutos: number } | null; avarias_abertas: number; resultados: ItemDaAgenda[] };
export type AvariaAberta = Omit<S["AvariaAberta"], "foto"> & { foto: S["Foto"] | null };
