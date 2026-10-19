// Tipos do contrato docs/api/veiculos.md. TEMPORÁRIO: sai quando o cliente gerado do OpenAPI existir.
import type { components } from "./schema";

export type StatusVeiculo = "disponivel" | "alugado" | "reservado" | "em_manutencao" | "a_venda" | "indisponivel" | "vendido" | "baixado";
export type TipoVeiculo = "moto" | "carro";

/** Tom decidido pela API para o rótulo de situação. */
export type TomApi = "sucesso" | "info" | "alerta" | "atencao" | "perigo" | "neutro" | "solido";

export type PrecoVigente = { diaria_centavos: number; semanal_centavos: number; mensal_centavos: number; caucao_centavos: number };

/** Blocos da ficha (T-275, "Blocos da ficha" de veiculos.md). Só vêm no detalhe e podem faltar: a tela esconde o que não vier. */
export type PagamentoDaLocacao = {
  situacao: "atrasado" | "vence_hoje" | "em_dia";
  /** Montado pela API ("Parcela 2 atrasada", "Em dia"). */
  rotulo: string;
  conta_id: number | null;
  /** Valor do dia, com multa e juros (FIN-03). */
  valor_centavos: number;
  atrasadas: number;
  cobrar: boolean;
};
export type LocacaoAtualDoVeiculo = {
  id: number;
  codigo: string;
  status: string;
  cliente_nome: string;
  inicio: string;
  fim_previsto: string;
  alerta?: string;
  plano?: { periodicidade: "diaria" | "semanal" | "mensal"; plano_especial: string | null; valor_periodo_centavos?: number };
  pagamento?: PagamentoDaLocacao;
};
export type ProximaManutencao = {
  servico: string;
  km: number;
  faltam_km?: number;
  intervalo_km?: number;
  /** De 0 a 100, com 2 casas, para a barra. */
  progresso_pct?: string;
  dias_estimados?: number | null;
  depois?: { servico: string; km: number; faltam_km: number } | null;
  nota?: string | null;
};
export type PosicaoDaFoto = "frente" | "traseira" | "lado_esquerdo" | "lado_direito" | "painel";
export type VistoriaRecente = {
  id: number;
  tipo: "saida" | "devolucao";
  concluida_em: string;
  vistoriador: { id: number; nome: string } | null;
  locacao_codigo: string | null;
  total_fotos: number;
  fotos: { id: number; posicao: PosicaoDaFoto; url: string; url_expira_em: string }[];
  avarias: { id: number; descricao: string; registrada_em: string; preexistente: boolean; locacao_codigo: string | null; foto_id: number | null }[];
};
export type MovimentacoesDoVeiculo = {
  total: number;
  ultimas: { id: number; codigo: string; status: string; destino_nome: string; paradas: string[]; iniciada_em: string; concluida_em: string | null }[];
  em_andamento: unknown;
};

export type Veiculo = {
  id: number;
  placa: string;
  chassi: string;
  renavam: string | null;
  marca: string;
  modelo: string;
  ano_fabricacao: number;
  ano_modelo: number;
  cor: string;
  tipo_veiculo: TipoVeiculo;
  categoria: { id: number; nome: string };
  filial: { id: number; nome: string };
  status: StatusVeiculo;
  motivo_status: string | null;
  km_atual: number;
  km_atualizado_em: string;
  capacidade_tanque_litros: string | null;
  /** Estes cinco campos vêm ausentes para o vistoriador (D-25, USR-09): a tela esconde o que não vier. */
  preco_vigente?: PrecoVigente;
  valor_venda_centavos?: number | null;
  referencia_fipe_centavos?: number | null;
  valor_compra_centavos?: number | null;
  data_compra?: string | null;
  entrou_na_frota_em: string;
  situacao: { codigo: string; rotulo: string; tom: TomApi };
  locacao_atual: LocacaoAtualDoVeiculo | null;
  manutencao: { proxima: ProximaManutencao | null; os_aberta: { id: number; codigo: string; status: string } | null; alerta?: string } | null;
  documentos_resumo: { pior_situacao: "em_dia" | "vence_em_breve" | "vencido" };
  acoes: {
    editar: boolean;
    colocar_a_venda: boolean;
    voltar_para_frota: boolean;
    bloquear: boolean;
    desbloquear: boolean;
    transferir: boolean;
    baixar: boolean;
    registrar_km: boolean;
    corrigir_km: boolean;
    /** T-275: `movimentar` e o motivo quando for `false`; ausentes até a API mandar. */
    movimentar?: boolean;
    motivo_movimentar?: string | null;
  };
};

export type VeiculoDetalhe = Veiculo & {
  /** Ausente para o vistoriador. */
  indicadores_financeiros?: { rendeu_no_ano_centavos: number; custo_manutencao_ano_centavos: number } | null;
  ocupacao: { pct: string; periodo_dias: number };
  /** Ausente para o financeiro e quando o veículo nunca teve vistoria. */
  vistoria_recente?: VistoriaRecente | null;
  movimentacoes?: MovimentacoesDoVeiculo | null;
  historico_status: { de: StatusVeiculo; para: StatusVeiculo; em: string; origem_codigo: string | null }[];
};

export type ListaVeiculos = {
  contagens: Record<"todos" | "disponivel" | "alugado" | "reservado" | "em_manutencao" | "a_venda" | "indisponivel" | "motos" | "carros", number>;
  resultados: Veiculo[];
  proximo: string | null;
  anterior: string | null;
};

export type FiltroVeiculos = { status?: string; tipo_veiculo?: TipoVeiculo; busca?: string; cursor?: string };

export type DocumentoVeiculo = {
  id: number;
  tipo: string;
  rotulo: string;
  validade: string | null;
  situacao: "em_dia" | "vence_em_breve" | "vencido";
  dias_para_vencer: number | null;
  /** Fora do contrato (só o falso manda): texto da situação de IPVA ("Pago") e rastreador ("Online"). */
  situacao_rotulo?: string;
};

// Listas que vêm dos contratos de locações e manutenção (ainda não escritos): mínimo que a ficha mostra.
export type LocacaoDoVeiculo = { id: number; codigo: string; cliente_nome: string; inicio: string; fim: string; situacao: { rotulo: string; tom: TomApi } };
export type LocacoesDoVeiculo = { total: number; resultados: LocacaoDoVeiculo[] };
export type ManutencaoDoVeiculo = { id: number; servico: string; data: string; km: number; custo_centavos: number };
export type ManutencoesDoVeiculo = { resultados: ManutencaoDoVeiculo[] };

/** Categoria de preço para escolher no cadastro (`GET /api/categorias/`). */
export type CategoriaVeiculo = {
  id: number;
  nome: string;
  tipo_veiculo: TipoVeiculo;
  filial: { id: number; nome: string } | null;
  ativo: boolean;
  preco_vigente: PrecoVigente & { vigente_desde: string };
};

/** Corpo de `POST /api/veiculos/`. Dinheiro em centavos, datas em ISO, placa sem hífen. */
/** POST /api/veiculos/{id}/corrigir-identificacao/ (VEI-01): só o administrador; o motivo é obrigatório. */
export type CorrecaoDeIdentificacao = { placa?: string; chassi?: string; motivo: string };

/** PATCH /api/veiculos/{id}/ (VEI-01): placa, chassi, km e filial não mudam aqui. `null` limpa o campo opcional. */
export type EdicaoVeiculo = {
  renavam?: string | null;
  marca?: string;
  modelo?: string;
  ano_fabricacao?: number;
  ano_modelo?: number;
  cor?: string;
  categoria_id?: number;
  capacidade_tanque_litros?: string | null;
  valor_compra_centavos?: number | null;
  data_compra?: string | null;
};

export type NovoVeiculo = {
  placa: string;
  chassi: string;
  renavam?: string;
  marca: string;
  modelo: string;
  ano_fabricacao: number;
  ano_modelo: number;
  cor: string;
  km_atual: number;
  categoria_id: number;
  filial_id: number;
  capacidade_tanque_litros?: string;
  valor_compra_centavos?: number;
  data_compra?: string;
  entrou_na_frota_em?: string;
  combustivel?: CombustivelDoVeiculo;
};

export type CombustivelDoVeiculo = NonNullable<components["schemas"]["CamposDoCrlv"]["combustivel"]>;

/** Resposta de `POST /api/veiculos/leitura-crlv/` (VEI-08): a API só lê, quem grava é o cadastro. */
export type LeituraCrlv = components["schemas"]["LeituraCrlv"];

/** O CRLV-e que vai junto no cadastro (multipart): o arquivo lido, a validade que a pessoa informa e o comprovante da leitura. */
export type CrlvDoCadastro = { arquivo: File; validade: string; exercicio: number | null; leitura: string };

/** `GET /api/veiculos/modelos/`: o catálogo local. O gerador deu ao tipo o nome dos contratos, por isso ele é escrito aqui. */
export type ModeloDoCatalogo = { marca: string; modelo: string; tipo: TipoVeiculo };
