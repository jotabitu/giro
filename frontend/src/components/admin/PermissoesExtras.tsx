"use client";

import type { PermissaoDoUsuario, Perfil, PermissaoExtra } from "@/lib/api";
import { apoioDaPermissao, ROTULO_DA_PERMISSAO } from "@/lib/usuarios";

/** Caixas de permissão extra. As que o perfil já dá aparecem marcadas e travadas (docs/api/contas.md). */
export function PermissoesExtras({
  permissoes,
  perfil,
  marcadas,
  filiais,
  aoMudar,
}: {
  permissoes: PermissaoDoUsuario[];
  perfil: Perfil;
  marcadas: PermissaoExtra[];
  /** Nomes das filiais escolhidas, para o apoio de "relatórios de todas as filiais". */
  filiais: string[];
  aoMudar: (m: PermissaoExtra[]) => void;
}) {
  return (
    <fieldset>
      <legend className="wl-field__label mb-1">Permissões extras</legend>
      {permissoes.map((p) => {
        const marcada = p.padrao_do_perfil || marcadas.includes(p.chave);
        return (
          <label key={p.chave} className="flex min-h-[44px] items-start gap-3 border-b border-line py-3 text-body last:border-b-0">
            <input
              type="checkbox"
              checked={marcada}
              disabled={p.padrao_do_perfil}
              onChange={(e) => aoMudar(e.target.checked ? [...marcadas, p.chave] : marcadas.filter((x) => x !== p.chave))}
              className="mt-px size-[22px] shrink-0 accent-[var(--solid)]"
            />
            <span>
              {ROTULO_DA_PERMISSAO[p.chave]}
              <small className="block text-caption text-ink-muted">{apoioDaPermissao(p, perfil, marcada, filiais)}</small>
            </span>
          </label>
        );
      })}
    </fieldset>
  );
}

/** Escolha das filiais com acesso. Administrador vê todas, por definição, e a lista some. */
export function FiliaisDoAcesso({ opcoes, marcadas, aoMudar, erro }: { opcoes: { id: number; nome: string }[]; marcadas: number[]; aoMudar: (ids: number[]) => void; erro?: string }) {
  return (
    <fieldset>
      <legend className="wl-field__label mb-1">Filiais com acesso</legend>
      {opcoes.map((f) => (
        <label key={f.id} className="flex min-h-[44px] items-center gap-3 text-body">
          <input
            type="checkbox"
            checked={marcadas.includes(f.id)}
            onChange={(e) => aoMudar(e.target.checked ? [...marcadas, f.id] : marcadas.filter((x) => x !== f.id))}
            className="size-[22px] shrink-0 accent-[var(--solid)]"
          />
          {f.nome}
        </label>
      ))}
      {erro && (
        <span role="alert" className="text-caption text-critical-ink">
          {erro}
        </span>
      )}
    </fieldset>
  );
}
