import { Bell, Building2, Download, FileText, Palette, Plug, ShieldCheck, Star, Tag, UserCog, type LucideIcon } from "lucide-react";
import type { ChaveDoCartao, ImplantacaoDeConfiguracoes } from "@/lib/api";

/** Rota e ícone de cada cartão de Configurações (docs/api/configuracoes.md, "Rotas dos cartões"). Título e resumo vêm da API. */
export const CARTOES: Record<ChaveDoCartao, { href: string; icone: LucideIcon }> = {
  marca: { href: "/admin/marca", icone: Palette },
  filiais: { href: "/admin/filiais", icone: Building2 },
  usuarios: { href: "/admin/usuarios", icone: UserCog },
  precos: { href: "/admin/precos", icone: Tag },
  modelos_contrato: { href: "/admin/contratos", icone: FileText },
  integracoes: { href: "/admin/integracoes", icone: Plug },
  notificacoes: { href: "/admin/notificacoes", icone: Bell },
  assinatura: { href: "/admin/assinatura", icone: Star },
  auditoria: { href: "/admin/auditoria", icone: ShieldCheck },
  exportar: { href: "/admin/auditoria/exportar", icone: Download },
};

/** Destino do botão da faixa da implantação; o assistente ainda não tem contrato por passo, então abre o assistente. */
export function destinoDaAcao(acao: NonNullable<ImplantacaoDeConfiguracoes["acao"]>): string {
  return acao.destino === "nova_locacao" ? "/locacoes/nova" : "/implantacao";
}
