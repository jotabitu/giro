"use client";

import { ChevronRight, LogOut } from "lucide-react";
import Link from "next/link";
import { Contador, Icone } from "@/design-system";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";
import { useSessao } from "@/lib/sessao";
import { useGruposDoMenu } from "./CascaDoApp";

const ROTULO_PERFIL = {
  administrador: "Administrador",
  gerente: "Gerente",
  vendedor: "Vendedor",
  vistoriador: "Vistoriador",
  financeiro: "Financeiro",
} as const;

function iniciais(nome: string) {
  return nome.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

/** Menu Mais do celular (Menu-Mobile): perfil, módulos por grupo e Sair. Só aparece o que a API liberou. */
export function MenuMais() {
  const { eu, sair } = useSessao();
  const marca = useMarcaDaEmpresa();
  const grupos = useGruposDoMenu();
  const filial = eu.filiais.length === 1 ? ` · ${eu.filiais[0]?.nome}` : "";

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-title">Mais</h1>
        <p className="text-caption text-ink-muted">
          {marca.nome}
          {filial}
        </p>
      </header>

      <div className="flex items-center gap-3 rounded-xl bg-surface p-4">
        <div className="wl-logo-slot rounded-full" aria-hidden="true">
          {iniciais(eu.nome)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-body-strong">{eu.nome}</div>
          <div className="text-caption text-ink-muted">{ROTULO_PERFIL[eu.perfil]}</div>
        </div>
      </div>

      {grupos.map((g, i) => (
        <section key={g.rotulo ?? i} aria-label={g.rotulo ?? "Atalhos"} className="flex flex-col gap-2">
          {g.rotulo && <h2 className="px-2 text-overline uppercase text-ink-muted">{g.rotulo}</h2>}
          <ul className="rounded-xl bg-surface px-4">
            {g.itens.map((item) => (
              <li key={item.href} className="border-b border-line last:border-b-0">
                <Link href={item.href} className="flex min-h-[56px] items-center gap-3 py-2">
                  {item.icone}
                  <span className="flex-1 text-body">{item.rotulo}</span>
                  {item.contador ? <Contador>{item.contador}</Contador> : null}
                  <Icone de={ChevronRight} className="text-ink-muted" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}

      <button type="button" onClick={() => void sair()} className="flex min-h-[56px] items-center gap-3 rounded-xl bg-surface px-4 text-body">
        <Icone de={LogOut} />
        Sair
      </button>
    </div>
  );
}
