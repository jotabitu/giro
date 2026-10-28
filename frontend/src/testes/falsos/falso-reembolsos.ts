// DADOS FALSOS dos reembolsos e das pendências do pagamento (docs/api/financeiro.md, T-358 e T-380). Só falso-financeiro.ts importa este arquivo.
// Seed Moto Rápida em 07 out 2026: Juliana com R$ 183,00 a fazer (DEV-02); Carlos com a pendência de R$ 299,40 (AUT-05).
// Os textos, os indicadores e as ações são da "API"; a tela só mostra.
import { ErroApi } from "@/lib/api/tipos";
import type { AcaoDaPendencia, FiltroPendencias, FiltroReembolsos, ListaPendencias, ListaReembolsos, PendenciaPagamento, Reembolso } from "@/lib/api/tipos-financeiro";
import { pausa } from "./falso";

const FEITO_POR = { id: 4, nome: "Bruna Alves" };
const COMPROVANTE = { url: "/comprovantes/reembolso.pdf", url_expira_em: "2026-10-07T13:15:00Z" };

function reembolso(p: Partial<Reembolso> & Pick<Reembolso, "id" | "cliente" | "valor_centavos" | "forma" | "criado_em">): Reembolso {
  return {
    origem: { tipo: "devolucao", codigo: "LOC-2836", id: 2836, veiculo: "QXA-4B21 · Honda CG 160 Fan" },
    origem_rotulo: "Devolução com caução",
    motivo: "Caução integral sem pendência",
    forma_rotulo: p.forma === "pix" ? "Pix" : p.forma === "dinheiro" ? "Dinheiro" : "Estorno no cartão",
    status: "feito",
    status_rotulo: "Feito",
    feito_em: p.criado_em,
    feito_por: FEITO_POR,
    comprovante: null,
    acoes: { marcar_feito: false },
    ...p,
  };
}

const REEMBOLSOS: Reembolso[] = [
  reembolso({
    id: 31,
    criado_em: "2026-10-07T17:10:00Z",
    cliente: { id: 1201, nome: "Juliana Rocha" },
    motivo: "Caução de R$ 600,00 menos diárias e acerto",
    forma: "pix",
    valor_centavos: 18300,
    status: "a_fazer",
    status_rotulo: "A fazer",
    feito_em: null,
    feito_por: null,
    acoes: { marcar_feito: true },
  }),
  reembolso({
    id: 30,
    criado_em: "2026-10-06T19:45:00Z",
    cliente: { id: 1180, nome: "Diego Santos" },
    origem: { tipo: "devolucao", codigo: "LOC-2820", id: 2820, veiculo: "PMZ-3E17 · Yamaha Factor 150" },
    forma: "estorno_cartao",
    valor_centavos: 60000,
    comprovante: COMPROVANTE,
  }),
  reembolso({
    id: 29,
    criado_em: "2026-10-05T14:20:00Z",
    cliente: { id: 1175, nome: "Letícia Barbosa" },
    origem: { tipo: "cancelamento", codigo: "LOC-2815", id: 2815, veiculo: "POZ-8C14 · Honda NXR 160 Bros" },
    origem_rotulo: "Locação cancelada antes da retirada",
    motivo: "Desistência antes da retirada do veículo",
    forma: "pix",
    valor_centavos: 35000,
    comprovante: COMPROVANTE,
  }),
  reembolso({
    id: 28,
    criado_em: "2026-10-02T20:30:00Z",
    cliente: { id: 1160, nome: "Marcos Lima" },
    origem: { tipo: "devolucao", codigo: "LOC-2804", id: 2804, veiculo: "ROX-2A19 · Honda CG 160 Fan" },
    motivo: "Saldo devolvido em dinheiro no caixa",
    forma: "dinheiro",
    valor_centavos: 15000,
  }),
];

function pendencia(p: Partial<PendenciaPagamento> & Pick<PendenciaPagamento, "id" | "criado_em" | "cliente" | "cobranca" | "motivo" | "motivo_rotulo" | "detalhe" | "valor_pago_centavos">): PendenciaPagamento {
  return {
    origem: { codigo: "LOC-2841", conta_id: 9921, parcela: "parcela 2 de 5" },
    status: "aberta",
    status_rotulo: "Aberta",
    resolucao: null,
    acoes: { resolver: true, baixar: true },
    ...p,
  };
}

const PENDENCIAS: PendenciaPagamento[] = [
  pendencia({
    id: 12,
    criado_em: "2026-10-07T17:45:00Z",
    cobranca: { id_no_parceiro: "pay_88192", forma: "pix", forma_rotulo: "Pix" },
    cliente: { id: 1187, nome: "Carlos Menezes" },
    motivo: "valor_diferente",
    motivo_rotulo: "Valor pago diferente",
    detalhe: "Pagou R$ 299,40; a conta estava em R$ 306,09 (falta R$ 6,69).",
    valor_pago_centavos: 29940,
  }),
  pendencia({
    id: 11,
    criado_em: "2026-10-06T19:30:00Z",
    cobranca: { id_no_parceiro: "pay_77401", forma: "pix", forma_rotulo: "Pix" },
    cliente: { id: 1190, nome: "Roberto Dias" },
    origem: { codigo: "LOC-2838", conta_id: 9930, parcela: "parcela 1 de 4" },
    motivo: "sem_conta",
    motivo_rotulo: "A conta já não estava aberta",
    detalhe: "Pagou R$ 329,00, mas a conta já estava cancelada.",
    valor_pago_centavos: 32900,
    acoes: { resolver: true, baixar: false },
  }),
  pendencia({
    id: 10,
    criado_em: "2026-10-05T12:12:00Z",
    cobranca: { id_no_parceiro: "pay_65219", forma: "cartao", forma_rotulo: "Cartão" },
    cliente: { id: 1150, nome: "Rafael Sousa" },
    origem: { codigo: "LOC-2790", conta_id: 9800, parcela: "parcela 4 de 4" },
    motivo: "estornada_no_parceiro",
    motivo_rotulo: "Estornada no parceiro",
    detalhe: "O parceiro estornou o pagamento de R$ 1.347,00.",
    valor_pago_centavos: 134700,
    status: "resolvida",
    status_rotulo: "Resolvida",
    resolucao: { texto: "Ignorada: estorno registrado", em: "2026-10-05T15:00:00Z" },
    acoes: { resolver: false, baixar: false },
  }),
];

let reembolsos: Reembolso[] = [];
let pendencias: PendenciaPagamento[] = [];
/** O plano Essencial não tem `recebimento_parceiro` (PLT-12); o teste liga isto para ver o 403. */
export const planoDoFalso = { essencial: false };
/** O que cada chamada de escrita recebeu, para o teste conferir o corpo. */
export const chamadasDeReembolso: { id: number; comprovante: boolean }[] = [];
export const chamadasDePendencia: { id: number; acao: AcaoDaPendencia; motivo: string }[] = [];

export function reiniciarReembolsosFalso() {
  reembolsos = REEMBOLSOS.map((r) => ({ ...r, acoes: { ...r.acoes } }));
  pendencias = PENDENCIAS.map((p) => ({ ...p, acoes: { ...p.acoes } }));
  planoDoFalso.essencial = false;
  chamadasDeReembolso.length = 0;
  chamadasDePendencia.length = 0;
}
reiniciarReembolsosFalso();

const semAcento = (t: string) => t.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const soma = (xs: { valor_centavos: number }[]) => xs.reduce((t, x) => t + x.valor_centavos, 0);
const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;
const dinheiroTexto = (c: number) => `R$ ${(c / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

export const reembolsosFalso = {
  async listarReembolsos(f: FiltroReembolsos = {}): Promise<ListaReembolsos> {
    await pausa(60);
    const status = f.status ?? "a_fazer";
    const termo = semAcento(f.busca ?? "");
    const doTermo = reembolsos.filter((r) => !termo || semAcento(`${r.cliente.nome} ${r.origem.codigo ?? ""}`).includes(termo));
    const aFazer = doTermo.filter((r) => r.status === "a_fazer");
    const feitos = doTermo.filter((r) => r.status === "feito");
    const lista = status === "todos" ? doTermo : status === "feito" ? feitos : aFazer;
    return {
      indicadores: {
        a_fazer: { valor_centavos: soma(aFazer), quantidade: aFazer.length, texto: plural(aFazer.length, "cliente com devolução", "clientes com devolução") },
        feitos: { valor_centavos: soma(feitos), quantidade: feitos.length, texto: plural(feitos.length, "reembolso feito", "reembolsos feitos") },
      },
      contagens: { a_fazer: aFazer.length, feito: feitos.length, todos: doTermo.length },
      resultados: lista.map((r) => ({ ...r })),
      proximo: null,
      anterior: null,
    };
  },

  async marcarReembolsoFeito(id: number, comprovante?: File | null): Promise<Reembolso> {
    await pausa(60);
    chamadasDeReembolso.push({ id, comprovante: !!comprovante });
    const atual = reembolsos.find((r) => r.id === id);
    if (!atual) throw new ErroApi(404, "nao_encontrado", "Reembolso não encontrado.");
    if (atual.status !== "a_fazer") throw new ErroApi(409, "transicao_reembolso", "Só reembolso a fazer pode ser marcado como feito.");
    const feito: Reembolso = { ...atual, status: "feito", status_rotulo: "Feito", feito_em: "2026-10-07T18:00:00Z", feito_por: FEITO_POR, comprovante: comprovante ? COMPROVANTE : null, acoes: { marcar_feito: false } };
    reembolsos = reembolsos.map((r) => (r.id === id ? feito : r));
    return { ...feito };
  },

  async listarPendencias(f: FiltroPendencias = {}): Promise<ListaPendencias> {
    await pausa(60);
    if (planoDoFalso.essencial) throw new ErroApi(403, "PLT-12", "Este recurso não está no plano da sua empresa.");
    const status = f.status ?? "aberta";
    const termo = semAcento(f.busca ?? "");
    const doTermo = pendencias.filter((p) => !termo || semAcento(`${p.cobranca.id_no_parceiro} ${p.cliente.nome} ${p.origem.codigo ?? ""}`).includes(termo));
    const abertas = doTermo.filter((p) => p.status === "aberta");
    const resolvidas = doTermo.filter((p) => p.status === "resolvida");
    const valor = (xs: PendenciaPagamento[]) => xs.reduce((t, p) => t + (p.valor_pago_centavos ?? 0), 0);
    const lista = status === "todas" ? doTermo : status === "resolvida" ? resolvidas : abertas;
    return {
      indicadores: {
        abertas: { quantidade: abertas.length, valor_centavos: valor(abertas), texto: `${dinheiroTexto(valor(abertas))} em análise` },
        resolvidas: { quantidade: resolvidas.length, valor_centavos: valor(resolvidas), texto: `${plural(resolvidas.length, "resolvida", "resolvidas")} no mês` },
      },
      contagens: { aberta: abertas.length, resolvida: resolvidas.length, todas: doTermo.length },
      resultados: lista.map((p) => ({ ...p })),
      proximo: null,
      anterior: null,
    };
  },

  async resolverPendencia(id: number, corpo: { acao: AcaoDaPendencia; motivo: string }): Promise<PendenciaPagamento> {
    await pausa(60);
    chamadasDePendencia.push({ id, ...corpo });
    const atual = pendencias.find((p) => p.id === id);
    if (!atual) throw new ErroApi(404, "nao_encontrado", "Pendência não encontrada.");
    if (!corpo.motivo.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { motivo: "Informe o motivo." });
    if (atual.status !== "aberta") throw new ErroApi(409, "transicao_pendencia", "Esta pendência já foi resolvida.");
    if (corpo.acao === "baixar" && !atual.acoes.baixar) throw new ErroApi(409, "transicao_conta", "A conta não está aberta.");
    const resolvida: PendenciaPagamento = {
      ...atual,
      status: "resolvida",
      status_rotulo: "Resolvida",
      resolucao: { texto: `${corpo.acao === "baixar" ? "Baixada" : "Ignorada"}: ${corpo.motivo.trim()}`, em: "2026-10-07T18:00:00Z" },
      acoes: { resolver: false, baixar: false },
    };
    pendencias = pendencias.map((p) => (p.id === id ? resolvida : p));
    return { ...resolvida };
  },
};
