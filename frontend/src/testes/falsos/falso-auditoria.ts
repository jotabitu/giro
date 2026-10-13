// DADOS FALSOS da auditoria da empresa e da exportação nos testes (docs/api/auditoria.md). Só api-falsa.ts importa este arquivo.
// Eventos do seed de 07 out 2026 (Admin-Auditoria): resumo e detalhe vêm prontos, como na API.
import { ErroApi } from "@/lib/api/tipos";
import type { DetalheDoEvento, EventoDeAuditoria, ExportacaoRecente, FiltroAuditoria, ListaEventos, PedidoDeExportacao, PessoaDaAuditoria } from "@/lib/api/tipos-auditoria";
import { pausa } from "./falso";

const usuario = (id: number, nome: string, iniciais: string) => ({ tipo: "usuario" as const, id, nome, iniciais });
const BRUNA = usuario(4, "Bruna Alves", "BA");
const JOAO = usuario(5, "João Silva", "JS");
const MARIANA = usuario(1, "Mariana Costa", "MC");
const SISTEMA = { tipo: "sistema" as const, id: null, nome: "Sistema", iniciais: "⚙" };
const SUPORTE = { tipo: "suporte" as const, id: null, nome: "Suporte Giro", iniciais: "SG" };

function evento(id: number, ocorrido_em: string, ator: EventoDeAuditoria["ator"], categoria: EventoDeAuditoria["categoria"], acao: string, resumo: string, detalhe: string, extra: Partial<EventoDeAuditoria> = {}): EventoDeAuditoria {
  return { id, ocorrido_em, ator, suporte: null, categoria, acao, resumo, detalhe, objeto: null, regra: null, ...extra };
}

const ACESSO = { atendente: "Diego Santos", motivo: "Chamado #1042", permissao: "ver", acesso_suporte_id: 31 };

const EVENTOS: EventoDeAuditoria[] = [
  evento(50219, "2026-10-07T16:52:00Z", SUPORTE, "suporte", "acesso_suporte.encerrar", "Diego Santos saiu do modo suporte", "Duração 12 min · só ver · nenhuma alteração", { suporte: ACESSO }),
  evento(50218, "2026-10-07T16:40:00Z", SUPORTE, "suporte", "acesso_suporte.entrar", "Diego Santos entrou como suporte", "Chamado #1042 · você foi avisada por e-mail", { suporte: ACESSO }),
  evento(50217, "2026-10-07T14:20:00Z", BRUNA, "financeiro", "despesa.criar", "Lançou despesa de R$ 48,00", "Óleo · QXA-4B21 · pago no caixa", { objeto: { tipo: "despesa", id: 802, codigo: null, filial: "Filial Centro" } }),
  evento(50216, "2026-10-07T13:30:00Z", BRUNA, "financeiro", "movimento_caixa.sangria", "Fez sangria de R$ 500,00", "Caixa da Filial Centro", { objeto: { tipo: "movimentocaixa", id: 412, codigo: null, filial: "Filial Centro" } }),
  evento(50215, "2026-10-07T12:15:00Z", BRUNA, "operacao", "locacao.criar", "Criou a locação LOC-2856", "Lucas Ferreira · Honda CG 160 Fan", { objeto: { tipo: "locacao", id: 2856, codigo: "LOC-2856", filial: "Filial Centro" } }),
  evento(50214, "2026-10-07T11:55:00Z", JOAO, "financeiro", "despesa.pedir_aprovacao", "Pediu despesa de R$ 1.200,00", "Pneus · PMZ-3E17 · aguardando gerente", { objeto: { tipo: "despesa", id: 801, codigo: null, filial: "Filial Centro" } }),
  evento(50213, "2026-10-07T11:02:00Z", SISTEMA, "seguranca", "login.bloqueado", "Login bloqueado", "5 senhas erradas para rodrigo@motorapida.com.br", { regra: "USR-06" }),
  evento(50212, "2026-10-07T10:55:00Z", BRUNA, "financeiro", "caixa.abrir", "Abriu o caixa", "Troco de R$ 200,00", { objeto: { tipo: "caixa", id: 240, codigo: null, filial: "Filial Centro" } }),
  evento(50211, "2026-10-06T21:10:00Z", MARIANA, "seguranca", "usuario.convidar", "Convidou João Silva", "Perfil vistoriador · Filial Centro", { objeto: { tipo: "usuario", id: 5, codigo: null, filial: null } }),
  evento(50200, "2026-10-01T20:42:00Z", MARIANA, "configuracoes", "preco.alterar", "Mudou a tabela de preço", "Street 150–160 · semanal R$ 299,40 → R$ 329,00"),
];

const PESSOAS: PessoaDaAuditoria[] = [
  { tipo: "usuario", id: 1, nome: "Mariana Costa" },
  { tipo: "usuario", id: 4, nome: "Bruna Alves" },
  { tipo: "usuario", id: 5, nome: "João Silva" },
  { tipo: "sistema", id: null, nome: "Sistema" },
  { tipo: "suporte", id: null, nome: "Suporte Giro" },
];

const DESDE = { "7d": "2026-10-01", "30d": "2026-09-07", "90d": "2026-07-09" } as const;

let exportacoes: ExportacaoRecente[] = [];
let proximaExportacao = 17;
export function reiniciarAuditoriaFalso() {
  exportacoes = [
    { id: 16, solicitada_em: "2026-10-06T19:30:00Z", solicitada_por: "Mariana Costa", conteudo: "Auditoria · 01/09/2026 a 30/09/2026", formato: "csv", tamanho_bytes: 184320, status: "pronta", expira_em: "2026-10-13T19:30:00Z" },
    { id: 12, solicitada_em: "2026-09-01T12:00:00Z", solicitada_por: "Mariana Costa", conteudo: "Auditoria · 01/08/2026 a 31/08/2026", formato: "csv", tamanho_bytes: 150000, status: "expirada", expira_em: null },
  ];
  proximaExportacao = 17;
}
reiniciarAuditoriaFalso();

export const auditoriaFalso = {
  async eventos(f: FiltroAuditoria = {}): Promise<ListaEventos> {
    await pausa(60);
    const desde = DESDE[f.periodo ?? "7d"];
    const lista = EVENTOS.filter(
      (e) =>
        e.ocorrido_em.slice(0, 10) >= desde &&
        (!f.categoria || e.categoria === f.categoria) &&
        (f.ator === undefined || e.ator.id === f.ator) &&
        (!f.ator_tipo || e.ator.tipo === f.ator_tipo),
    );
    return { resultados: lista.map((e) => ({ ...e })), proximo: null, anterior: null };
  },

  async evento(id: number): Promise<DetalheDoEvento> {
    await pausa(40);
    const e = EVENTOS.find((x) => x.id === id);
    if (!e) throw new ErroApi(404, "nao_encontrado", "Evento não encontrado.");
    const preco = e.acao === "preco.alterar";
    return { ...e, antes: preco ? { semanal_centavos: 29940 } : {}, depois: preco ? { semanal_centavos: 32900 } : {}, ip: "177.84.10.4", aparelho: "Chrome no Windows" };
  },

  async pessoas(): Promise<PessoaDaAuditoria[]> {
    await pausa(40);
    return PESSOAS.map((p) => ({ ...p }));
  },

  async exportacoes(): Promise<ExportacaoRecente[]> {
    await pausa(40);
    return exportacoes.map((e) => ({ ...e }));
  },

  async exportar(corpo: PedidoDeExportacao): Promise<{ id: number; status: string }> {
    await pausa(60);
    const itens = corpo.itens as string[];
    if (itens.length !== 1 || itens[0] !== "auditoria" || corpo.formato !== "csv") throw new ErroApi(422, "exportacao_indisponivel", "Por enquanto, só a auditoria em CSV pode ser exportada.");
    const id = proximaExportacao++;
    const p = corpo.periodo;
    const br = (d: string) => d.split("-").reverse().join("/");
    exportacoes = [{ id, solicitada_em: "2026-10-07T18:00:00Z", solicitada_por: "Mariana Costa", conteudo: p ? `Auditoria · ${br(p.de)} a ${br(p.ate)}` : "Auditoria · tudo", formato: "csv", tamanho_bytes: null, status: "na_fila", expira_em: null }, ...exportacoes];
    return { id, status: "na_fila" };
  },

  async baixar(id: number): Promise<Blob> {
    await pausa(40);
    const e = exportacoes.find((x) => x.id === id);
    if (!e) throw new ErroApi(404, "nao_encontrado", "Exportação não encontrada.");
    if (e.status === "expirada") throw new ErroApi(410, "exportacao_expirada", "Este arquivo expirou. Gere outro.");
    return new Blob(["quando,quem,o_que\n"], { type: "text/csv" });
  },
};
