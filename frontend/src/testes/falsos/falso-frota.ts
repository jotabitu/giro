// DADOS FALSOS de veículos enquanto a API não existe (contrato: docs/api/veiculos.md).
// Só ./index.ts importa este arquivo. A "API" decide situação, ações e o que cada perfil enxerga.
import { pausa, perfilAtualFalso } from "./falso";
import {
  type GaleriaDoEditar,
  type GaleriaDoVeiculo,
  type CategoriaVeiculo,
  type CombustivelDoVeiculo,
  type DocumentoDoVeiculo,
  type LeituraCrlvNoEditar,
  type RastreadorDoVeiculo,
  type LeituraCrlv,
  type ModeloDoCatalogo,
  type DocumentoVeiculo,
  type NovoDocumentoVeiculo,
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
  // VEI-09: o documento guarda tudo; `blocosDoDocumento` tira o motor e as observações de quem não os vê.
  combustivel?: CombustivelDoVeiculo | null;
  documento?: DocumentoDoVeiculo;
  rastreador?: RastreadorDoVeiculo;
  anotacoes?: string | null;
};

const DOCUMENTO_VAZIO: DocumentoDoVeiculo = { potencia_cv: null, cilindrada_cc: null, especie: null, tipo: null, carroceria: null, lotacao: null, peso_bruto_kg: null, numero_motor: null, observacoes: null };

const SEMENTES: Semente[] = [
  { id: 501, placa: "QXA4B21", marca: "Honda", modelo: "CG 160 Fan", ano: 2023, cor: "vermelha", tipo: "moto", categoria: "Street 150–160", status: "alugado", km: 18950, diaria: 5490, semanal: 32900, proximaKm: 19900, servico: "Troca de óleo", locacao: { codigo: "LOC-2841", cliente: "Carlos Menezes", fim: "2026-10-28", atrasada: false }, chassi: "9C2KC2210PR004401",
    // Caso "Dados do CRLV-e do QXA-4B21" das regras (VEI-09).
    combustivel: "flex",
    documento: { potencia_cv: 15, cilindrada_cc: 162, especie: "passageiro", tipo: "Motocicleta", carroceria: null, lotacao: 2, peso_bruto_kg: 290, numero_motor: "KC22E1P004401", observacoes: "ALIENACAO FIDUCIARIA" },
    rastreador: { numero: "356938035643809", empresa: "Rastreia Fácil" },
    anotacoes: "Risco no tanque, lado esquerdo" },
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

// VEI-10 (T-414): a galeria de cada veículo na memória. O QXA-4B21 tem 3 fotos; os outros nascem sem foto.
type FotoGuardada = { id: number; capa: boolean; nome: string };
const GALERIAS = new Map<number, FotoGuardada[]>([[501, [{ id: 7002, capa: true, nome: "moto-1.jpg" }, { id: 7001, capa: false, nome: "moto-2.jpg" }, { id: 7003, capa: false, nome: "moto-3.jpg" }]]]);
let proximaFotoDaGaleria = 7100;
const LIMITE_DE_FOTOS = 20;
const MSG_FOTO = "Envie uma foto JPG ou PNG de até 10 MB.";

function fotosDe(id: number): FotoGuardada[] {
  const l = GALERIAS.get(id) ?? [];
  GALERIAS.set(id, l);
  return l;
}

/** Os links só vêm para quem a API manda; aqui o falso manda sempre, menos nulos de propósito nos testes. */
function galeriaDoFalso(id: number, motivo: string | null = null): GaleriaDoVeiculo & { editar: boolean; motivo: string | null } {
  const s = SEMENTES.find((x) => x.id === id);
  const placa = s ? `${s.placa.slice(0, 3)}-${s.placa.slice(3)}` : "";
  const ordem = [...fotosDe(id)].sort((a, b) => Number(b.capa) - Number(a.capa));
  const editar = podeEditar() && s?.status !== "vendido" && s?.status !== "baixado";
  return {
    total: ordem.length,
    limite: LIMITE_DE_FOTOS,
    editar,
    motivo,
    fotos: ordem.map((f, i) => ({
      id: f.id,
      numero: i + 1,
      rotulo: null,
      capa: f.capa,
      url: `/fotos/${f.id}.jpg`,
      url_download: `/fotos/${f.id}.jpg?download=1`,
      url_expira_em: "2099-01-01T00:00:00Z",
      nome_arquivo: `${placa}-galeria-${i + 1}.${f.nome.toLowerCase().endsWith(".png") ? "png" : "jpg"}`,
      enviada_em: "2026-10-07T13:02:00Z",
      enviada_por: { id: 1, nome: "Mariana Costa" },
    })),
  };
}

function exigirEdicaoDeFotos(id: number) {
  const s = SEMENTES.find((x) => x.id === id);
  if (!s) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
  if (!podeEditar()) throw new ErroApi(403, "sem_permissao", "Você não tem permissão para mudar as fotos.");
  if (s.status === "vendido" || s.status === "baixado") throw new ErroApi(409, "VEI-10", `A galeria de veículo ${s.status} fica só para ver.`);
}

function exigirFotoValida(arquivo: File) {
  const ok = /\.(jpe?g|png)$/i.test(arquivo.name) && arquivo.size <= 10 * 1024 * 1024;
  if (!ok) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { arquivo: MSG_FOTO });
}

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

/** VEI-09: `numero_motor` e `observacoes` só para administrador e gerente; para os outros as chaves vêm ausentes (CA-421-12). */
function blocosDoDocumento(s: Semente): Pick<VeiculoDetalhe, "combustivel" | "documento" | "rastreador" | "anotacoes"> {
  const { numero_motor, observacoes, ...aberto } = { ...DOCUMENTO_VAZIO, ...s.documento };
  return {
    combustivel: s.combustivel ?? null,
    documento: podeEditar() ? { ...aberto, numero_motor, observacoes } : aberto,
    rastreador: s.rastreador ?? { numero: null, empresa: null },
    anotacoes: s.anotacoes ?? null,
  };
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
    situacao: atrasada ? { codigo: "atrasado", rotulo: "Atrasado", tom: "perigo" } : s.status === "reservado" && s.locacao ? { codigo: "reservado", rotulo: `Reservado na ${s.locacao.codigo}`, tom: base.tom } : { codigo: s.status, ...base },
    reserva: s.status === "reservado" && s.locacao ? { locacao_id: s.id * 10, codigo: s.locacao.codigo, motivo: "locacao" } : null,
    locacao_atual: s.locacao
      ? { id: s.id * 10, codigo: s.locacao.codigo, status: atrasada ? "devolucao_atrasada" : "ativa", cliente_nome: s.locacao.cliente, inicio: "2026-09-23", fim_previsto: s.locacao.fim, alerta: atrasada ? { codigo: "atrasado", rotulo: "Atrasado", tom: "perigo" } : undefined }
      : null,
    manutencao: {
      proxima: { servico: s.servico ?? "Revisão", km: s.proximaKm },
      os_aberta: s.os ? { id: 193, codigo: s.os, status: "aberta" } : null,
      alerta: s.proximaKm - s.km <= 1000 ? { codigo: "revisao_proxima", rotulo: "Revisão próxima", tom: "alerta" } : undefined,
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
      motivo_trocar_tipo: editar ? motivoDeNaoTrocarTipo(s) : null,
      editar_fotos: editar && s.status !== "vendido" && s.status !== "baixado",
    },
  };
}

/** VEI-11: reservado ou alugado, o tipo não muda (a frase do 409 `tipo_com_locacao_aberta`). */
function motivoDeNaoTrocarTipo(s: Semente): string | null {
  if (s.status !== "alugado" && s.status !== "reservado") return null;
  return s.locacao ? `Este veículo está na ${s.locacao.codigo}. Troque o tipo depois da devolução.` : "Este veículo está numa locação aberta. Troque o tipo depois da devolução.";
}

function normalizar(t: string): string {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

type CorpoVei09 = { combustivel?: CombustivelDoVeiculo | null; documento?: Partial<Record<keyof DocumentoDoVeiculo, unknown>>; rastreador?: { numero?: unknown; empresa?: unknown }; anotacoes?: string | null };

/** VEI-09: formatos e mensagens do contrato (docs/api/veiculos.md), com a chave pontuada no erro 400. */
function validarVei09(v: CorpoVei09): Record<string, string> {
  const erros: Record<string, string> = {};
  const inteiro = (chave: string, valor: unknown, min: number, max: number, mensagem: string) => {
    if (valor === undefined || valor === null || valor === "") return;
    if (typeof valor !== "number" || !Number.isInteger(valor) || valor < min || valor > max) erros[chave] = mensagem;
  };
  const texto = (chave: string, valor: unknown, max: number, mensagem = `Use até ${max} caracteres.`, so?: RegExp) => {
    if (valor === undefined || valor === null) return;
    const t = String(valor).trim();
    if (t.length > max || (so && t && !so.test(t))) erros[chave] = mensagem;
  };
  const d = v.documento ?? {};
  inteiro("documento.potencia_cv", d.potencia_cv, 1, 999, "Informe a potência em cv, de 1 a 999.");
  inteiro("documento.cilindrada_cc", d.cilindrada_cc, 1, 9999, "Informe a cilindrada em cc, de 1 a 9999.");
  inteiro("documento.lotacao", d.lotacao, 1, 99, "Informe a lotação em pessoas, de 1 a 99.");
  inteiro("documento.peso_bruto_kg", d.peso_bruto_kg, 1, 99999, "Informe o peso bruto em kg.");
  if (d.especie && !["passageiro", "carga", "misto", "competicao", "tracao", "especial", "colecao"].includes(String(d.especie))) erros["documento.especie"] = "Escolha a espécie da lista.";
  texto("documento.tipo", d.tipo, 30);
  texto("documento.carroceria", d.carroceria, 30);
  texto("documento.numero_motor", d.numero_motor, 21, "Use só letras e números, até 21.", /^[A-Za-z0-9]+$/);
  texto("documento.observacoes", d.observacoes, 500);
  texto("rastreador.numero", v.rastreador?.numero, 20, "Use só letras e números, até 20.", /^[A-Za-z0-9]+$/);
  texto("rastreador.empresa", v.rastreador?.empresa, 60);
  texto("anotacoes", v.anotacoes, 500);
  return erros;
}

const vazioParaNulo = <T>(valor: T): T | null => (valor === "" || valor === undefined ? null : valor);

/** Chave enviada substitui, ausente não muda, `null` e `""` apagam (VEI-09). */
function gravarVei09(s: Semente, v: CorpoVei09): void {
  if (v.combustivel !== undefined) s.combustivel = v.combustivel || null;
  if (v.documento) {
    const atual = { ...DOCUMENTO_VAZIO, ...s.documento };
    for (const [chave, valor] of Object.entries(v.documento)) {
      const texto = typeof valor === "string" ? valor.trim() : valor;
      (atual as Record<string, unknown>)[chave] = chave === "numero_motor" && typeof texto === "string" ? vazioParaNulo(texto.toUpperCase()) : vazioParaNulo(texto);
    }
    s.documento = atual;
  }
  if (v.rastreador) {
    const atual = { numero: null, empresa: null, ...s.rastreador };
    if (v.rastreador.numero !== undefined) atual.numero = vazioParaNulo(String(v.rastreador.numero ?? "").trim().toUpperCase()) as string | null;
    if (v.rastreador.empresa !== undefined) atual.empresa = vazioParaNulo(String(v.rastreador.empresa ?? "").trim()) as string | null;
    s.rastreador = atual;
  }
  if (v.anotacoes !== undefined) s.anotacoes = vazioParaNulo(v.anotacoes?.trim() ?? null);
}

/** Campos que o CRLV-e de exemplo (crlv-tbc5h21.pdf) traz além dos 9 de antes: 16 no total (CA-421-01). */
const CAMPOS_DO_TBC5H21 = { "documento.potencia_cv": 8, "documento.cilindrada_cc": 109, "documento.especie": "passageiro", "documento.tipo": "Motocicleta", "documento.carroceria": null, "documento.lotacao": 2, "documento.peso_bruto_kg": 240, "documento.numero_motor": "JC75E1S123456", "documento.observacoes": null } as const;
const CAMPOS_DA_VEI_09_VAZIOS = { "documento.potencia_cv": null, "documento.cilindrada_cc": null, "documento.especie": null, "documento.tipo": null, "documento.carroceria": null, "documento.lotacao": null, "documento.peso_bruto_kg": null, "documento.numero_motor": null, "documento.observacoes": null } as const;
const lidosDe = (campos: Record<string, unknown>) => Object.keys(campos).filter((k) => campos[k] !== null);

const PLACA = /^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$/;
const CHASSI = /^[A-Z0-9]{17}$/;

const CATALOGO: ModeloDoCatalogo[] = [
  { marca: "Honda", modelo: "CG 160 Start", tipo: "moto" },
  { marca: "Honda", modelo: "Pop 110i ES", tipo: "moto" },
  { marca: "Yamaha", modelo: "Factor 150", tipo: "moto" },
  { marca: "Fiat", modelo: "Mobi Like", tipo: "carro" },
];

const ROTULO_DOC: Record<string, string> = { crlv: "CRLV", seguro: "Seguro", ipva: "IPVA", rastreador: "Rastreador" };
const substituidos = new Map<number, DocumentoVeiculo[]>();
const renovados = new Map<string, DocumentoVeiculo>();

function documentosAtivos(id: number): DocumentoVeiculo[] {
  const seguroVence = id === 501;
  const arquivo = (nome: string) => ({ nome, url: `https://arquivos.falso/${id}/${nome}`, url_expira_em: "2026-10-07T12:15:00Z" });
  const base: DocumentoVeiculo[] = [
    { id: id * 10 + 1, tipo: "crlv", rotulo: "CRLV 2026", validade: "2026-12-31", situacao: "em_dia", dias_para_vencer: 85, arquivo: arquivo("crlv-2026.pdf") },
    // IPVA e rastreador ainda não são tipos do contrato (VEI-03: CRLV e seguro). O texto da situação é do falso.
    { id: id * 10 + 3, tipo: "ipva", rotulo: "IPVA 2026", validade: null, situacao: "em_dia", dias_para_vencer: null, situacao_rotulo: "Pago", arquivo: arquivo("ipva-2026.pdf") },
    { id: id * 10 + 2, tipo: "seguro", rotulo: "Seguro", validade: seguroVence ? "2026-10-25" : "2027-03-10", situacao: seguroVence ? "vence_em_breve" : "em_dia", dias_para_vencer: seguroVence ? 18 : 154, arquivo: arquivo("apolice.pdf") },
    { id: id * 10 + 4, tipo: "rastreador", rotulo: "Rastreador", validade: null, situacao: "em_dia", dias_para_vencer: null, situacao_rotulo: "Online", arquivo: null },
  ];
  return base.map((d) => renovados.get(`${id}:${d.tipo}`) ?? d);
}

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
    Object.assign(campos, validarVei09(v));
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
    gravarVei09(s, v);
    SEMENTES.push(s);
    return veiculosFalso.obter(s.id);
  },

  /** POST /api/veiculos/leitura-crlv/ (VEI-08): lê só o que o PDF de exemplo traz; qualquer outro arquivo é a recusa 422 de sempre. */
  async lerCrlv(arquivo: File): Promise<LeituraCrlv> {
    await pausa(400);
    if (!podeEditar()) throw new ErroApi(403, "permissao", "Você não tem permissão para cadastrar veículos");
    if (!/.pdf$/i.test(arquivo.name)) throw new ErroApi(400, "validacao", "Confira o arquivo", undefined, { arquivo: "Envie o PDF do CRLV-e." });
    if (!/crlv/i.test(arquivo.name)) throw new ErroApi(422, "VEI-08", "Não conseguimos ler este documento. Preencha os campos à mão.");
    // T-415 (VEI-08): "CHEVROLET/CRUZE LT NB" não traz o modelo, só a marca e as 3 versões que batem no catálogo.
    if (/cruze/i.test(arquivo.name))
      return {
        documento: "crlv",
        campos: { placa: "RAB1C23", chassi: "9BGKS48B0PG123456", renavam: "01234567891", marca: "GM - Chevrolet", modelo: null, ano_fabricacao: 2023, ano_modelo: 2023, cor: "prata", combustivel: "flex", ...CAMPOS_DA_VEI_09_VAZIOS },
        lidos: ["placa", "chassi", "renavam", "marca", "ano_fabricacao", "ano_modelo", "cor", "combustivel"],
        quantidade: 8,
        rotulo: "CRLV-e lido · 8 campos preenchidos",
        exercicio: 2026,
        dicas: {
          marca_modelo: "CHEVROLET/CRUZE LT NB",
          candidatos: [
            { marca: "GM - Chevrolet", modelo: "CRUZE LT 1.4 16V Turbo Flex 4p Aut.", tipo: "carro" },
            { marca: "GM - Chevrolet", modelo: "CRUZE LT 1.8 16V FlexPower 4p Aut.", tipo: "carro" },
            { marca: "GM - Chevrolet", modelo: "CRUZE LT 1.8 16V FlexPower 4p Mec.", tipo: "carro" },
          ],
        },
        leitura: "comprovante-do-cruze",
      };
    // CA-421-01: os 9 de antes e os 7 da VEI-09 que o documento traz; carroceria e observações vazias ficam fora da conta.
    const campos = { placa: "TBC5H21", chassi: "9C2JC7500TR012345", renavam: "01234567890", marca: "Honda", modelo: "Pop 110i ES", ano_fabricacao: 2026, ano_modelo: 2026, cor: "vermelha", combustivel: "gasolina", ...CAMPOS_DO_TBC5H21 } as LeituraCrlv["campos"];
    const lidos = lidosDe(campos);
    return { documento: "crlv", campos, lidos, quantidade: lidos.length, rotulo: `CRLV-e lido · ${lidos.length} campos preenchidos`, exercicio: 2026, dicas: { marca_modelo: null, candidatos: [] }, leitura: "comprovante-de-exemplo" };
  },

  /**
   * POST /api/veiculos/{id}/leitura-crlv/ (VEI-08, T-421): lê como o cadastro, sem placa e chassi, e confere que o documento é deste veículo.
   * O arquivo `crlv-<placa>.pdf` diz de quem é o documento; o falso lê o de exemplo do PNB-7C04 e recusa o de outra placa.
   */
  async lerCrlvDoVeiculo(id: number, arquivo: File): Promise<LeituraCrlvNoEditar> {
    await pausa(400);
    if (!podeEditar()) throw new ErroApi(403, "permissao", "Você não tem permissão para editar veículos");
    const s = SEMENTES.find((x) => x.id === id);
    if (!s) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    if (!/.pdf$/i.test(arquivo.name)) throw new ErroApi(400, "validacao", "Confira o arquivo", undefined, { arquivo: "Envie o PDF do CRLV-e." });
    const dono = /crlv-([a-z]{3}\d[a-z0-9]\d{2})/i.exec(arquivo.name)?.[1]?.toUpperCase();
    if (!dono) throw new ErroApi(422, "VEI-08", "Não conseguimos ler este documento. Preencha os campos à mão.");
    if (dono !== s.placa) throw new ErroApi(422, "crlv_outro_veiculo", "Este CRLV-e é de outro veículo.");
    const campos = { renavam: "01289934410", marca: s.marca, modelo: s.modelo, ano_fabricacao: s.anoFabricacao ?? s.ano, ano_modelo: s.ano, cor: s.cor, combustivel: "flex", ...CAMPOS_DA_VEI_09_VAZIOS, "documento.potencia_cv": 12, "documento.cilindrada_cc": 149, "documento.especie": "passageiro", "documento.tipo": "Motocicleta", "documento.lotacao": 2, "documento.peso_bruto_kg": 270 } as LeituraCrlvNoEditar["campos"];
    const lidos = lidosDe(campos);
    return { documento: "crlv", campos, lidos, quantidade: lidos.length, rotulo: `CRLV-e lido · ${lidos.length} campos preenchidos`, exercicio: 2026, dicas: { marca_modelo: null, candidatos: [] }, leitura: `comprovante-do-veiculo-${id}` };
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
      else if (categoria.filial && categoria.filial.id !== (s.filialId ?? 1)) campos.categoria_id = "Esta categoria é de outra filial";
    }
    Object.assign(campos, validarVei09(v));
    if (Object.keys(campos).length > 0) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, campos);
    // VEI-11: o tipo vem da categoria; com locação aberta, a troca de tipo é recusada.
    const travado = motivoDeNaoTrocarTipo(s);
    if (categoria && categoria.tipo_veiculo !== s.tipo && travado) throw new ErroApi(409, "tipo_com_locacao_aberta", travado);
    gravarVei09(s, v);
    if (v.marca !== undefined) s.marca = v.marca.trim();
    if (v.modelo !== undefined) s.modelo = v.modelo.trim();
    if (v.ano_fabricacao !== undefined) s.anoFabricacao = v.ano_fabricacao;
    if (v.ano_modelo !== undefined) s.ano = v.ano_modelo;
    if (v.cor !== undefined) s.cor = v.cor.trim().toLowerCase();
    if (categoria) {
      s.categoriaId = categoria.id;
      s.categoria = categoria.nome;
      s.tipo = categoria.tipo_veiculo;
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
      ...blocosDoDocumento(s),
      // T-156, USR-09: vendedor e vistoriador recebem a ficha sem a chave (ausente, não `null`).
      ...(financeiro ? { indicadores_financeiros: { rendeu_no_ano_centavos: 987000, custo_manutencao_ano_centavos: 35300 } } : {}),
      galeria: (({ total, limite, fotos }) => ({ total, limite, fotos }))(galeriaDoFalso(id)),
      ocupacao: { pct: "86.00", periodo_dias: 90 },
      historico_status: [{ de: "disponivel", para: "alugado", em: "2026-09-23T12:00:00Z", origem_codigo: "LOC-2841" }],
    };
    return semValores(detalhe);
  },

  async documentos(id: number): Promise<DocumentoVeiculo[]> {
    await pausa(120);
    if (!SEMENTES.some((x) => x.id === id)) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    return documentosAtivos(id);
  },

  /** `GET .../documentos/historico/`: ativos e renovados. */
  async historicoDeDocumentos(id: number): Promise<DocumentoVeiculo[]> {
    await pausa(120);
    if (!SEMENTES.some((x) => x.id === id)) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    return [...documentosAtivos(id).map((d) => ({ ...d, ativo: true })), ...(substituidos.get(id) ?? [])];
  },

  async fotos(id: number): Promise<GaleriaDoEditar> {
    await pausa(120);
    if (!SEMENTES.some((x) => x.id === id)) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    return galeriaDoFalso(id);
  },

  async enviarFoto(id: number, arquivo: File): Promise<GaleriaDoEditar> {
    await pausa(120);
    exigirEdicaoDeFotos(id);
    exigirFotoValida(arquivo);
    const l = fotosDe(id);
    if (l.length >= LIMITE_DE_FOTOS) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { arquivo: "O veículo já tem 20 fotos. Apague uma para enviar outra." });
    const nova = { id: proximaFotoDaGaleria++, capa: l.length === 0, nome: arquivo.name };
    l.push(nova);
    return { ...galeriaDoFalso(id), foto_id: nova.id };
  },

  async trocarFoto(id: number, fotoId: number, arquivo: File): Promise<GaleriaDoEditar> {
    await pausa(120);
    exigirEdicaoDeFotos(id);
    exigirFotoValida(arquivo);
    const l = fotosDe(id);
    const i = l.findIndex((f) => f.id === fotoId);
    if (i < 0) throw new ErroApi(404, "nao_encontrado", "Foto não encontrada");
    const nova = { id: proximaFotoDaGaleria++, capa: l[i]!.capa, nome: arquivo.name };
    l[i] = nova;
    return { ...galeriaDoFalso(id), foto_id: nova.id };
  },

  async usarComoCapa(id: number, fotoId: number): Promise<GaleriaDoEditar> {
    await pausa(120);
    exigirEdicaoDeFotos(id);
    const l = fotosDe(id);
    if (!l.some((f) => f.id === fotoId)) throw new ErroApi(404, "nao_encontrado", "Foto não encontrada");
    for (const f of l) f.capa = f.id === fotoId;
    return galeriaDoFalso(id);
  },

  async apagarFoto(id: number, fotoId: number): Promise<GaleriaDoEditar> {
    await pausa(120);
    exigirEdicaoDeFotos(id);
    const l = fotosDe(id);
    const i = l.findIndex((f) => f.id === fotoId);
    if (i < 0) throw new ErroApi(404, "nao_encontrado", "Foto não encontrada");
    const eraCapa = l[i]!.capa;
    l.splice(i, 1);
    if (eraCapa && l[0]) l[0].capa = true;
    return galeriaDoFalso(id);
  },

  /** `POST .../documentos/` (VEI-03): o ativo do mesmo tipo vira inativo. Só administrador e gerente. */
  async enviarDocumento(id: number, d: NovoDocumentoVeiculo): Promise<DocumentoVeiculo> {
    await pausa(200);
    if (!podeEditar()) throw new ErroApi(403, "sem_permissao", "Você não tem permissão para editar veículos");
    if (!SEMENTES.some((x) => x.id === id)) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    if (!d.validade) throw new ErroApi(400, "validacao", "Informe a validade", undefined, { validade: "Informe a validade" });
    const anterior = documentosAtivos(id).find((x) => x.tipo === d.tipo);
    if (anterior) substituidos.set(id, [{ ...anterior, ativo: false }, ...(substituidos.get(id) ?? [])]);
    const novo: DocumentoVeiculo = {
      id: id * 10 + 50 + (substituidos.get(id)?.length ?? 0),
      tipo: d.tipo,
      rotulo: ROTULO_DOC[d.tipo] ?? d.tipo,
      validade: d.validade,
      situacao: "em_dia",
      dias_para_vencer: null,
      arquivo: d.arquivo ? { nome: d.arquivo.name, url: `https://arquivos.falso/${id}/${d.arquivo.name}` } : null,
    };
    renovados.set(`${id}:${d.tipo}`, novo);
    return novo;
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
