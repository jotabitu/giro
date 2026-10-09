// Tipos do contrato docs/api/veiculos.md. TEMPORÁRIO: sai quando o cliente gerado do OpenAPI existir.

export type StatusVeiculo = "disponivel" | "alugado" | "reservado" | "em_manutencao" | "a_venda" | "indisponivel" | "vendido" | "baixado";
export type TipoVeiculo = "moto" | "carro";

/** Tom decidido pela API para o rótulo de situação. */
export type TomApi = "sucesso" | "info" | "alerta" | "atencao" | "perigo" | "neutro" | "solido";

export type PrecoVigente = { diaria_centavos: number; semanal_centavos: number; mensal_centavos: number; caucao_centavos: number };

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
  preco_vigente: PrecoVigente;
  valor_venda_centavos: number | null;
  referencia_fipe_centavos: number | null;
  valor_compra_centavos: number | null;
  data_compra: string | null;
  entrou_na_frota_em: string;
  situacao: { codigo: string; rotulo: string; tom: TomApi };
  locacao_atual: { id: number; codigo: string; status: string; cliente_nome: string; inicio: string; fim_previsto: string; alerta?: string } | null;
  manutencao: { proxima: { servico: string; km: number } | null; os_aberta: { id: number; codigo: string; status: string } | null; alerta?: string } | null;
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
  };
};

export type VeiculoDetalhe = Veiculo & {
  indicadores_financeiros: { rendeu_no_ano_centavos: number; custo_manutencao_ano_centavos: number } | null;
  ocupacao: { pct: string; periodo_dias: number };
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
};

// Listas que vêm dos contratos de locações e manutenção (ainda não escritos): mínimo que a ficha mostra.
export type LocacaoDoVeiculo = { id: number; codigo: string; cliente_nome: string; inicio: string; fim: string; situacao: { rotulo: string; tom: TomApi } };
export type ManutencaoDoVeiculo = { id: number; servico: string; data: string; km: number; custo_centavos: number };
export type ManutencoesDoVeiculo = { proxima: string | null; resultados: ManutencaoDoVeiculo[] };

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
};
