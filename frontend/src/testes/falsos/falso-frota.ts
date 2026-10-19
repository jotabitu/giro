// DADOS FALSOS de veículos enquanto a API não existe (contrato: docs/api/veiculos.md).
// Só ./index.ts importa este arquivo. A "API" decide situação, ações e o que cada perfil enxerga.
import { pausa, perfilAtualFalso } from "./falso";
import {
  type CategoriaVeiculo,
  type LeituraCrlv,
  type ModeloDoCatalogo,
  type DocumentoVeiculo,
  type FiltroVeiculos,
  type ListaVeiculos,
  type LocacoesDoVeiculo,
  type CorrecaoDeIdentificacao,
  type EdicaoVeiculo,
  type NovoVeiculo,
  type ManutencoesDoVeiculo,
  type StatusVeiculo,
  type TomApi,
  type TipoVeiculo,
  type Veiculo,
  type VeiculoDetalhe,
} from "@/lib/api/tipos-frota";
import { ErroApi } from "@/lib/api/tipos";

const TAMANHO = 8;
const FILIAL = { id: 1, nome: "Filial Centro" };
const FILIAIS = [FILIAL, { id: 2, nome: "Filial Aldeota" }];

/** Limite de veículos do plano (PLT-03). Os testes baixam este valor para provocar o 422. */
let limiteDoPlano = 150;
export const definirLimiteDoPlanoFalso = (n: number) => {
  limiteDoPlano = n;
};

const preco = (diaria: number, semanal: number, caucao = 30000) => ({ vigente_desde: "2026-10-01", diaria_centavos: diaria, semanal_centavos: semanal, mensal_centavos: semanal * 4, caucao_centavos: caucao });
const CATEGORIAS: CategoriaVeiculo[] = [
  { id: 1, nome: "Urbana 110", tipo_veiculo: "moto", filial: null, ativo: true, preco_vigente: preco(3990, 23900) },
  { id: 2, nome: "Street 150–160", tipo_veiculo: "moto", filial: null, ativo: true, preco_vigente: preco(5490, 32900) },
  { id: 3, nome: "Street 300", tipo_veiculo: "moto", filial: null, ativo: true, preco_vigente: preco(8990, 52900, 50000) },
  { id: 4, nome: "Scooter", tipo_veiculo: "moto", filial: { id: 2, nome: "Filial Aldeota" }, ativo: true, preco_vigente: preco(6990, 41900) },
  { id: 5, nome: "Compacto", tipo_veiculo: "carro", filial: null, ativo: true, preco_vigente: preco(11900, 69900, 80000) },
  { id: 6, nome: "Hatch médio", tipo_veiculo: "carro", filial: null, ativo: true, preco_vigente: preco(12900, 77900, 80000) },
];

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
  // Só dos veículos cadastrados pela tela.
  categoriaId?: number;
  filialId?: number;
  renavam?: string;
  anoFabricacao?: number;
  tanque?: string | null;
  compraCentavos?: number | null;
  dataCompra?: string | null;
  entrouEm?: string;
};

const SEMENTES: Semente[] = [
  { id: 501, placa: "QXA4B21", marca: "Honda", modelo: "CG 160 Fan", ano: 2023, cor: "vermelha", tipo: "moto", categoria: "Street 150–160", status: "alugado", km: 18950, diaria: 5490, semanal: 32900, proximaKm: 19900, servico: "Troca de óleo", locacao: { codigo: "LOC-2841", cliente: "Carlos Menezes", fim: "2026-10-28", atrasada: false }, chassi: "9C2KC2210PR004401" },
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

/** D-25, USR-09: o vistoriador recebe a frota sem preço, valor de venda, FIPE, compra nem indicadores. As chaves vêm ausentes, não `null`. */
function semValores<T extends Veiculo>(v: T): T {
  if (perfilAtualFalso() !== "vistoriador") return v;
  const { preco_vigente: _a, valor_venda_centavos: _b, referencia_fipe_centavos: _c, valor_compra_centavos: _d, data_compra: _e, ...resto } = v;
  void [_a, _b, _c, _d, _e];
  if ("indicadores_financeiros" in resto) delete (resto as Partial<VeiculoDetalhe>).indicadores_financeiros;
  return resto as T;
}

function montar(s: Semente): Veiculo {
  return semValores(montarCompleto(s));
}

function montarCompleto(s: Semente): Veiculo {
  const editar = podeEditar();
  const base = ROTULO[s.status] ?? { rotulo: s.status, tom: "neutro" as TomApi };
  const atrasada = s.locacao?.atrasada === true;
  return {
    id: s.id,
    placa: s.placa,
    chassi: s.chassi,
    renavam: s.renavam ?? "01289934410",
    marca: s.marca,
    modelo: s.modelo,
    ano_fabricacao: s.anoFabricacao ?? s.ano,
    ano_modelo: s.ano,
    cor: s.cor,
    tipo_veiculo: s.tipo,
    categoria: { id: s.categoriaId ?? CATEGORIAS.find((c) => c.nome === s.categoria)?.id ?? 2, nome: s.categoria },
    filial: FILIAIS.find((f) => f.id === s.filialId) ?? FILIAL,
    status: s.status,
    motivo_status: null,
    km_atual: s.km,
    km_atualizado_em: s.locacao ? "2026-09-23T12:00:00Z" : "2026-10-07T11:00:00Z",
    capacidade_tanque_litros: s.tanque !== undefined ? s.tanque : s.tipo === "moto" ? "16.0" : "47.0",
    preco_vigente: { diaria_centavos: s.diaria, semanal_centavos: s.semanal, mensal_centavos: s.semanal * 4, caucao_centavos: 30000 },
    valor_venda_centavos: s.vendaCentavos ?? null,
    referencia_fipe_centavos: s.id === 501 ? 1240000 : s.vendaCentavos ? 2190000 : null,
    valor_compra_centavos: editar ? (s.compraCentavos !== undefined ? s.compraCentavos : 1390000) : null,
    data_compra: editar ? (s.dataCompra !== undefined ? s.dataCompra : "2023-03-10") : null,
    entrou_na_frota_em: s.entrouEm ?? "2023-03-12",
    situacao: atrasada ? { codigo: "atrasado", rotulo: "Atrasado", tom: "perigo" } : { codigo: s.status, ...base },
    locacao_atual: s.locacao
      ? { id: s.id * 10, codigo: s.locacao.codigo, status: atrasada ? "devolucao_atrasada" : "ativa", cliente_nome: s.locacao.cliente, inicio: "2026-09-23", fim_previsto: s.locacao.fim, alerta: atrasada ? "Devolução atrasada" : undefined }
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
      // T-275 (MOV-03): só o veículo disponível se movimenta; o alugado diz por quê.
      ...(editar ? { movimentar: s.status === "disponivel", motivo_movimentar: s.status === "alugado" && s.locacao ? `Veículo alugado não se movimenta. O botão volta quando a ${s.locacao.codigo} for devolvida.` : null } : {}),
    },
  };
}

function normalizar(t: string): string {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

const PLACA = /^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$/;
const CHASSI = /^[A-Z0-9]{17}$/;

const CATALOGO: ModeloDoCatalogo[] = [
  { marca: "Honda", modelo: "CG 160 Start", tipo: "moto" },
  { marca: "Honda", modelo: "Pop 110i ES", tipo: "moto" },
  { marca: "Yamaha", modelo: "Factor 150", tipo: "moto" },
  { marca: "Fiat", modelo: "Mobi Like", tipo: "carro" },
];

export const veiculosFalso = {
  async categorias(filtro: { filial?: number; tipo_veiculo?: TipoVeiculo } = {}): Promise<CategoriaVeiculo[]> {
    await pausa(150);
    const lista = CATEGORIAS.filter((c) => c.ativo && (!filtro.tipo_veiculo || c.tipo_veiculo === filtro.tipo_veiculo) && (!filtro.filial || !c.filial || c.filial.id === filtro.filial));
    // O vistoriador lê as categorias sem preço (D-25): a chave vem ausente.
    return perfilAtualFalso() === "vistoriador" ? lista.map((c) => ({ ...c, preco_vigente: undefined }) as unknown as CategoriaVeiculo) : lista;
  },

  /** POST /api/veiculos/ (VEI-01, PLT-03). O veículo entra `disponivel`. */
  async criar(v: NovoVeiculo): Promise<VeiculoDetalhe> {
    await pausa(300);
    if (!podeEditar()) throw new ErroApi(403, "sem_permissao", "Você não tem permissão para cadastrar veículos");
    const placa = v.placa.toUpperCase().replace(/[^A-Z0-9]/g, "");
    const chassi = v.chassi.toUpperCase().replace(/\s/g, "");
    const categoria = CATEGORIAS.find((c) => c.id === v.categoria_id);
    const filial = FILIAIS.find((f) => f.id === v.filial_id);
    const campos: Record<string, string> = {};
    if (!PLACA.test(placa)) campos.placa = "Placa inválida. Use ABC1234 ou ABC1D23";
    if (!CHASSI.test(chassi)) campos.chassi = "O chassi tem 17 letras e números";
    if (!v.marca.trim()) campos.marca = "Informe a marca";
    if (!v.modelo.trim()) campos.modelo = "Informe o modelo";
    if (!v.cor.trim()) campos.cor = "Informe a cor";
    const ano = new Date().getFullYear();
    if (!Number.isInteger(v.ano_fabricacao) || v.ano_fabricacao < 1990 || v.ano_fabricacao > ano + 1) campos.ano_fabricacao = "Ano de fabricação inválido";
    else if (!Number.isInteger(v.ano_modelo) || v.ano_modelo < v.ano_fabricacao || v.ano_modelo > ano + 1) campos.ano_modelo = "O ano do modelo não pode ser menor que o de fabricação";
    if (!Number.isInteger(v.km_atual) || v.km_atual < 0) campos.km_atual = "Informe o km do veículo";
    if (!filial) campos.filial_id = "Escolha a filial";
    if (!categoria) campos.categoria_id = "Escolha a categoria";
    else if (categoria.filial && categoria.filial.id !== v.filial_id) campos.categoria_id = "Esta categoria é de outra filial";
    if (v.renavam && !/^\d{9,11}$/.test(v.renavam)) campos.renavam = "Renavam deve ter de 9 a 11 números";
    if (Object.keys(campos).length > 0 || !categoria) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, campos);
    // Qualquer estado conta, inclusive vendido e baixado (VEI-01); o seed não tem esses dois.
    const mesma = SEMENTES.find((s) => s.placa === placa);
    if (mesma) throw new ErroApi(409, "VEI-01", "Já existe um veículo com esta placa", { campo: "placa", veiculo_id: mesma.id });
    const mesmoChassi = SEMENTES.find((s) => s.chassi === chassi);
    if (mesmoChassi) throw new ErroApi(409, "VEI-01", "Já existe um veículo com este chassi", { campo: "chassi", veiculo_id: mesmoChassi.id });
    if (SEMENTES.length >= limiteDoPlano) throw new ErroApi(422, "PLT-03", "Seu plano chegou ao limite de veículos. Fale com o administrador para mudar de plano.");
    const s: Semente = {
      id: Math.max(...SEMENTES.map((x) => x.id)) + 1,
      placa,
      marca: v.marca.trim(),
      modelo: v.modelo.trim(),
      ano: v.ano_modelo,
      anoFabricacao: v.ano_fabricacao,
      cor: v.cor.trim().toLowerCase(),
      tipo: categoria.tipo_veiculo,
      categoria: categoria.nome,
      categoriaId: categoria.id,
      filialId: v.filial_id,
      status: "disponivel",
      km: v.km_atual,
      diaria: categoria.preco_vigente.diaria_centavos,
      semanal: categoria.preco_vigente.semanal_centavos,
      proximaKm: v.km_atual + 1000,
      chassi,
      renavam: v.renavam,
      tanque: v.capacidade_tanque_litros ?? null,
      compraCentavos: v.valor_compra_centavos ?? null,
      dataCompra: v.data_compra ?? null,
      entrouEm: v.entrou_na_frota_em ?? new Date().toISOString().slice(0, 10),
    };
    SEMENTES.push(s);
    return veiculosFalso.obter(s.id);
  },

  /** POST /api/veiculos/leitura-crlv/ (VEI-08): lê só o que o PDF de exemplo traz; qualquer outro arquivo é a recusa 422 de sempre. */
  async lerCrlv(arquivo: File): Promise<LeituraCrlv> {
    await pausa(400);
    if (!podeEditar()) throw new ErroApi(403, "permissao", "Você não tem permissão para cadastrar veículos");
    if (!/.pdf$/i.test(arquivo.name)) throw new ErroApi(400, "validacao", "Confira o arquivo", undefined, { arquivo: "Envie o PDF do CRLV-e." });
    if (!/crlv/i.test(arquivo.name)) throw new ErroApi(422, "VEI-08", "Não conseguimos ler este documento. Preencha os campos à mão.");
    return {
      documento: "crlv",
      campos: { placa: "TBC5H21", chassi: "9C2JC7500TR012345", renavam: "01234567890", marca: "Honda", modelo: "Pop 110i ES", ano_fabricacao: 2026, ano_modelo: 2026, cor: "vermelha", combustivel: "gasolina" },
      lidos: ["placa", "chassi", "renavam", "marca", "modelo", "ano_fabricacao", "ano_modelo", "cor", "combustivel"],
      quantidade: 9,
      rotulo: "CRLV-e lido · 9 campos preenchidos",
      exercicio: 2026,
      dicas: { marca_modelo: null },
      leitura: "comprovante-de-exemplo",
    };
  },

  /** GET /api/veiculos/modelos/: o catálogo local. */
  async modelos(filtro: { tipo?: TipoVeiculo; marca?: string; busca?: string } = {}): Promise<ModeloDoCatalogo[]> {
    await pausa(100);
    const norma = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    return CATALOGO.filter((m) => (!filtro.tipo || m.tipo === filtro.tipo) && (!filtro.marca || norma(m.marca) === norma(filtro.marca)) && (!filtro.busca || norma(filtro.busca).split(/s+/).every((p) => norma(`${m.marca} ${m.modelo}`).includes(p))));
  },

  /** POST /api/veiculos/{id}/corrigir-identificacao/ (VEI-01): só o administrador; placa e chassi únicos, chassi com 17 caracteres. */
  async corrigirIdentificacao(id: number, c: CorrecaoDeIdentificacao): Promise<VeiculoDetalhe> {
    await pausa(200);
    if (perfilAtualFalso() !== "administrador") throw new ErroApi(403, "sem_permissao", "Só o administrador corrige placa ou chassi");
    const s = SEMENTES.find((x) => x.id === id);
    if (!s) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    const campos: Record<string, string> = {};
    if (!c.motivo.trim()) campos.motivo = "Informe o motivo da correção";
    if (c.placa === undefined && c.chassi === undefined) campos.placa = "Informe a placa ou o chassi corrigido";
    const placa = c.placa?.replace(/[\s-]/g, "").toUpperCase();
    const chassi = c.chassi?.replace(/\s/g, "").toUpperCase();
    if (placa !== undefined && !/^[A-Z]{3}\d[A-Z0-9]\d{2}$/.test(placa)) campos.placa = "Placa inválida";
    if (chassi !== undefined && chassi.length !== 17) campos.chassi = "O chassi tem 17 caracteres";
    if (Object.keys(campos).length > 0) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, campos);
    const outraPlaca = placa !== undefined ? SEMENTES.find((x) => x.id !== id && x.placa === placa) : undefined;
    if (outraPlaca) throw new ErroApi(409, "VEI-01", "Já existe um veículo com esta placa", { campo: "placa", veiculo_id: outraPlaca.id });
    const outroChassi = chassi !== undefined ? SEMENTES.find((x) => x.id !== id && x.chassi === chassi) : undefined;
    if (outroChassi) throw new ErroApi(409, "VEI-01", "Já existe um veículo com este chassi", { campo: "chassi", veiculo_id: outroChassi.id });
    if (placa !== undefined) s.placa = placa;
    if (chassi !== undefined) s.chassi = chassi;
    return veiculosFalso.obter(id);
  },

  /** PATCH /api/veiculos/{id}/ (VEI-01): administrador e gerente; placa, chassi, km e filial não mudam por aqui. */
  async atualizar(id: number, v: EdicaoVeiculo): Promise<VeiculoDetalhe> {
    await pausa(300);
    if (!podeEditar()) throw new ErroApi(403, "sem_permissao", "Você não tem permissão para editar veículos");
    const s = SEMENTES.find((x) => x.id === id);
    if (!s) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    const campos: Record<string, string> = {};
    if (v.marca !== undefined && !v.marca.trim()) campos.marca = "Informe a marca";
    if (v.modelo !== undefined && !v.modelo.trim()) campos.modelo = "Informe o modelo";
    if (v.cor !== undefined && !v.cor.trim()) campos.cor = "Informe a cor";
    const ano = new Date().getFullYear();
    const fabricacao = v.ano_fabricacao ?? s.anoFabricacao ?? s.ano;
    const modelo = v.ano_modelo ?? s.ano;
    if (v.ano_fabricacao !== undefined && (!Number.isInteger(fabricacao) || fabricacao < 1990 || fabricacao > ano + 1)) campos.ano_fabricacao = "Ano de fabricação inválido";
    else if (v.ano_modelo !== undefined && (!Number.isInteger(modelo) || modelo < fabricacao || modelo > ano + 1)) campos.ano_modelo = "O ano do modelo não pode ser menor que o de fabricação";
    if (v.renavam && !/^\d{9,11}$/.test(v.renavam)) campos.renavam = "Renavam deve ter de 9 a 11 números";
    const categoria = v.categoria_id !== undefined ? CATEGORIAS.find((c) => c.id === v.categoria_id) : undefined;
    if (v.categoria_id !== undefined) {
      if (!categoria) campos.categoria_id = "Escolha a categoria";
      else if (categoria.tipo_veiculo !== s.tipo) campos.categoria_id = "Esta categoria é de outro tipo de veículo";
      else if (categoria.filial && categoria.filial.id !== (s.filialId ?? 1)) campos.categoria_id = "Esta categoria é de outra filial";
    }
    if (Object.keys(campos).length > 0) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, campos);
    if (v.marca !== undefined) s.marca = v.marca.trim();
    if (v.modelo !== undefined) s.modelo = v.modelo.trim();
    if (v.ano_fabricacao !== undefined) s.anoFabricacao = v.ano_fabricacao;
    if (v.ano_modelo !== undefined) s.ano = v.ano_modelo;
    if (v.cor !== undefined) s.cor = v.cor.trim().toLowerCase();
    if (categoria) {
      s.categoriaId = categoria.id;
      s.categoria = categoria.nome;
    }
    if (v.renavam !== undefined) s.renavam = v.renavam ?? undefined;
    if (v.capacidade_tanque_litros !== undefined) s.tanque = v.capacidade_tanque_litros;
    if (v.valor_compra_centavos !== undefined) s.compraCentavos = v.valor_compra_centavos;
    if (v.data_compra !== undefined) s.dataCompra = v.data_compra;
    return veiculosFalso.obter(id);
  },

  /** POST /api/veiculos/{id}/km/ (VEI-02): o km só sobe. */
  async registrarKm(id: number, novoKm: number): Promise<Veiculo> {
    await pausa(200);
    const s = SEMENTES.find((x) => x.id === id);
    if (!s) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    if (novoKm < s.km) {
      const atual = new Intl.NumberFormat("pt-BR").format(s.km);
      throw new ErroApi(422, "VEI-01", `O km informado é menor que o atual (${atual}). Para corrigir, use Corrigir km.`, { km_atual: s.km });
    }
    s.km = novoKm;
    return montar(s);
  },

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
    const detalhe: VeiculoDetalhe = {
      ...v,
      // T-156, USR-09: vendedor e vistoriador recebem a ficha sem a chave (ausente, não `null`).
      ...(financeiro ? { indicadores_financeiros: { rendeu_no_ano_centavos: 987000, custo_manutencao_ano_centavos: 35300 } } : {}),
      ocupacao: { pct: "86.00", periodo_dias: 90 },
      historico_status: [{ de: "disponivel", para: "alugado", em: "2026-09-23T12:00:00Z", origem_codigo: "LOC-2841" }],
    };
    return semValores(detalhe);
  },

  async documentos(id: number): Promise<DocumentoVeiculo[]> {
    await pausa(120);
    if (!SEMENTES.some((x) => x.id === id)) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    const seguroVence = id === 501;
    return [
      { id: id * 10 + 1, tipo: "crlv", rotulo: "CRLV 2026", validade: "2026-12-31", situacao: "em_dia", dias_para_vencer: 85 },
      // IPVA e rastreador ainda não são tipos do contrato (VEI-03: CRLV e seguro). O texto da situação é do falso.
      { id: id * 10 + 3, tipo: "ipva", rotulo: "IPVA 2026", validade: null, situacao: "em_dia", dias_para_vencer: null, situacao_rotulo: "Pago" },
      { id: id * 10 + 2, tipo: "seguro", rotulo: "Seguro", validade: seguroVence ? "2026-10-25" : "2027-03-10", situacao: seguroVence ? "vence_em_breve" : "em_dia", dias_para_vencer: seguroVence ? 18 : 154 },
      { id: id * 10 + 4, tipo: "rastreador", rotulo: "Rastreador", validade: null, situacao: "em_dia", dias_para_vencer: null, situacao_rotulo: "Online" },
    ];
  },

  // Vêm dos contratos de locações e manutenção (`GET /api/locacoes/?veiculo=`, `/api/manutencao/ordens/?veiculo=`).
  // `total` não existe no contrato de locações ainda: a ficha mostra "14 no total" e as 3 mais recentes.
  async locacoes(id: number): Promise<LocacoesDoVeiculo> {
    await pausa(150);
    if (id !== 501) return { total: 0, resultados: [] };
    return {
      total: 14,
      resultados: [
        { id: 5010, codigo: "LOC-2841", cliente_nome: "Carlos Menezes", inicio: "2026-09-23", fim: "2026-10-28", situacao: { rotulo: "Em andamento", tom: "info" } },
        { id: 5009, codigo: "LOC-2702", cliente_nome: "Ana Beatriz Lima", inicio: "2026-08-01", fim: "2026-09-22", situacao: { rotulo: "Encerrada", tom: "neutro" } },
        { id: 5008, codigo: "LOC-2640", cliente_nome: "Marcos Viana", inicio: "2026-07-03", fim: "2026-07-31", situacao: { rotulo: "Encerrada", tom: "neutro" } },
      ],
    };
  },

  async manutencoes(id: number): Promise<ManutencoesDoVeiculo> {
    await pausa(150);
    if (id !== 501) return { resultados: [] };
    return {
      resultados: [
        { id: 1, servico: "Troca de óleo", data: "2026-09-12", km: 18900, custo_centavos: 4800 },
        { id: 2, servico: "Pastilha de freio", data: "2026-07-20", km: 15300, custo_centavos: 9500 },
        { id: 3, servico: "Revisão 15 mil", data: "2026-07-02", km: 15010, custo_centavos: 21000 },
      ],
    };
  },
};
