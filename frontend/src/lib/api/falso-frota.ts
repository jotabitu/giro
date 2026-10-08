// DADOS FALSOS de veículos enquanto a API não existe (contrato: docs/api/veiculos.md).
// Só ./index.ts importa este arquivo. A "API" decide situação, ações e o que cada perfil enxerga.
import { pausa, perfilAtualFalso } from "./falso";
import {
  type DocumentoVeiculo,
  type FiltroVeiculos,
  type ListaVeiculos,
  type LocacaoDoVeiculo,
  type ManutencoesDoVeiculo,
  type StatusVeiculo,
  type TomApi,
  type TipoVeiculo,
  type Veiculo,
  type VeiculoDetalhe,
} from "./tipos-frota";
import { ErroApi } from "./tipos";

const TAMANHO = 8;
const FILIAL = { id: 1, nome: "Filial Centro" };

type Semente = {
  id: number;
  placa: string;
  marca: string;
  modelo: string;
  ano: number;
  cor: string;
  tipo: TipoVeiculo;
  categoria: string;
  status: StatusVeiculo;
  km: number;
  diaria: number;
  semanal: number;
  proximaKm: number;
  servico?: string;
  locacao?: { codigo: string; cliente: string; fim: string; atrasada?: boolean };
  os?: string;
  vendaCentavos?: number;
  chassi: string;
};

const SEMENTES: Semente[] = [
  { id: 501, placa: "QXA4B21", marca: "Honda", modelo: "CG 160 Fan", ano: 2023, cor: "vermelha", tipo: "moto", categoria: "Street 150–160", status: "alugado", km: 18950, diaria: 5490, semanal: 29940, proximaKm: 19900, servico: "Troca de óleo", locacao: { codigo: "LOC-2841", cliente: "Carlos Menezes", fim: "2026-11-04", atrasada: true }, chassi: "9C2KC2210PR004417" },
  { id: 502, placa: "PNB7C04", marca: "Yamaha", modelo: "Factor 150", ano: 2023, cor: "preta", tipo: "moto", categoria: "Street 150–160", status: "alugado", km: 21870, diaria: 5490, semanal: 32900, proximaKm: 25000, locacao: { codigo: "LOC-2843", cliente: "Juliana Rocha", fim: "2026-10-07" }, chassi: "9C6RG3110PR003302" },
  { id: 503, placa: "ROE2A88", marca: "Fiat", modelo: "Mobi Like", ano: 2023, cor: "branco", tipo: "carro", categoria: "Compacto", status: "alugado", km: 38405, diaria: 11900, semanal: 69900, proximaKm: 40000, locacao: { codigo: "LOC-2846", cliente: "Pedro Alencar", fim: "2026-10-08" }, chassi: "9BD341A5JPY887120" },
  { id: 504, placa: "SAK1D39", marca: "Honda", modelo: "CG 160 Fan", ano: 2025, cor: "vermelha", tipo: "moto", categoria: "Street 150–160", status: "disponivel", km: 3120, diaria: 5490, semanal: 32900, proximaKm: 5000, chassi: "9C2KC2210RR004417" },
  { id: 505, placa: "PMZ3E17", marca: "Honda", modelo: "Pop 110i", ano: 2024, cor: "branca", tipo: "moto", categoria: "Urbana 110", status: "em_manutencao", km: 9884, diaria: 3990, semanal: 23900, proximaKm: 10000, os: "OS-0193", chassi: "9C2JC7510RR110233" },
  { id: 506, placa: "RHT9F02", marca: "Renault", modelo: "Kwid Zen", ano: 2022, cor: "cinza", tipo: "carro", categoria: "Compacto", status: "reservado", km: 52310, diaria: 10900, semanal: 64900, proximaKm: 60000, locacao: { codigo: "LOC-2850", cliente: "Aline Duarte", fim: "2026-10-15" }, chassi: "93YRBB005NJ441907" },
  { id: 507, placa: "QYB5H60", marca: "Honda", modelo: "CB 300F Twister", ano: 2024, cor: "azul", tipo: "moto", categoria: "Street 300", status: "a_venda", km: 11045, diaria: 8990, semanal: 52900, proximaKm: 15000, vendaCentavos: 2290000, chassi: "9C2NC5110RR300871" },
  { id: 508, placa: "SBC0J44", marca: "Yamaha", modelo: "NMax 160", ano: 2025, cor: "cinza", tipo: "moto", categoria: "Scooter", status: "alugado", km: 6730, diaria: 6990, semanal: 41900, proximaKm: 10000, locacao: { codigo: "LOC-2852", cliente: "Rafael Sousa", fim: "2026-10-10" }, chassi: "9C6SG5010RR003055" },
  { id: 509, placa: "TAD2K15", marca: "Honda", modelo: "Biz 125", ano: 2024, cor: "vermelha", tipo: "moto", categoria: "Urbana 110", status: "disponivel", km: 7420, diaria: 4490, semanal: 26900, proximaKm: 10000, chassi: "9C2JC4810RR125560" },
  { id: 510, placa: "UEF8L63", marca: "Fiat", modelo: "Argo Drive", ano: 2023, cor: "prata", tipo: "carro", categoria: "Hatch médio", status: "disponivel", km: 29870, diaria: 12900, semanal: 77900, proximaKm: 30000, chassi: "9BD358A5NPY622140" },
];

const ROTULO: Record<string, { rotulo: string; tom: TomApi }> = {
  disponivel: { rotulo: "Disponível", tom: "sucesso" },
  alugado: { rotulo: "Alugado", tom: "solido" },
  reservado: { rotulo: "Reservado", tom: "info" },
  em_manutencao: { rotulo: "Em manutenção", tom: "alerta" },
  a_venda: { rotulo: "À venda", tom: "neutro" },
  indisponivel: { rotulo: "Indisponível", tom: "neutro" },
};

function podeEditar(): boolean {
  const p = perfilAtualFalso();
  return p === "administrador" || p === "gerente";
}

function montar(s: Semente): Veiculo {
  const editar = podeEditar();
  const base = ROTULO[s.status] ?? { rotulo: s.status, tom: "neutro" as TomApi };
  const atrasada = s.locacao?.atrasada === true;
  return {
    id: s.id,
    placa: s.placa,
    chassi: s.chassi,
    renavam: "01289934410",
    marca: s.marca,
    modelo: s.modelo,
    ano_fabricacao: s.ano,
    ano_modelo: s.ano,
    cor: s.cor,
    tipo_veiculo: s.tipo,
    categoria: { id: 2, nome: s.categoria },
    filial: FILIAL,
    status: s.status,
    motivo_status: null,
    km_atual: s.km,
    km_atualizado_em: "2026-10-07T11:00:00Z",
    capacidade_tanque_litros: s.tipo === "moto" ? "16.0" : "47.0",
    preco_vigente: { diaria_centavos: s.diaria, semanal_centavos: s.semanal, mensal_centavos: s.semanal * 4, caucao_centavos: 30000 },
    valor_venda_centavos: s.vendaCentavos ?? null,
    referencia_fipe_centavos: s.vendaCentavos ? 2190000 : null,
    valor_compra_centavos: editar ? 1390000 : null,
    data_compra: editar ? "2023-03-10" : null,
    entrou_na_frota_em: "2023-03-12",
    situacao: atrasada ? { codigo: "atrasado", rotulo: "Atrasado", tom: "perigo" } : { codigo: s.status, ...base },
    locacao_atual: s.locacao
      ? { id: s.id * 10, codigo: s.locacao.codigo, status: atrasada ? "devolucao_atrasada" : "ativa", cliente_nome: s.locacao.cliente, inicio: "2026-09-30", fim_previsto: s.locacao.fim, alerta: atrasada ? "Devolução atrasada" : undefined }
      : null,
    manutencao: {
      proxima: { servico: s.servico ?? "Revisão", km: s.proximaKm },
      os_aberta: s.os ? { id: 193, codigo: s.os, status: "aberta" } : null,
      alerta: s.proximaKm - s.km <= 1000 ? "Revisão próxima" : undefined,
    },
    documentos_resumo: { pior_situacao: s.id === 501 ? "vence_em_breve" : "em_dia" },
    acoes: {
      editar,
      colocar_a_venda: editar && s.status === "disponivel",
      voltar_para_frota: editar && s.status === "a_venda",
      bloquear: editar && s.status === "disponivel",
      desbloquear: false,
      transferir: editar && s.status === "disponivel",
      baixar: perfilAtualFalso() === "administrador" && s.status !== "alugado",
      registrar_km: editar || perfilAtualFalso() === "vistoriador",
      corrigir_km: editar,
    },
  };
}

function normalizar(t: string): string {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export const veiculosFalso = {
  async listar(f: FiltroVeiculos = {}): Promise<ListaVeiculos> {
    await pausa(200);
    const busca = f.busca ? normalizar(f.busca).replace(/-/g, "") : "";
    const doTipo = SEMENTES.filter((s) => (!f.tipo_veiculo || s.tipo === f.tipo_veiculo) && (!busca || normalizar(`${s.placa}${s.modelo}${s.chassi}`).includes(busca)));
    const conta = (st: StatusVeiculo) => doTipo.filter((s) => s.status === st).length;
    const filtrado = f.status && f.status !== "todos" ? doTipo.filter((s) => s.status === f.status) : doTipo;
    const inicio = Number(f.cursor ?? 0);
    const pagina = filtrado.slice(inicio, inicio + TAMANHO);
    return {
      contagens: {
        todos: doTipo.length,
        disponivel: conta("disponivel"),
        alugado: conta("alugado"),
        reservado: conta("reservado"),
        em_manutencao: conta("em_manutencao"),
        a_venda: conta("a_venda"),
        indisponivel: conta("indisponivel"),
        motos: SEMENTES.filter((s) => s.tipo === "moto").length,
        carros: SEMENTES.filter((s) => s.tipo === "carro").length,
      },
      resultados: pagina.map(montar),
      proximo: inicio + TAMANHO < filtrado.length ? String(inicio + TAMANHO) : null,
      anterior: inicio > 0 ? String(Math.max(inicio - TAMANHO, 0)) : null,
    };
  },

  async obter(id: number): Promise<VeiculoDetalhe> {
    await pausa(200);
    const s = SEMENTES.find((x) => x.id === id);
    if (!s) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    const v = montar(s);
    const financeiro = perfilAtualFalso() !== "vendedor" && perfilAtualFalso() !== "vistoriador";
    return {
      ...v,
      indicadores_financeiros: financeiro ? { rendeu_no_ano_centavos: 987000, custo_manutencao_ano_centavos: 35300 } : null,
      ocupacao: { pct: "86.00", periodo_dias: 90 },
      historico_status: [{ de: "disponivel", para: "alugado", em: "2026-09-30T12:00:00Z", origem_codigo: "LOC-2841" }],
    };
  },

  async documentos(id: number): Promise<DocumentoVeiculo[]> {
    await pausa(120);
    if (!SEMENTES.some((x) => x.id === id)) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    return [
      { id: id * 10 + 1, tipo: "crlv", rotulo: "CRLV 2026", validade: "2026-12-31", situacao: "em_dia", dias_para_vencer: 85 },
      { id: id * 10 + 2, tipo: "seguro", rotulo: "Seguro", validade: id === 501 ? "2026-10-25" : "2027-03-10", situacao: id === 501 ? "vence_em_breve" : "em_dia", dias_para_vencer: id === 501 ? 18 : 154 },
    ];
  },

  // Vêm dos contratos de locações e manutenção (`GET /api/locacoes/?veiculo=`, `/api/manutencao/ordens/?veiculo=`).
  async locacoes(id: number): Promise<LocacaoDoVeiculo[]> {
    await pausa(150);
    if (id !== 501) return [];
    return [
      { id: 5010, codigo: "LOC-2841", cliente_nome: "Carlos Menezes", inicio: "2026-09-30", fim: "2026-11-04", situacao: { rotulo: "Em andamento", tom: "info" } },
      { id: 5009, codigo: "LOC-2702", cliente_nome: "Ana Beatriz Lima", inicio: "2026-08-01", fim: "2026-09-29", situacao: { rotulo: "Encerrada", tom: "neutro" } },
      { id: 5008, codigo: "LOC-2640", cliente_nome: "Marcos Viana", inicio: "2026-07-03", fim: "2026-07-31", situacao: { rotulo: "Encerrada", tom: "neutro" } },
    ];
  },

  async manutencoes(id: number): Promise<ManutencoesDoVeiculo> {
    await pausa(150);
    if (id !== 501) return { proxima: null, resultados: [] };
    return {
      proxima: "troca de óleo aos 19.900 km",
      resultados: [
        { id: 1, servico: "Troca de óleo", data: "2026-09-12", km: 17900, custo_centavos: 4800 },
        { id: 2, servico: "Pastilha de freio", data: "2026-07-20", km: 15300, custo_centavos: 9500 },
        { id: 3, servico: "Revisão 15 mil", data: "2026-07-02", km: 15010, custo_centavos: 21000 },
      ],
    };
  },
};
