"use client";

import { useQuery } from "@tanstack/react-query";
import { Car, Ellipsis, KeyRound, LayoutGrid, LogOut, Menu, Plus, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Icone, IconButton, Sidebar, type GrupoMenu } from "@/design-system";
import { relatorios } from "@/lib/api";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";
import { destinosDaBarra, gruposDaRota, montarMenu } from "@/lib/menu";
import { useSessao } from "@/lib/sessao";

/** Menu do usuário no formato do componente Sidebar: o que a API mandou em `eu.navegacao`, com os contadores (a cada 60 s). */
export function useGruposDoMenu(): GrupoMenu[] {
  const { eu } = useSessao();
  const rota = usePathname();
  const { data } = useQuery({ queryKey: ["contadores"], queryFn: async () => (await relatorios.contadores()).contadores, staleTime: 60_000, refetchInterval: 60_000 });
  return montarMenu(gruposDaRota(eu.navegacao, rota), rota, data).map((g) => ({
    rotulo: g.rotulo,
    itens: g.itens.map((i) => ({ rotulo: i.rotulo, href: i.href, icone: <Icone de={i.icone} />, ativo: i.ativo, contador: i.total })),
  }));
}

export function SidebarDaEmpresa() {
  const { eu } = useSessao();
  const marca = useMarcaDaEmpresa();
  const grupos = useGruposDoMenu();
  // Esconde o seletor quando a pessoa tem uma filial só (docs/design-system/components/Sidebar).
  // Sem lista de filiais no componente ainda: mostra a primeira. Ver handoff T-020.
  const filial = eu.filiais.length > 1 ? { nome: eu.filiais[0]?.nome ?? "", cidade: "" } : undefined;
  return <Sidebar componenteLink={Link} marca={{ nome: marca.nome, logoSrc: marca.logoUrl }} filial={filial} grupos={grupos} />;
}

function BotaoSair() {
  const { sair } = useSessao();
  return (
    <button type="button" onClick={() => void sair()} className="flex h-[44px] items-center gap-3 rounded-pill px-4 text-body text-ink hover:bg-surface-sunken">
      <Icone de={LogOut} />
      Sair
    </button>
  );
}

function Gaveta({ aberta, aoFechar }: { aberta: boolean; aoFechar: () => void }) {
  const fechar = useRef<HTMLButtonElement>(null);
  const rota = usePathname();

  useEffect(() => {
    if (!aberta) return;
    fechar.current?.focus();
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && aoFechar();
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aberta, aoFechar]);

  // Navegou: fecha.
  useEffect(() => {
    aoFechar();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só reage à troca de rota
  }, [rota]);

  if (!aberta) return null;
  return (
    <div className="fixed inset-0 z-40 md:hidden">
      <button type="button" aria-label="Fechar menu" className="absolute inset-0 bg-ink opacity-40" onClick={aoFechar} tabIndex={-1} />
      <div role="dialog" aria-modal="true" aria-label="Menu" className="absolute inset-y-0 left-0 flex w-[320px] max-w-[88vw] flex-col gap-2 overflow-y-auto bg-canvas p-3 shadow-pop">
        <div className="flex justify-end">
          <button ref={fechar} type="button" aria-label="Fechar menu" onClick={aoFechar} className="grid size-[44px] place-items-center rounded-full bg-surface">
            <Icone de={X} />
          </button>
        </div>
        <SidebarDaEmpresa />
        <div className="rounded-xl bg-surface p-2">
          <BotaoSair />
        </div>
      </div>
    </div>
  );
}

function ItemBarra({ href, rotulo, icone, ativo, destaque }: { href: string; rotulo: string; icone: ReactNode; ativo: boolean; destaque?: boolean }) {
  if (destaque) {
    return (
      <Link href={href} aria-label={rotulo} className="grid size-[48px] place-items-center rounded-full bg-brand text-on-brand">
        {icone}
      </Link>
    );
  }
  return (
    <Link href={href} aria-label={rotulo} aria-current={ativo ? "page" : undefined} className={`flex h-[48px] min-w-[48px] items-center justify-center gap-2 rounded-pill px-3 ${ativo ? "bg-solid text-on-solid" : "text-ink"}`}>
      {icone}
      {ativo && <span className="text-caption font-medium">{rotulo}</span>}
    </Link>
  );
}

const ICONE_DA_BARRA = { inicio: LayoutGrid, veiculos: Car, nova_locacao: Plus, locacoes: KeyRound, mais: Ellipsis } as const;

/** Os destinos vêm de `eu.navegacao.barra_celular`; a tela só decide o ícone e o destaque do "+". */
function BarraInferior() {
  const { eu } = useSessao();
  const rota = usePathname();
  const ativo = (h: string) => rota === h || rota.startsWith(`${h}/`);
  return (
    <nav aria-label="Navegação principal" className="fixed inset-x-4 bottom-4 z-30 flex items-center justify-between rounded-pill bg-surface p-2 shadow-pop md:hidden">
      {destinosDaBarra(eu.navegacao.barra_celular).map((d) => (
        <ItemBarra
          key={d.chave}
          href={d.href}
          rotulo={d.rotulo}
          ativo={d.chave !== "nova_locacao" && ativo(d.href)}
          destaque={d.chave === "nova_locacao"}
          icone={<Icone de={ICONE_DA_BARRA[d.chave as keyof typeof ICONE_DA_BARRA] ?? Ellipsis} />}
        />
      ))}
    </nav>
  );
}

/** Casca do app: sidebar de 280px no desktop; no celular, cabeçalho com gaveta e barra inferior (Início, Veículos, +, Locações, Mais). */
export function CascaDoApp({ children }: { children: ReactNode }) {
  const marca = useMarcaDaEmpresa();
  const [gaveta, setGaveta] = useState(false);
  return (
    <div className="min-h-screen bg-canvas md:flex md:gap-6 md:p-6">
      <aside className="sticky top-6 hidden h-[calc(100vh-48px)] shrink-0 flex-col gap-2 overflow-y-auto md:flex">
        <SidebarDaEmpresa />
        <div className="rounded-xl bg-surface p-2">
          <BotaoSair />
        </div>
      </aside>

      <div className="flex items-center justify-between gap-3 p-4 pb-0 md:hidden">
        <div className="flex items-center gap-3">
          <div className="wl-logo-slot" aria-hidden="true">
            {marca.nome.slice(0, 2).toUpperCase()}
          </div>
          <span className="text-heading">{marca.nome}</span>
        </div>
        <IconButton aria-label="Abrir menu" icone={<Icone de={Menu} />} onClick={() => setGaveta(true)} />
      </div>
      <Gaveta aberta={gaveta} aoFechar={() => setGaveta(false)} />

      <main className="min-w-0 flex-1 p-4 pb-[104px] md:p-0">{children}</main>
      <BarraInferior />
    </div>
  );
}
