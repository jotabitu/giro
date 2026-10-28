import {
  AlertCircle,
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
  Truck,
  Undo2,
  UserCog,
  Users,
  Wallet,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type { Eu, GrupoNavegacao, Navegacao } from "@/lib/api";

/** Rota e ícone de cada `chave` de item de menu. O que aparece e o rótulo vêm da API (`eu.navegacao`, USR-05). */
const DESTINOS: Record<string, { href: string; icone: LucideIcon }> = {
  inicio: { href: "/inicio", icone: LayoutGrid },
  aprovacoes: { href: "/aprovacoes", icone: CheckCheck },
  veiculos: { href: "/veiculos", icone: Car },
  movimentacoes: { href: "/veiculos/movimentacoes", icone: Truck },
  locacoes: { href: "/locacoes", icone: KeyRound },
  vendas: { href: "/vendas", icone: Tag },
  clientes: { href: "/clientes", icone: Users },
  manutencoes: { href: "/manutencoes", icone: Wrench },
  caixa: { href: "/financeiro/caixa", icone: Wallet },
  receber: { href: "/financeiro/receber", icone: Receipt },
  despesas: { href: "/financeiro/despesas", icone: CreditCard },
  reembolsos: { href: "/financeiro/reembolsos", icone: Undo2 },
  pendencias_pagamento: { href: "/financeiro/pendencias-pagamento", icone: AlertCircle },
  comissoes: { href: "/financeiro/comissoes", icone: Percent },
  conciliacao: { href: "/financeiro/conciliacao", icone: ArrowLeftRight },
  relatorios: { href: "/relatorios", icone: BarChart3 },
  config: { href: "/admin/configuracoes", icone: Settings },
  marca: { href: "/admin/marca", icone: Palette },
  filiais: { href: "/admin/filiais", icone: Building2 },
  usuarios: { href: "/admin/usuarios", icone: UserCog },
  assinatura: { href: "/admin/assinatura", icone: Gauge },
  auditoria: { href: "/admin/auditoria", icone: ShieldCheck },
  // Itens próprios do menu do início (docs/api/contas.md). Rotas conforme a tabela "Rotas do menu" de docs/telas/README.md (T-055).
  agenda: { href: "/vistorias", icone: CalendarCheck },
  avarias: { href: "/vistorias/avarias", icone: AlertTriangle },
  consultar_veiculo: { href: "/veiculos", icone: Search },
  contas_a_pagar: { href: "/financeiro/despesas", icone: CreditCard },
  caixa_e_bancos: { href: "/financeiro/caixa", icone: Landmark },
  propostas: { href: "/vendas?aba=propostas", icone: Tag },
  minhas_vendas: { href: "/vendas", icone: Tag },
  veiculos_a_venda: { href: "/veiculos?status=a_venda", icone: Car },
  minhas_comissoes: { href: "/financeiro/comissoes", icone: Percent },
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

const caminhoDe = (href: string) => href.split("?")[0];
/** Compara só o caminho: `?aba=` e `?status=` não entram na rota ativa. */
const estaEm = (rota: string, href: string) => {
  const caminho = caminhoDe(href);
  return rota === caminho || rota.startsWith(`${caminho}/`);
};

/** A pessoa vê o item no menu? Seção sem módulo ainda (ex.: Manutenções, fase 2) fica escondida até o item existir (T-128). */
export function temNoMenu(nav: Navegacao, chave: string): boolean {
  return nav.menu_completo.some((g) => g.itens.some((i) => i.chave === chave));
}

const chavesDe = (grupos: GrupoNavegacao[]) => grupos.flatMap((g) => g.itens.map((i) => i.chave));
const abreRota = (grupos: GrupoNavegacao[], rota: string) => chavesDe(grupos).some((c) => DESTINOS[c] && estaEm(rota, DESTINOS[c].href));

/** O menu da tela inicial vale no início e nas rotas que os itens dele abrem (só o caminho, com sub-rotas); no resto vale o completo (USR-05). */
export function gruposDaRota(nav: Navegacao, rotaAtual: string): GrupoNavegacao[] {
  const noMenuDoInicio = estaEm(rotaAtual, nav.inicio.rota) || abreRota(nav.menu_inicio, rotaAtual);
  return noMenuDoInicio && nav.menu_inicio.length > 0 ? nav.menu_inicio : nav.menu_completo;
}

/**
 * A pessoa pode abrir esta rota? Vale o que o menu do perfil mostra (menu do início e menu completo), mais as telas
 * que o menu não lista mas que um item dele leva a (D-26, USR-09). A API continua respondendo 403 ao que o perfil não pode ler.
 */
export function rotaPermitida(eu: Pick<Eu, "pode" | "navegacao">, rota: string): boolean {
  const { pode, navegacao: nav } = eu;
  if (estaEm(rota, nav.inicio.rota) || estaEm(rota, "/mais")) return true;
  const noMenu = (...chaves: string[]) => chaves.some((c) => chavesDe(nav.menu_completo).includes(c) || chavesDe(nav.menu_inicio).includes(c));
  if (rota === "/locacoes/nova") return pode.locacoes_criar && noMenu("locacoes");
  if (/^\/locacoes\/\d+\/(vistoria|devolucao)(\/|$)/.test(rota)) return pode.vistorias_fazer;
  // A ficha da locação abre da lista, da ficha do cliente (financeiro, para receber) e da lista de avarias (vistoriador).
  if (/^\/locacoes\/\d+$/.test(rota)) return noMenu("locacoes", "receber", "clientes", "avarias");
  // Exportar dados abre pelo botão da Auditoria e é do mesmo perfil (administrador).
  if (rota === "/admin/exportar") return noMenu("auditoria");
  // O ramo abre pelo cartão de Configurações e é só do administrador (PLT-12).
  if (rota === "/admin/ramo") return pode.administracao;
  // O controle do suporte abre pelo cartão de Configurações e é só do administrador.
  if (rota === "/admin/suporte") return pode.administracao;
  // Empresa e marca: simular e salvar são só do administrador (docs/api/empresas.md, "Escrita da marca").
  if (rota === "/admin/marca") return pode.administracao;
  // Passos do assistente de implantação: Administração, só do administrador (CA-027-16).
  if (rota === "/implantacao" || rota.startsWith("/implantacao/")) return pode.administracao;
  if (rota === "/clientes/novo") return pode.clientes_cadastrar && noMenu("clientes");
  // Quem só lê a frota (`ver`: vendedor e financeiro, USR-09) abre a lista e a ficha, não o cadastro nem a edição.
  if (/^\/veiculos\/\d+\/editar$/.test(rota)) return pode.veiculos === "editar" && noMenu("veiculos");
  if (rota === "/veiculos/novo") return pode.veiculos === "editar" && noMenu("veiculos");
  // Movimentações (MOV-02, USR-05): o quadro, a Nova movimentação e a chegada valem para quem tem o item no menu; ficam fora do "Veículos".
  if (rota === "/veiculos/movimentacoes" || rota.startsWith("/veiculos/movimentacoes/")) return noMenu("movimentacoes");
  return abreRota(nav.menu_completo, rota) || abreRota(nav.menu_inicio, rota);
}

/** Liga o menu pronto da API às rotas e aos ícones, com a rota ativa e os contadores. Chave desconhecida fica de fora. */
export function montarMenu(grupos: GrupoNavegacao[], rotaAtual: string, contadores: Record<string, number | null> = {}): GrupoMontado[] {
  // Itens diferentes podem dividir o caminho (ex.: Frota e Veículos à venda) ou um conter o outro (Veículos e Movimentações):
  // fica ativo só o de caminho mais longo; em empate, o primeiro.
  const candidatos = grupos.flatMap((g) =>
    g.itens.flatMap((i) => {
      const href = DESTINOS[i.chave]?.href;
      return href && estaEm(rotaAtual, href) ? [{ chave: i.chave, tamanho: caminhoDe(href)?.length ?? 0 }] : [];
    }),
  );
  const ativoChave = candidatos.reduce<{ chave: string; tamanho: number } | null>((melhor, c) => (!melhor || c.tamanho > melhor.tamanho ? c : melhor), null)?.chave;
  return grupos
    .map((g) => ({
      rotulo: g.grupo ?? undefined,
      itens: g.itens.flatMap((i): ItemMontado[] => {
        const destino = DESTINOS[i.chave];
        if (!destino) return [];
        const total = i.contador ? contadores[i.contador] : null;
        const ativo = i.chave === ativoChave;
        return [{ chave: i.chave, rotulo: i.rotulo, href: destino.href, icone: destino.icone, ativo, total: total || undefined }];
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
  const base = HREF_BARRA[chave] ?? DESTINOS[chave]?.href;
  if (!base) return undefined;
  const [caminho, queryDaRota] = base.split("?");
  const query = [queryDaRota, filtro].filter(Boolean).join("&");
  // Reembolso e pendência não têm página de detalhe: o "Para hoje" leva à lista, onde a ação está.
  const semDetalhe = chave === "reembolsos" || chave === "pendencias_pagamento";
  return `${caminho}${id !== undefined && !semDetalhe ? `/${id}` : ""}${query ? `?${query}` : ""}`;
}
