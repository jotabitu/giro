import {
  ArrowLeftRight,
  BarChart3,
  Building2,
  Car,
  CreditCard,
  Gauge,
  KeyRound,
  LayoutGrid,
  Palette,
  Percent,
  Receipt,
  Settings,
  ShieldCheck,
  Tag,
  UserCog,
  Users,
  Wallet,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type { Pode } from "@/lib/api";

export type ItemDoMenu = {
  chave: string;
  rotulo: string;
  href: string;
  icone: LucideIcon;
  /** Chave em `contadores` da API; sem pendência, sem contador. */
  contador?: string;
  /** Só mostra o item quando a API liberou: lê `pode`, nunca o perfil (USR-05). */
  visivel: (pode: Pode) => boolean;
};

export type GrupoDoMenu = { rotulo?: string; itens: ItemDoMenu[] };

// Relação item de menu -> chave `pode` do contrato docs/api/contas.md.
// O contrato não traz uma chave por item de menu; esta tabela é a ponte e deve ser revista com o arquiteto (T-011).
export const MENU: GrupoDoMenu[] = [
  {
    itens: [
      { chave: "inicio", rotulo: "Visão geral", href: "/inicio", icone: LayoutGrid, visivel: (p) => p.painel !== "nao" },
      { chave: "veiculos", rotulo: "Veículos", href: "/veiculos", icone: Car, contador: "veiculos", visivel: (p) => p.veiculos !== "nao" },
    ],
  },
  {
    rotulo: "Operação",
    itens: [
      { chave: "locacoes", rotulo: "Locações", href: "/locacoes", icone: KeyRound, contador: "locacoes", visivel: (p) => p.locacoes_criar || p.vistorias_fazer },
      { chave: "vendas", rotulo: "Vendas", href: "/vendas", icone: Tag, visivel: (p) => p.vendas_criar },
      { chave: "clientes", rotulo: "Clientes", href: "/clientes", icone: Users, visivel: (p) => p.clientes_cadastrar },
      { chave: "manutencoes", rotulo: "Manutenções", href: "/manutencoes", icone: Wrench, contador: "manutencoes", visivel: (p) => p.os_abrir },
    ],
  },
  {
    rotulo: "Financeiro",
    itens: [
      { chave: "caixa", rotulo: "Caixa do dia", href: "/financeiro/caixa", icone: Wallet, visivel: (p) => p.caixa_receber || p.caixa_abrir_fechar },
      { chave: "receber", rotulo: "Contas a receber", href: "/financeiro/receber", icone: Receipt, contador: "receber", visivel: (p) => p.caixa_receber },
      { chave: "despesas", rotulo: "Despesas", href: "/financeiro/despesas", icone: CreditCard, contador: "despesas", visivel: (p) => p.despesas_lancar !== "nao" },
      { chave: "comissoes", rotulo: "Comissões", href: "/financeiro/comissoes", icone: Percent, visivel: (p) => p.financeiro_pagar },
      { chave: "conciliacao", rotulo: "Conciliação", href: "/financeiro/conciliacao", icone: ArrowLeftRight, contador: "conciliacao", visivel: (p) => p.financeiro_pagar },
      { chave: "relatorios", rotulo: "Relatórios", href: "/relatorios", icone: BarChart3, visivel: (p) => p.painel === "todas_filiais" || p.painel === "filial" },
    ],
  },
  {
    rotulo: "Administração",
    itens: [
      { chave: "config", rotulo: "Configurações", href: "/admin/configuracoes", icone: Settings, visivel: (p) => p.administracao },
      { chave: "marca", rotulo: "Empresa e marca", href: "/admin/marca", icone: Palette, visivel: (p) => p.administracao },
      { chave: "filiais", rotulo: "Filiais", href: "/admin/filiais", icone: Building2, visivel: (p) => p.administracao },
      { chave: "usuarios", rotulo: "Usuários", href: "/admin/usuarios", icone: UserCog, contador: "usuarios", visivel: (p) => p.administracao },
      { chave: "assinatura", rotulo: "Assinatura", href: "/admin/assinatura", icone: Gauge, visivel: (p) => p.administracao },
      { chave: "auditoria", rotulo: "Auditoria", href: "/admin/auditoria", icone: ShieldCheck, visivel: (p) => p.administracao },
    ],
  },
];

export type ItemMontado = ItemDoMenu & { ativo: boolean; total?: number };
export type GrupoMontado = { rotulo?: string; itens: ItemMontado[] };

/** Menu do usuário: só o que `pode` libera (sem itens desabilitados), com a rota ativa marcada e os contadores da API. */
export function montarMenu(pode: Pode, rotaAtual: string, contadores: Record<string, number> = {}): GrupoMontado[] {
  return MENU.map((g) => ({
    rotulo: g.rotulo,
    itens: g.itens
      .filter((i) => i.visivel(pode))
      .map((i) => ({
        ...i,
        ativo: rotaAtual === i.href || rotaAtual.startsWith(`${i.href}/`),
        total: i.contador ? contadores[i.contador] : undefined,
      })),
  })).filter((g) => g.itens.length > 0);
}

/** Os cinco destinos da barra inferior no celular. "Mais" abre /mais; o "+" leva à nova locação. */
export function barraInferior(pode: Pode) {
  return {
    inicio: pode.painel !== "nao",
    veiculos: pode.veiculos !== "nao",
    novaLocacao: pode.locacoes_criar,
    locacoes: pode.locacoes_criar || pode.vistorias_fazer,
  };
}
