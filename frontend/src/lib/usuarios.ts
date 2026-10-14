// Textos de Administração › Usuários. Situação, plano e permissões padrão vêm da API; aqui só rótulos e formatação.
import type { TomStatus } from "@/design-system";
import type { PermissaoDoUsuario, PermissaoExtra, UsuarioDaLista } from "@/lib/api";
import type { Perfil } from "@/lib/api";
import { dataCurta, diaDe } from "@/lib/formatos";

export const ROTULO_DO_PERFIL: Record<Perfil, string> = {
  administrador: "Administrador",
  gerente: "Gerente",
  vendedor: "Vendedor",
  vistoriador: "Vistoriador",
  financeiro: "Financeiro",
};

export const PERFIS: { valor: Perfil; rotulo: string }[] = (Object.keys(ROTULO_DO_PERFIL) as Perfil[]).map((valor) => ({ valor, rotulo: ROTULO_DO_PERFIL[valor] }));

/** Administrador na cor da marca, gerente em sólido, os demais neutros (Admin-Usuarios). */
export const TOM_DO_PERFIL: Record<Perfil, TomStatus> = { administrador: "marca", gerente: "solido", vendedor: "neutro", vistoriador: "neutro", financeiro: "neutro" };

export const ROTULO_DA_PERMISSAO: Record<PermissaoExtra, string> = {
  aprovar_desconto: "Aprovar descontos acima de 5%",
  cancelar_contrato: "Cancelar contratos",
  relatorios_todas_filiais: "Ver relatórios de todas as filiais",
};

/** Texto de apoio de cada permissão: o padrão do perfil (travado) ou o que a marcação muda. */
export function apoioDaPermissao(p: PermissaoDoUsuario, perfil: Perfil, marcada: boolean, filiais: string[]): string {
  if (p.padrao_do_perfil) return `Padrão do perfil ${ROTULO_DO_PERFIL[perfil]}`;
  if (p.chave === "relatorios_todas_filiais") return marcada ? "Vê os relatórios de todas as filiais" : filiais.length ? `Hoje vê só ${filiais.join(", ")}` : "Escolha as filiais dele";
  return "Fica registrado na auditoria";
}

export type SituacaoDoUsuario = { rotulo: string; tom: TomStatus };

export function situacaoDoUsuario(u: Pick<UsuarioDaLista, "status" | "dois_fatores_ativo">): SituacaoDoUsuario {
  if (u.status === "convite_pendente") return { rotulo: "Convite enviado", tom: "info" };
  if (u.status === "desativado") return { rotulo: "Desativado", tom: "neutro" };
  return { rotulo: u.dois_fatores_ativo ? "Ativo · 2FA" : "Ativo", tom: "sucesso" };
}

/** "agora", "há 2 h", "ontem", "12 set" ou "—" (nunca entrou). */
export function ultimoAcesso(iso: string | null, agora: Date): string {
  if (!iso) return "—";
  const passou = agora.getTime() - new Date(iso).getTime();
  if (passou < 5 * 60_000) return "agora";
  if (diaDe(iso) === diaDe(agora.toISOString())) {
    const min = Math.floor(passou / 60_000);
    return min < 60 ? `há ${min} min` : `há ${Math.floor(min / 60)} h`;
  }
  const ontem = diaDe(new Date(agora.getTime() - 24 * 3_600_000).toISOString());
  return diaDe(iso) === ontem ? "ontem" : dataCurta(iso);
}

/** "Centro" no lugar de "Filial Centro", como nas telas; administrador e quem vê tudo: "Todas". */
export function filiaisDoUsuario(u: Pick<UsuarioDaLista, "filiais" | "todas_filiais">): string {
  if (u.todas_filiais) return "Todas";
  return u.filiais.map((f) => f.nome.replace(/^Filial /, "")).join(", ") || "—";
}
