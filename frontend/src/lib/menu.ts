import {
  AlertTriangle,
  ArrowLeftRight,
  BarChart3,
  Building2,
  CalendarCheck,
  Car,
  CheckCheck,
  CreditCard,
  Gauge,
  KeyRound,
  Landmark,
  LayoutGrid,
  Palette,
  Percent,
  Receipt,
  Search,
  Settings,
  ShieldCheck,
  Tag,
  UserCog,
  Users,
  Wallet,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type { GrupoNavegacao, Navegacao } from "@/lib/api";

/** Rota e ícone de cada `chave` de item de menu. O que aparece e o rótulo vêm da API (`eu.navegacao`, USR-05). */
const DESTINOS: Record<string, { href: string; icone: LucideIcon }> = {
  inicio: { href: "/inicio", icone: LayoutGrid },
  aprovacoes: { href: "/aprovacoes", icone: CheckCheck },
  veiculos: { href: "/veiculos", icone: Car },
  locacoes: { href: "/locacoes", icone: KeyRound },
  vendas: { href: "/vendas", icone: Tag },
  clientes: { href: "/clientes", icone: Users },
  manutencoes: { href: "/manutencoes", icone: Wrench },
  caixa: { href: "/financeiro/caixa", icone: Wallet },
  receber: { href: "/financeiro/receber", icone: Receipt },
  despesas: { href: "/financeiro/despesas", icone: CreditCard },
  comissoes: { href: "/financeiro/comissoes", icone: Percent },
  conciliacao: { href: "/financeiro/conciliacao", icone: ArrowLeftRight },
  relatorios: { href: "/relatorios", icone: BarChart3 },
  config: { href: "/admin/configuracoes", icone: Settings },
  marca: { href: "/admin/marca", icone: Palette },
  filiais: { href: "/admin/filiais", icone: Building2 },
  usuarios: { href: "/admin/usuarios", icone: UserCog },
  assinatura: { href: "/admin/assinatura", icone: Gauge },
  auditoria: { href: "/admin/auditoria", icone: ShieldCheck },
  // Itens próprios do menu do início (docs/api/contas.md). Rotas a confirmar com as telas de cada módulo.
  agenda: { href: "/vistorias", icone: CalendarCheck },
  avarias: { href: "/avarias", icone: AlertTriangle },
  consultar_veiculo: { href: "/veiculos/consultar", icone: Search },
  contas_a_pagar: { href: "/financeiro/pagar", icone: CreditCard },
  caixa_e_bancos: { href: "/financeiro/bancos", icone: Landmark },
  propostas: { href: "/propostas", icone: Tag },
  minhas_vendas: { href: "/vendas/minhas", icone: Tag },
  veiculos_a_venda: { href: "/vendas/veiculos", icone: Car },
  minhas_comissoes: { href: "/financeiro/minhas-comissoes", icone: Percent },
};

export type ItemMontado = {
  chave: string;
  rotulo: string;
  href: string;
  icone: LucideIcon;
  ativo: boolean;
  /** Número do contador; `undefined` sem pendência ou quando o módulo ainda não existe (`null` na API). */
  total?: number;
};
export type GrupoMontado = { rotulo?: string; itens: ItemMontado[] };

const estaEm = (rota: string, href: string) => rota === href || rota.startsWith(`${href}/`);

/** O menu da tela inicial só vale na rota inicial do perfil; nas telas compartilhadas vale o completo (USR-05). */
export function gruposDaRota(nav: Navegacao, rotaAtual: string): GrupoNavegacao[] {
  const noInicio = estaEm(rotaAtual, nav.inicio.rota);
  return noInicio && nav.menu_inicio.length > 0 ? nav.menu_inicio : nav.menu_completo;
}

/** Liga o menu pronto da API às rotas e aos ícones, com a rota ativa e os contadores. Chave desconhecida fica de fora. */
export function montarMenu(grupos: GrupoNavegacao[], rotaAtual: string, contadores: Record<string, number | null> = {}): GrupoMontado[] {
  return grupos
    .map((g) => ({
      rotulo: g.grupo ?? undefined,
      itens: g.itens.flatMap((i): ItemMontado[] => {
        const destino = DESTINOS[i.chave];
        if (!destino) return [];
        const total = i.contador ? contadores[i.contador] : null;
        return [{ chave: i.chave, rotulo: i.rotulo, href: destino.href, icone: destino.icone, ativo: estaEm(rotaAtual, destino.href), total: total || undefined }];
      }),
    }))
    .filter((g) => g.itens.length > 0);
}

export type DestinoDaBarra = { chave: string; href: string; rotulo: string };

const ROTULO_BARRA: Record<string, string> = { inicio: "Início", veiculos: "Veículos", nova_locacao: "Nova locação", locacoes: "Locações", mais: "Mais" };
const HREF_BARRA: Record<string, string> = { nova_locacao: "/locacoes/nova", mais: "/mais" };

/** Os destinos da barra inferior do celular, na ordem e com o filtro que a API mandou em `barra_celular`. */
export function destinosDaBarra(chaves: string[]): DestinoDaBarra[] {
  return chaves.flatMap((chave) => {
    const href = HREF_BARRA[chave] ?? DESTINOS[chave]?.href;
    return href ? [{ chave, href, rotulo: ROTULO_BARRA[chave] ?? chave }] : [];
  });
}

/** Rota de um `destino` do painel (`{ chave, filtro?, id? }`) ou de um destino de ação ("nova_locacao"). Sem rota conhecida, `undefined`. */
export function hrefDoDestino(chave: string, filtro?: string, id?: number): string | undefined {
  const base = HREF_BARRA[chave] ?? DESTINOS[chave]?.href ?? (chave === "reembolsos" ? "/financeiro/reembolsos" : undefined);
  if (!base) return undefined;
  return `${base}${id !== undefined ? `/${id}` : ""}${filtro ? `?${filtro}` : ""}`;
}
