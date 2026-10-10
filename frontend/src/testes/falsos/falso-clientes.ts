// DADOS FALSOS de clientes enquanto a API não existe (contrato: docs/api/clientes.md).
// Só ./index.ts importa este arquivo. A "API" decide situação, ação principal, pendências e erros de validação.
import { pausa, perfilAtualFalso } from "./falso";
import {
  type AcaoPrincipal,
  type AnaliseCadastro,
  type ClienteCompleto,
  type ClienteResumo,
  type FiltroClientes,
  type HistoricoDoCliente,
  type ListaClientes,
  type LocacoesDoCliente,
  type NovoCliente,
  type StatusCliente,
  type TipoDocumentoCliente,
} from "@/lib/api/tipos-clientes";
import type { TomApi } from "@/lib/api/tipos-frota";
import { ErroApi } from "@/lib/api/tipos";

const TAMANHO = 8;

type Registro = {
  id: number;
  tipo: "pf" | "pj";
  nome: string;
  documento: string;
  celular: string;
  status: StatusCliente;
  desde: string;
  criadoEm: number;
  locacao?: { id: number; codigo: string; veiculo: string; detalhe: string; alerta?: string; aDevolver?: number };
  ultima?: { codigo: string; encerrada_em: string };
  pago: number;
  aberto: number;
  venda?: { id: number; codigo: string; veiculo: string };
  pendencias: string[];
  anexos: TipoDocumentoCliente[];
  motivoBloqueio?: "atraso" | "manual";
  /** Dados do cadastro completo (nascimento, CNH, endereço...). Sem eles a API devolve `null`. */
  extra?: Partial<NovoCliente>;
};

/** "Hoje" do seed (07 out 2026): a idade que a API devolve é calculada contra ele. */
const HOJE_DO_SEED = "2026-10-07";

function idadeEm(nascimento: string): number {
  const [a = 0, m = 0, d = 0] = nascimento.split("-").map(Number);
  const [ah = 0, mh = 0, dh = 0] = HOJE_DO_SEED.split("-").map(Number);
  return ah - a - (mh < m || (mh === m && dh < d) ? 1 : 0);
}

const REGISTROS: Registro[] = [
  { id: 1206, tipo: "pf", nome: "Lucas Ferreira", documento: "12345678909", celular: "85988771203", status: "incompleto", desde: "2026-10-07", criadoEm: 9, locacao: { id: 2856, codigo: "LOC-2856", veiculo: "Honda CG 160 Fan", detalhe: "" }, pago: 62900, aberto: 0, pendencias: ["selfie_documento", "comprovante_residencia"], anexos: ["cnh_frente", "cnh_verso"] },
  { id: 1201, tipo: "pf", nome: "Juliana Rocha", documento: "05221833018", celular: "85981142290", status: "ativo", desde: "2026-03-04", criadoEm: 8, locacao: { id: 2836, codigo: "LOC-2836", veiculo: "Factor 150", detalhe: "semanal" }, pago: 267400, aberto: 0, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"],
    extra: {
      nascimento: "1994-07-02",
      email: "juliana.rocha@email.com",
      profissao: "Entregadora",
      cnh: { numero: "03811234562", categoria: "A", validade: "2030-11-18", primeira_habilitacao: "2016-08-10" },
      endereco: { cep: "60115190", logradouro: "Rua Monsenhor Bruno", numero: "1120", complemento: null, bairro: "Aldeota", cidade: "Fortaleza", uf: "CE" },
      referencia: { nome: "Sandra Rocha", parentesco: "mãe", telefone: "85988224410" },
      consentimento: true,
    },
  },
  { id: 1202, tipo: "pf", nome: "Carlos Menezes", documento: "39901442055", celular: "85997025531", status: "ativo", desde: "2026-01-12", criadoEm: 7, locacao: { id: 2841, codigo: "LOC-2841", veiculo: "CG 160 Fan", detalhe: "" }, pago: 389220, aberto: 29940, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"] },
  { id: 1203, tipo: "pf", nome: "Rafael Sousa", documento: "15337710582", celular: "85986504419", status: "bloqueado", desde: "2025-08-20", criadoEm: 6, locacao: { id: 2790, codigo: "LOC-2790", veiculo: "Pop 110i", detalhe: "25 dias de atraso" }, pago: 179600, aberto: 134700, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"], motivoBloqueio: "atraso" },
  { id: 1204, tipo: "pf", nome: "Marcos Viana", documento: "76640258014", celular: "85992318870", status: "ativo", desde: "2025-05-09", criadoEm: 5, locacao: { id: 2850, codigo: "LOC-2850", veiculo: "Biz 125", detalhe: "mensal" }, pago: 1138000, aberto: 0, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"] },
  { id: 1205, tipo: "pf", nome: "Patrícia Gomes", documento: "21412987403", celular: "85988430912", status: "ativo", desde: "2026-02-17", criadoEm: 4, locacao: { id: 2812, codigo: "LOC-2812", veiculo: "NMax 160", detalhe: "", alerta: "Cancelando", aDevolver: 28620 }, pago: 477000, aberto: 0, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"] },
  { id: 1207, tipo: "pf", nome: "Diego Martins", documento: "31789123092", celular: "85991206634", status: "ativo", desde: "2025-11-03", criadoEm: 3, locacao: { id: 2848, codigo: "LOC-2848", veiculo: "Kwid", detalhe: "proposta CB 300F" }, pago: 214070, aberto: 0, venda: { id: 177, codigo: "VEN-0177", veiculo: "CB 300F" }, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"] },
  { id: 1208, tipo: "pf", nome: "Ana Beatriz Lima", documento: "55201689071", celular: "85987613345", status: "ativo", desde: "2025-07-22", criadoEm: 2, ultima: { codigo: "LOC-2702", encerrada_em: "2026-09-29" }, pago: 263200, aberto: 0, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"] },
  { id: 1209, tipo: "pj", nome: "Veloz Entregas Ltda", documento: "11222333000181", celular: "85984410077", status: "ativo", desde: "2026-04-15", criadoEm: 1, locacao: { id: 2860, codigo: "LOC-2860", veiculo: "Biz 125", detalhe: "mensal" }, pago: 540000, aberto: 0, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"] },
  { id: 1210, tipo: "pf", nome: "Bruno Teixeira", documento: "48370915005", celular: "85983302211", status: "inativo", desde: "2024-12-02", criadoEm: 0, pago: 98000, aberto: 0, pendencias: [], anexos: ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"] },
];

/** LOC-2836 (LOC-05, LOC-06): 2 semanas de 30 set 18:00 a 14 out 18:00, ativa em 07 out, sem "devolve hoje". */
const LOCACOES: Record<number, LocacoesDoCliente> = {
  1201: {
    total: 3,
    com_atraso: 0,
    resultados: [
      { id: 2836, codigo: "LOC-2836", status: "ativa", veiculo: { id: 412, modelo: "Yamaha Factor 150", placa: "PNB7C04", tipo_veiculo: "moto" }, periodicidade: "semanal", inicio: "2026-09-30T21:00:00Z", fim_previsto: "2026-10-14T21:00:00Z", situacao: { codigo: "ativa", rotulo: "Ativa", tom: "sucesso" }, pago_centavos: 95800, pago_detalhe: "2 semanas + caução R$ 300,00", valor_periodo_centavos: 32900, caucao_centavos: 30000, caucao_em_garantia: true, parcelas_pagas: 2, parcelas_total: 2 },
      { id: 2760, codigo: "LOC-2760", status: "encerrada", veiculo: { id: 412, modelo: "Yamaha Factor 150", placa: "PNB7C04", tipo_veiculo: "moto" }, periodicidade: "mensal", inicio: "2026-08-01T15:00:00Z", fim_previsto: "2026-08-31T15:00:00Z", situacao: { codigo: "encerrada", rotulo: "Encerrada", tom: "neutro" }, pago_centavos: 119000, pago_detalhe: "caução devolvida", valor_periodo_centavos: 89000, caucao_centavos: 30000, caucao_em_garantia: false, parcelas_pagas: 1, parcelas_total: 1 },
      { id: 2701, codigo: "LOC-2701", status: "encerrada", veiculo: { id: 501, modelo: "Honda CG 160 Fan", placa: "QXA4B21", tipo_veiculo: "moto" }, periodicidade: "semanal", inicio: "2026-06-02T15:00:00Z", fim_previsto: "2026-06-12T15:00:00Z", situacao: { codigo: "encerrada", rotulo: "Encerrada", tom: "neutro" }, pago_centavos: 52600, pago_detalhe: "1 semana + 3 diárias + combustível", valor_periodo_centavos: 29900, caucao_centavos: 30000, caucao_em_garantia: false, parcelas_pagas: 1, parcelas_total: 1 },
    ],
  },
};

const HISTORICO: Record<number, HistoricoDoCliente["resultados"]> = {
  1201: [
    { em: "2026-10-07T11:02:00Z", rotulo: "Pagou a 2ª semana da LOC-2836", detalhe: "Pix · R$ 329,00" },
    { em: "2026-10-01T15:00:00Z", rotulo: "Retirou a Yamaha Factor 150 (LOC-2836)", detalhe: "vistoria de saída por João Silva" },
    { em: "2026-08-31T15:00:00Z", rotulo: "Encerrou a LOC-2760 sem pendências", detalhe: "caução de R$ 300,00 devolvida" },
    { em: "2026-03-04T13:00:00Z", rotulo: "Cadastro criado", detalhe: "por Bruna Alves · autorizou o uso dos dados (LGPD)" },
  ],
};

const TIPOS_DOCUMENTO: TipoDocumentoCliente[] = ["cnh_frente", "cnh_verso", "selfie_documento", "comprovante_residencia"];

export function digitos(t: string): string {
  return t.replace(/\D/g, "");
}

function cpfValido(c: string): boolean {
  if (c.length !== 11 || /^(\d)\1+$/.test(c)) return false;
  for (const t of [9, 10]) {
    const soma = [...c.slice(0, t)].reduce((a, d, i) => a + Number(d) * (t + 1 - i), 0);
    const dv = ((soma * 10) % 11) % 10;
    if (dv !== Number(c[t])) return false;
  }
  return true;
}

function cnpjValido(c: string): boolean {
  if (c.length !== 14 || /^(\d)\1+$/.test(c)) return false;
  for (const t of [12, 13]) {
    const pesos = t === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const soma = [...c.slice(0, t)].reduce((a, d, i) => a + Number(d) * (pesos[i] ?? 0), 0);
    const resto = soma % 11;
    const dv = resto < 2 ? 0 : 11 - resto;
    if (dv !== Number(c[t])) return false;
  }
  return true;
}

function mascarar(r: Pick<Registro, "tipo" | "documento">): string {
  const d = r.documento;
  return r.tipo === "pj" ? `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}` : `***.${d.slice(3, 6)}.${d.slice(6, 9)}-**`;
}

function situacaoDe(r: Registro): { codigo: string; rotulo: string; tom: TomApi } {
  if (r.status === "bloqueado") return { codigo: "bloqueado", rotulo: "Bloqueado", tom: "perigo" };
  if (r.locacao?.alerta === "Cancelando") return { codigo: "cancelando", rotulo: "Cancelando", tom: "alerta" };
  if (r.aberto > 0) return { codigo: "parcela_atrasada", rotulo: "Parcela atrasada", tom: "perigo" };
  if (r.status === "incompleto") return { codigo: "incompleto", rotulo: "Cadastro incompleto", tom: "alerta" };
  if (r.status === "inativo") return { codigo: "inativo", rotulo: "Inativo", tom: "neutro" };
  if (r.locacao) return { codigo: "em_dia", rotulo: "Em dia", tom: "sucesso" };
  return { codigo: "sem_locacao", rotulo: "Sem locação", tom: "neutro" };
}

function acaoDe(r: Registro): AcaoPrincipal | null {
  if (r.aberto > 0) return { codigo: "cobrar", rotulo: "Cobrar", alvo: { tipo: "conta", id: r.id } };
  if (r.status === "incompleto") return { codigo: "completar_cadastro", rotulo: "Completar cadastro", alvo: { tipo: "cliente", id: r.id } };
  if (r.venda) return { codigo: "ver_proposta", rotulo: "Ver proposta", alvo: { tipo: "venda", id: r.venda.id } };
  if (r.locacao) return { codigo: "ver_locacao", rotulo: "Ver locação", alvo: { tipo: "locacao", id: r.locacao.id } };
  if (r.status === "ativo") return { codigo: "nova_locacao", rotulo: "Nova locação", alvo: { tipo: "cliente", id: r.id } };
  return null;
}

function resumo(r: Registro): ClienteResumo {
  return {
    id: r.id,
    tipo: r.tipo,
    nome: r.nome,
    documento_mascarado: mascarar(r),
    celular: r.celular,
    status: r.status,
    situacao: situacaoDe(r),
    cliente_desde: r.desde,
    locacao_atual: r.locacao ? { id: r.locacao.id, codigo: r.locacao.codigo, veiculo: r.locacao.veiculo, detalhe: r.locacao.detalhe, alerta: r.locacao.alerta ?? null, valor_a_devolver_centavos: r.locacao.aDevolver } : null,
    ultima_locacao: r.ultima ?? null,
    financeiro: { total_pago_centavos: r.pago, em_aberto_centavos: r.aberto, a_devolver_centavos: r.locacao?.aDevolver ?? 0 },
    venda_aberta: r.venda ?? null,
    acao_principal: acaoDe(r),
  };
}

function analisarCorpo(c: Partial<NovoCliente>, anexos = 0): AnaliseCadastro {
  const doc = digitos(c.documento ?? "");
  const pj = c.tipo === "pj";
  const bloqueado = REGISTROS.some((r) => r.status === "bloqueado" && r.documento === doc);
  const docOk = pj ? cnpjValido(doc) : cpfValido(doc);
  const cat = c.cnh?.categoria;
  return {
    itens: [
      { codigo: "cpf", situacao: docOk ? "ok" : doc ? "problema" : "pendente", rotulo: pj ? (docOk ? "CNPJ válido" : doc ? "CNPJ inválido" : "CNPJ não informado") : docOk ? "CPF válido" : doc ? "CPF inválido" : "CPF não informado" },
      { codigo: "cnh", situacao: cat ? "ok" : "pendente", rotulo: cat ? `CNH categoria ${cat}, válida` : "CNH não informada" },
      { codigo: "lista_bloqueio", situacao: bloqueado ? "problema" : "ok", rotulo: bloqueado ? "Consta na lista de bloqueio" : "Fora da lista de bloqueio" },
      { codigo: "historico", situacao: "ok", rotulo: "Sem atraso na empresa" },
      { codigo: "documentos", situacao: anexos >= 4 ? "ok" : "pendente", rotulo: anexos >= 4 ? "Documentos enviados" : `Faltam ${4 - anexos} documentos` },
    ],
  };
}

function pendenciasDe(c: NovoCliente): string[] {
  const p: string[] = [];
  if (!c.consentimento) p.push("consentimento");
  if (!c.cnh?.numero || !c.cnh.categoria || !c.cnh.validade) p.push("cnh");
  if (!c.endereco?.cep || !c.endereco.logradouro || !c.endereco.numero) p.push("endereco");
  if (!c.referencia?.nome || !c.referencia.telefone) p.push("referencia");
  if (c.tipo === "pf" && !c.nascimento) p.push("nascimento");
  if (c.tipo === "pj" && !c.responsavel?.nome) p.push("responsavel");
  return p;
}

function completo(r: Registro): ClienteCompleto {
  const x = r.extra ?? {};
  return {
    ...resumo(r),
    documento: r.documento,
    nascimento: x.nascimento ?? null,
    idade: x.nascimento ? idadeEm(x.nascimento) : null,
    email: x.email ?? null,
    profissao: x.profissao ?? null,
    cnh: x.cnh?.numero && x.cnh.categoria && x.cnh.validade ? { numero: x.cnh.numero, categoria: x.cnh.categoria, validade: x.cnh.validade, primeira_habilitacao: x.cnh.primeira_habilitacao ?? null, situacao: "valida" } : null,
    responsavel: x.responsavel?.nome ? { nome: x.responsavel.nome, cpf: x.responsavel.cpf ?? "", celular: x.responsavel.celular ?? "" } : null,
    endereco: x.endereco ?? null,
    referencia: x.referencia?.nome ? { nome: x.referencia.nome, parentesco: x.referencia.parentesco ?? "", telefone: x.referencia.telefone ?? "" } : null,
    consentimento_em: x.consentimento ? `${r.desde}T13:00:00Z` : null,
    bloqueio: r.motivoBloqueio ? { motivo: r.motivoBloqueio, desde: "2026-09-12", descricao: "Conta com 15 dias de atraso desde 27/08/2026", desbloqueia_sozinho: r.motivoBloqueio === "atraso" } : null,
    documentos: TIPOS_DOCUMENTO.map((tipo) => ({ tipo, enviado_em: r.anexos.includes(tipo) ? (tipo === "comprovante_residencia" && r.id === 1201 ? "2026-09-15T12:00:00Z" : `${r.desde}T12:00:00Z`) : null })),
    pendencias: r.pendencias,
    analise: analisarCorpo({ tipo: r.tipo, documento: r.documento, cnh: { categoria: x.cnh?.categoria ?? "A" } }, r.anexos.length),
  };
}

function normalizar(t: string): string {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function podeVerCompleto(): boolean {
  const p = perfilAtualFalso();
  return p === "administrador" || p === "gerente" || p === "vendedor";
}

export const clientesFalso = {
  async listar(f: FiltroClientes = {}): Promise<ListaClientes> {
    await pausa(200);
    const ativos = REGISTROS.filter((r) => r.status !== "inativo");
    const doFiltro = (r: Registro) => {
      switch (f.situacao) {
        case "com_locacao": return !!r.locacao;
        case "em_aberto": return r.aberto > 0;
        case "bloqueados": return r.status === "bloqueado";
        case "incompletos": return r.status === "incompleto";
        case "inativos": return r.status === "inativo";
        default: return r.status !== "inativo";
      }
    };
    let lista = REGISTROS.filter(doFiltro);
    if (f.busca) {
      const dig = digitos(f.busca);
      lista = lista.filter((r) => ((dig.length === 11 || dig.length === 14) && !/\D/.test(f.busca ?? "") ? r.documento === dig : normalizar(r.nome).includes(normalizar(f.busca ?? "")) || r.celular.includes(dig || "x")));
    }
    lista = [...lista].sort((a, b) => (f.ordem === "nome" ? a.nome.localeCompare(b.nome) : f.ordem === "-total_pago" ? b.pago - a.pago : b.criadoEm - a.criadoEm));
    const inicio = Number(f.cursor ?? 0);
    return {
      contagens: {
        todos: ativos.length,
        com_locacao: ativos.filter((r) => r.locacao).length,
        em_aberto: ativos.filter((r) => r.aberto > 0).length,
        bloqueados: ativos.filter((r) => r.status === "bloqueado").length,
        incompletos: ativos.filter((r) => r.status === "incompleto").length,
      },
      indicadores: { novos_no_mes_anterior: 38, com_locacao_pct: "7.00", em_aberto_total_centavos: ativos.reduce((a, r) => a + r.aberto, 0) },
      resultados: lista.slice(inicio, inicio + TAMANHO).map(resumo),
      proximo: inicio + TAMANHO < lista.length ? String(inicio + TAMANHO) : null,
      anterior: inicio > 0 ? String(Math.max(inicio - TAMANHO, 0)) : null,
    };
  },

  async obter(id: number): Promise<ClienteResumo | ClienteCompleto> {
    await pausa(150);
    const r = REGISTROS.find((x) => x.id === id);
    if (!r) throw new ErroApi(404, "nao_encontrado", "Cliente não encontrado");
    return podeVerCompleto() ? completo(r) : resumo(r);
  },

  async analisar(corpo: Partial<NovoCliente>): Promise<AnaliseCadastro> {
    await pausa(150);
    return analisarCorpo(corpo);
  },

  async criar(c: NovoCliente): Promise<ClienteCompleto> {
    await pausa(300);
    const doc = digitos(c.documento);
    const campos: Record<string, string> = {};
    if (c.tipo === "pf" ? !cpfValido(doc) : !cnpjValido(doc)) campos.documento = c.tipo === "pf" ? "CPF inválido. Confira os números." : "CNPJ inválido. Confira os números.";
    if (c.endereco?.cep && digitos(c.endereco.cep).length !== 8) campos["endereco.cep"] = "CEP deve ter 8 números";
    if (c.cnh?.categoria && !["A", "B", "AB", "C", "D", "E", "ACC"].includes(c.cnh.categoria)) campos["cnh.categoria"] = "Categoria de CNH inválida";
    if (Object.keys(campos).length > 0) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, campos);
    const existente = REGISTROS.find((r) => r.documento === doc);
    if (existente) {
      throw new ErroApi(409, "CLI-01", c.tipo === "pf" ? "Já existe um cliente com este CPF" : "Já existe um cliente com este CNPJ", { cliente_id: existente.id, nome: existente.nome });
    }
    const pendencias = [...TIPOS_DOCUMENTO, ...pendenciasDe(c)];
    const r: Registro = {
      id: 1211 + REGISTROS.length,
      tipo: c.tipo,
      nome: c.nome,
      documento: doc,
      celular: digitos(c.celular),
      status: "incompleto",
      desde: new Date().toISOString().slice(0, 10),
      criadoEm: REGISTROS.length,
      pago: 0,
      aberto: 0,
      pendencias,
      anexos: [],
      extra: c,
    };
    REGISTROS.push(r);
    return completo(r);
  },

  // Falsos: vêm de GET /api/locacoes/?cliente= (T-015) e de eventos de auditoria; ainda sem contrato para a ficha do cliente.
  async locacoes(id: number): Promise<LocacoesDoCliente> {
    await pausa(150);
    return LOCACOES[id] ?? { total: 0, com_atraso: 0, resultados: [] };
  },

  async historico(id: number): Promise<HistoricoDoCliente> {
    await pausa(150);
    return { resultados: HISTORICO[id] ?? [] };
  },

  async enviarDocumento(id: number, tipo: TipoDocumentoCliente, arquivo: File): Promise<ClienteCompleto> {
    await pausa(250);
    const r = REGISTROS.find((x) => x.id === id);
    if (!r) throw new ErroApi(404, "nao_encontrado", "Cliente não encontrado");
    if (arquivo.size > 10 * 1024 * 1024) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { arquivo: "O arquivo passa de 10 MB. Envie um menor." });
    if (!r.anexos.includes(tipo)) r.anexos.push(tipo);
    r.pendencias = r.pendencias.filter((p) => p !== tipo);
    if (r.pendencias.length === 0) r.status = "ativo";
    return completo(r);
  },
};
