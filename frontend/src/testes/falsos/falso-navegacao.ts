// Faz o papel de `navegacao` em GET /api/auth/eu/ (docs/api/contas.md, "Menu e início") enquanto contas não está ligada na API real.
// Espelha backend/apps/contas/navegacao.py (T-071): cada item é definido uma vez, com a permissão, o recurso do plano,
// a atividade e o módulo. A tela nunca monta menu; só lê o resultado.
import type { GrupoNavegacao, ItemNavegacao, Navegacao, Perfil, Pode, VarianteInicio } from "@/lib/api/tipos";

export type Atividade = "aluga" | "vende" | "ambos";

/** Apps entregues (`GIRO_MODULOS_ATIVOS`). No falso valem todos, para o desenvolvimento ver o menu cheio. */
export const TODOS_OS_MODULOS = [
  "aprovacoes", "auditoria", "clientes", "configuracoes", "contas", "empresas", "filiais", "financeiro",
  "locacoes", "manutencao", "plataforma", "relatorios", "veiculos", "vendas", "vistorias",
] as const;

/** Recursos do plano Profissional. */
export const TODOS_OS_RECURSOS = [
  "locacoes_vistoria", "contas_receber", "contrato_digital", "vendas_comissoes", "manutencao_despesas",
  "relatorios", "dominio_proprio", "api_integracoes", "suporte_prioritario",
] as const;

export type ContextoNavegacao = {
  recursos: readonly string[];
  atividade: Atividade;
  modulos: readonly string[];
};

const CONTEXTO_PADRAO: ContextoNavegacao = { recursos: TODOS_OS_RECURSOS, atividade: "ambos", modulos: TODOS_OS_MODULOS };

type Definicao = {
  chave: string;
  rotulo: string;
  contador?: string;
  permissao?: (p: Pode) => boolean;
  recurso?: string;
  atividade?: "aluga" | "vende";
  modulo?: string;
};

/** Gerente, administrador ou permissão extra de aprovar (APR, USR-03). */
const decidePedidos = (p: Pode) => ["aprova", "sim"].includes(p.desconto_acima_limite) || ["aprova", "sim"].includes(p.locacoes_cancelar);
const vePainel = (p: Pode) => p.painel === "todas_filiais" || p.painel === "filial";

const DEFINICOES: Definicao[] = [
  { chave: "inicio", rotulo: "Visão geral" },
  { chave: "aprovacoes", rotulo: "Aprovações", contador: "aprovacoes", permissao: decidePedidos, modulo: "aprovacoes" },
  { chave: "veiculos", rotulo: "Veículos", contador: "veiculos", permissao: (p) => p.veiculos !== "nao", modulo: "veiculos" },
  { chave: "locacoes", rotulo: "Locações", contador: "locacoes", permissao: (p) => p.locacoes_criar, recurso: "locacoes_vistoria", atividade: "aluga", modulo: "locacoes" },
  { chave: "vendas", rotulo: "Vendas", permissao: (p) => p.vendas_criar, recurso: "vendas_comissoes", atividade: "vende", modulo: "vendas" },
  { chave: "clientes", rotulo: "Clientes", permissao: (p) => p.clientes_cadastrar || p.caixa_receber, modulo: "clientes" },
  { chave: "manutencoes", rotulo: "Manutenções", contador: "manutencoes", permissao: (p) => p.os_abrir, recurso: "manutencao_despesas", modulo: "manutencao" },
  { chave: "caixa", rotulo: "Caixa do dia", permissao: (p) => p.caixa_receber || p.caixa_abrir_fechar, recurso: "contas_receber", modulo: "financeiro" },
  { chave: "receber", rotulo: "Contas a receber", contador: "receber", permissao: (p) => p.caixa_receber, recurso: "contas_receber", modulo: "financeiro" },
  { chave: "despesas", rotulo: "Despesas", contador: "despesas", permissao: (p) => p.despesas_lancar !== "nao", recurso: "manutencao_despesas", modulo: "financeiro" },
  { chave: "comissoes", rotulo: "Comissões", permissao: (p) => p.financeiro_pagar, recurso: "vendas_comissoes", modulo: "vendas" },
  { chave: "conciliacao", rotulo: "Conciliação", contador: "conciliacao", permissao: (p) => p.financeiro_pagar, recurso: "contas_receber", modulo: "financeiro" },
  { chave: "relatorios", rotulo: "Relatórios", permissao: vePainel, recurso: "relatorios", modulo: "relatorios" },
  { chave: "config", rotulo: "Configurações", permissao: (p) => p.administracao, modulo: "configuracoes" },
  { chave: "marca", rotulo: "Empresa e marca", permissao: (p) => p.administracao, modulo: "empresas" },
  { chave: "filiais", rotulo: "Filiais", permissao: (p) => p.administracao, modulo: "filiais" },
  { chave: "usuarios", rotulo: "Usuários", contador: "usuarios", permissao: (p) => p.administracao, modulo: "contas" },
  { chave: "assinatura", rotulo: "Assinatura", permissao: (p) => p.administracao, modulo: "plataforma" },
  { chave: "auditoria", rotulo: "Auditoria", permissao: (p) => p.administracao, modulo: "auditoria" },
  // Itens próprios das telas iniciais.
  { chave: "agenda", rotulo: "Vistorias de hoje", contador: "agenda", permissao: (p) => p.vistorias_fazer, recurso: "locacoes_vistoria", atividade: "aluga", modulo: "vistorias" },
  { chave: "consultar_veiculo", rotulo: "Consultar veículo", permissao: (p) => p.veiculos !== "nao", modulo: "veiculos" },
  { chave: "avarias", rotulo: "Avarias abertas", contador: "avarias", permissao: (p) => p.vistorias_fazer, recurso: "locacoes_vistoria", atividade: "aluga", modulo: "vistorias" },
  { chave: "propostas", rotulo: "Propostas", contador: "propostas", permissao: (p) => p.vendas_criar, recurso: "vendas_comissoes", atividade: "vende", modulo: "vendas" },
  { chave: "minhas_vendas", rotulo: "Minhas vendas", permissao: (p) => p.vendas_criar, recurso: "vendas_comissoes", atividade: "vende", modulo: "vendas" },
  { chave: "veiculos_a_venda", rotulo: "Veículos à venda", permissao: (p) => p.vendas_criar, recurso: "vendas_comissoes", atividade: "vende", modulo: "vendas" },
  { chave: "minhas_comissoes", rotulo: "Minhas comissões", permissao: (p) => p.vendas_criar, recurso: "vendas_comissoes", atividade: "vende", modulo: "vendas" },
  { chave: "contas_a_pagar", rotulo: "Contas a pagar", contador: "contas_a_pagar", permissao: (p) => p.financeiro_pagar, recurso: "manutencao_despesas", modulo: "financeiro" },
  { chave: "caixa_e_bancos", rotulo: "Caixa e bancos", permissao: (p) => p.caixa_abrir_fechar, recurso: "contas_receber", modulo: "financeiro" },
];
const ITENS = new Map(DEFINICOES.map((d) => [d.chave, d]));

/** Uma entrada é a chave do item, ou `[chave, rótulo]` para trocar o rótulo nessa tela. */
type Entrada = string | readonly [string, string];
type Grupos = readonly (readonly [string | null, readonly Entrada[]])[];

/** Tabela "Itens do menu_completo" do contrato, na ordem. */
const menuCompleto = (rotuloDoInicio: string): Grupos => [
  [null, [["inicio", rotuloDoInicio], "aprovacoes", "veiculos"]],
  ["Operação", ["locacoes", "vendas", "clientes", "manutencoes"]],
  ["Financeiro", ["caixa", "receber", "despesas", "comissoes", "conciliacao", "relatorios"]],
  ["Administração", ["config", "marca", "filiais", "usuarios", "assinatura", "auditoria"]],
];

/** O rótulo de `inicio` no menu completo é o do início do perfil (USR-05). */
const ROTULO_DO_INICIO: Partial<Record<VarianteInicio, string>> = { gerente: "Visão da filial", vendedor: "Início", financeiro: "Início" };

/** Menu da tela inicial de cada variante (telas Gerente, Vendedor, Vistoriador e Financeiro). */
const MENU_INICIO: Partial<Record<VarianteInicio, Grupos>> = {
  gerente: [
    [null, [["inicio", "Visão da filial"], "aprovacoes", "veiculos"]],
    ["Operação", ["locacoes", "vendas", "clientes", "manutencoes"]],
    ["Filial", [["caixa", "Caixa da filial"], "relatorios"]],
  ],
  vendedor: [
    [null, [["inicio", "Início"]]],
    ["Operação", ["locacoes", "veiculos", "clientes"]],
    ["Vendas", ["propostas", "minhas_vendas", "veiculos_a_venda", "minhas_comissoes"]],
  ],
  vistoriador: [[null, ["agenda", "consultar_veiculo", "avarias"]]],
  financeiro: [[null, [["inicio", "Início"], "receber", "contas_a_pagar", "caixa_e_bancos", "veiculos", "comissoes"]]],
};

const BARRA_CELULAR = ["inicio", "veiculos", "nova_locacao", "locacoes", "mais"];

function aparece(d: Definicao, pode: Pode, ctx: ContextoNavegacao): boolean {
  if (d.modulo && !ctx.modulos.includes(d.modulo)) return false;
  if (d.recurso && !ctx.recursos.includes(d.recurso)) return false;
  if (d.atividade && ctx.atividade !== d.atividade && ctx.atividade !== "ambos") return false;
  return d.permissao ? d.permissao(pode) : true;
}

/** Despesas: o número é do que a pessoa pode aprovar; quem só lança fica sem contador. */
const contadorDe = (d: Definicao, pode: Pode): string | null => (d.chave === "despesas" && !pode.despesas_aprovar ? null : (d.contador ?? null));

function montar(grupos: Grupos, pode: Pode, ctx: ContextoNavegacao): GrupoNavegacao[] {
  return grupos
    .map(([grupo, entradas]): GrupoNavegacao => ({
      grupo,
      itens: entradas.flatMap((e): ItemNavegacao[] => {
        const [chave, rotulo] = typeof e === "string" ? [e, undefined] : e;
        const d = ITENS.get(chave)!;
        return aparece(d, pode, ctx) ? [{ chave, rotulo: rotulo ?? d.rotulo, contador: contadorDe(d, pode) }] : [];
      }),
    }))
    .filter((g) => g.itens.length > 0);
}

/** `contexto` troca plano, atividade e módulos; sem ele, vale o plano Profissional, aluga e vende, todos os módulos. */
export function navegacaoFalsa(_perfil: Perfil, pode: Pode, variante: VarianteInicio, contexto: Partial<ContextoNavegacao> = {}): Navegacao {
  const ctx = { ...CONTEXTO_PADRAO, ...contexto };
  const inicio = MENU_INICIO[variante];
  // Vistoriador: um menu só, igual ao do início, sem Visão geral nem Locações (USR-05, T-141).
  const completo = variante === "vistoriador" && inicio ? montar(inicio, pode, ctx) : montar(menuCompleto(ROTULO_DO_INICIO[variante] ?? "Visão geral"), pode, ctx);
  const visiveis = new Set(completo.flatMap((g) => g.itens.map((i) => i.chave)));
  const barra: Record<string, boolean> = {
    inicio: true,
    veiculos: visiveis.has("veiculos") || visiveis.has("consultar_veiculo"),
    nova_locacao: visiveis.has("locacoes") && pode.locacoes_criar,
    locacoes: visiveis.has("locacoes"),
    mais: true,
  };
  return {
    inicio: { rota: "/inicio", variante },
    menu_inicio: inicio ? montar(inicio, pode, ctx) : completo,
    menu_completo: completo,
    barra_celular: BARRA_CELULAR.filter((c) => barra[c]),
  };
}
