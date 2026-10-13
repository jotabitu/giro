// DADOS FALSOS da importação por planilha nos testes (docs/api/importacao.md). Só api-falsa.ts importa este arquivo.
// Caso do seed (CA-027-01): frota-moto-rapida.xlsx com 86 linhas, 83 prontas e 3 com erro (linhas 14, 37 e 52); corrigidas, 86 veículos.
import { ErroApi } from "@/lib/api/tipos";
import type { Importacao, LinhaDaImportacao, NovaImportacao, StatusDaLinha, TipoDeImportacao } from "@/lib/api/tipos-importacao";
import { pausa } from "./falso";

type Estado = { imp: Importacao; linhas: LinhaDaImportacao[] };

let estados: Estado[] = [];
let proximoId = 12;
let limiteDeVeiculos: number | null = 150;
let jaImportadosAntes = 0;

const ERROS_DO_SEED: Record<number, { campo: string; codigo: string; mensagem: string; dados: Record<string, string> }> = {
  14: { campo: "placa", codigo: "VEI-01", mensagem: "Placa QXA4B2 está incompleta", dados: { placa: "QXA4B2", chassi: "9C2KC2210PR004417", modelo: "CG 160 Fan" } },
  37: { campo: "chassi", codigo: "VEI-01", mensagem: "Chassi repetido na linha 12", dados: { placa: "RJD5B38", chassi: "9C2KC2210PR004412", modelo: "Biz 125" } },
  52: { campo: "ano_modelo", codigo: "validacao", mensagem: "Ano do modelo em branco", dados: { placa: "PQD6E21", chassi: "9C2KC2210PR004450", modelo: "Pop 110i", ano_modelo: "" } },
};

function linhasDe(tipo: TipoDeImportacao, total: number): LinhaDaImportacao[] {
  return Array.from({ length: total }, (_, i) => {
    const numero = i + 1;
    const erro = tipo === "veiculos" ? ERROS_DO_SEED[numero] : undefined;
    return {
      numero,
      status: erro ? "com_erro" : "pronta",
      dados: erro ? erro.dados : tipo === "veiculos" ? { placa: `AAA${1000 + numero}`, modelo: "CG 160" } : { nome: `Cliente ${numero}`, documento: "***.218.330-**", celular: "85988771203" },
      erros: erro ? [{ campo: erro.campo, codigo: erro.codigo, mensagem: erro.mensagem }] : [],
      objeto: null,
    } satisfies LinhaDaImportacao;
  });
}

function recontar(e: Estado) {
  const n = (s: StatusDaLinha) => e.linhas.filter((l) => l.status === s).length;
  e.imp = { ...e.imp, contagens: { linhas: e.linhas.length, prontas: n("pronta"), com_erro: n("com_erro"), importadas: n("importada"), acima_do_limite: n("acima_do_limite") } };
}

function montar(tipo: TipoDeImportacao, arquivo: string, total: number): Estado {
  const imp: Importacao = {
    id: proximoId++,
    tipo,
    arquivo,
    status: "validada",
    filial_padrao: tipo === "veiculos" ? { id: 1, nome: "Filial Centro" } : null,
    contagens: { linhas: total, prontas: 0, com_erro: 0, importadas: 0, acima_do_limite: 0 },
    plano: tipo === "veiculos" ? { usado: jaImportadosAntes, limite: limiteDeVeiculos, cabem: limiteDeVeiculos === null ? null : limiteDeVeiculos - jaImportadosAntes } : null,
    aviso: null,
    enviada_por: "Mariana Costa",
    enviada_em: "2026-10-07T13:00:00Z",
    concluida_em: null,
    apagar_em: "2026-11-06",
  };
  const e = { imp, linhas: linhasDe(tipo, total) };
  recontar(e);
  return e;
}

export function reiniciarImportacaoFalso(opcoes: { veiculosEnviados?: boolean; limite?: number | null } = {}) {
  estados = [];
  proximoId = 12;
  limiteDeVeiculos = opcoes.limite === undefined ? 150 : opcoes.limite;
  jaImportadosAntes = 0;
  if (opcoes.veiculosEnviados) estados.push(montar("veiculos", "frota-moto-rapida.xlsx", 86));
}
reiniciarImportacaoFalso();

const achar = (id: number) => {
  const e = estados.find((x) => x.imp.id === id);
  if (!e) throw new ErroApi(404, "nao_encontrado", "Importação não encontrada.");
  return e;
};

export const importacaoFalso = {
  async listar(): Promise<Importacao[]> {
    await pausa(40);
    return estados.map((e) => ({ ...e.imp }));
  },

  async obter(id: number): Promise<Importacao> {
    await pausa(40);
    return { ...achar(id).imp };
  },

  async enviar(corpo: NovaImportacao): Promise<Importacao> {
    await pausa(60);
    if (!/\.(xlsx|csv)$/i.test(corpo.arquivo.name)) throw new ErroApi(400, "validacao", "Envie um arquivo .xlsx ou .csv.", undefined, { arquivo: "Envie um arquivo .xlsx ou .csv." });
    if (estados.some((e) => e.imp.tipo === corpo.tipo && ["validando", "importando"].includes(e.imp.status))) throw new ErroApi(409, "importacao_em_andamento", "Já existe uma importação em andamento.");
    const e = montar(corpo.tipo, corpo.arquivo.name, corpo.tipo === "veiculos" ? 86 : 10);
    estados = [e, ...estados];
    return { ...e.imp };
  },

  async linhas(id: number, status?: StatusDaLinha): Promise<LinhaDaImportacao[]> {
    await pausa(40);
    return achar(id)
      .linhas.filter((l) => !status || l.status === status)
      .map((l) => ({ ...l, dados: { ...l.dados }, erros: l.erros.map((x) => ({ ...x })) }));
  },

  async corrigir(id: number, numero: number, dados: Record<string, string>): Promise<LinhaDaImportacao> {
    await pausa(40);
    const e = achar(id);
    const l = e.linhas.find((x) => x.numero === numero);
    if (!l || !["com_erro", "pronta"].includes(l.status)) throw new ErroApi(409, "transicao_linha", "Esta linha não pode ser corrigida.");
    const novos = { ...l.dados, ...dados };
    const vazio = Object.values(dados).some((v) => v.trim() === "");
    const placaCurta = typeof dados.placa === "string" && dados.placa.replace(/\W/g, "").length !== 7;
    const erros = vazio ? [{ campo: Object.keys(dados)[0]!, codigo: "validacao", mensagem: "Campo obrigatório em branco" }] : placaCurta ? [{ campo: "placa", codigo: "VEI-01", mensagem: "Placa incompleta" }] : [];
    const nova: LinhaDaImportacao = { ...l, dados: novos, erros, status: erros.length ? "com_erro" : "pronta" };
    e.linhas = e.linhas.map((x) => (x.numero === numero ? nova : x));
    recontar(e);
    return nova;
  },

  async ignorar(id: number, numero: number): Promise<LinhaDaImportacao> {
    await pausa(40);
    const e = achar(id);
    e.linhas = e.linhas.map((x) => (x.numero === numero ? { ...x, status: "ignorada" as const } : x));
    recontar(e);
    return { ...e.linhas.find((x) => x.numero === numero)! };
  },

  async importar(id: number): Promise<Importacao> {
    await pausa(60);
    const e = achar(id);
    const prontas = e.linhas.filter((l) => l.status === "pronta");
    if (prontas.length === 0) throw new ErroApi(422, "nada_para_importar", "Não há linhas prontas para importar.");
    const cabem = limiteDeVeiculos === null || e.imp.tipo === "clientes" ? prontas.length : Math.max(limiteDeVeiculos - jaImportadosAntes, 0);
    const entram = new Set(prontas.slice(0, cabem).map((l) => l.numero));
    e.linhas = e.linhas.map((l) => (l.status !== "pronta" ? l : entram.has(l.numero) ? { ...l, status: "importada" as const, objeto: { tipo: e.imp.tipo === "veiculos" ? "veiculo" : "cliente", id: 500 + l.numero } } : { ...l, status: "acima_do_limite" as const }));
    jaImportadosAntes += entram.size;
    const fora = prontas.length - entram.size;
    recontar(e);
    e.imp = {
      ...e.imp,
      status: "concluida",
      concluida_em: "2026-10-07T13:05:00Z",
      aviso: fora > 0 ? { codigo: "IMP-03", mensagem: `Importamos ${entram.size} veículos, o limite do plano Essencial. ${fora} ficaram de fora: mude de plano para importar o resto.` } : null,
    };
    return { ...e.imp };
  },

  async cancelar(id: number): Promise<Importacao> {
    await pausa(40);
    const e = achar(id);
    if (e.imp.status !== "validada") throw new ErroApi(409, "transicao_importacao", "Só uma importação validada pode ser cancelada.");
    e.imp = { ...e.imp, status: "cancelada" };
    return { ...e.imp };
  },

  async modelo(tipo: TipoDeImportacao): Promise<Blob> {
    await pausa(40);
    return new Blob([`modelo ${tipo}`], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  },
};
