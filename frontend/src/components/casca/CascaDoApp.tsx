"use client";

import { useQuery } from "@tanstack/react-query";
import { Car, Ellipsis, KeyRound, LayoutGrid, LogOut, Menu, Plus, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Icone, IconButton, SeletorDeFilial, Sidebar, type GrupoMenu } from "@/design-system";
import { relatorios } from "@/lib/api";
import { useFilial } from "@/lib/filial-escolhida";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";
import { destinosDaBarra, gruposDaRota, montarMenu, rotaPermitida } from "@/lib/menu";
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
  const marca = useMarcaDaEmpresa();
  const grupos = useGruposDoMenu();
  const filial = useFilial();
  // Só com mais de uma opção no escopo (USR-07); com uma filial e sem "Todas", o seletor nem aparece.
  const seletor = filial?.escolha ? (
    <SeletorDeFilial
      filiais={filial.filiais.map((f) => ({ id: String(f.id), nome: f.nome, cidade: f.cidade }))}
      valor={filial.escolha}
      aoMudar={filial.trocar}
      permiteTodas={filial.podeEscolherTodas}
    />
  ) : undefined;
  return <Sidebar componenteLink={Link} marca={{ nome: marca.nome, logoSrc: marca.logo?.url, iniciais: marca.iniciais }} seletorDeFilial={seletor} grupos={grupos} />;
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
      <Link href={href} aria-label={rotulo} className="grid size-[48px] shrink-0 place-items-center rounded-full bg-brand text-on-brand">
        {icone}
      </Link>
    );
  }
  return (
    <Link href={href} aria-label={rotulo} aria-current={ativo ? "page" : undefined} className={`flex h-[48px] min-w-0 flex-1 basis-0 flex-col items-center justify-center rounded-pill ${ativo ? "bg-solid text-on-solid" : "text-ink"}`}>
      {icone}
      {ativo && <span className="max-w-full truncate text-caption font-medium leading-none">{rotulo}</span>}
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
    <nav aria-label="Navegação principal" className="fixed inset-x-4 bottom-4 z-30 flex items-center gap-1 rounded-pill bg-surface p-2 shadow-pop md:hidden">
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

/** D-26: a rota que o menu do perfil não mostra responde só com o aviso, sem chamar a API da tela. */
export function GuardaDeRota({ children }: { children: ReactNode }) {
  const { eu } = useSessao();
  const rota = usePathname();
  if (rotaPermitida(eu, rota)) return <>{children}</>;
  return (
    <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
      Seu perfil não tem acesso a esta página.
    </p>
  );
}

/** Casca do app: sidebar de 280px no desktop; no celular, cabeçalho com gaveta e barra inferior (Início, Veículos, +, Locações, Mais). */
export function CascaDoApp({ children }: { children: ReactNode }) {
  const marca = useMarcaDaEmpresa();
  const rota = usePathname();
  const [gaveta, setGaveta] = useState(false);
  // O assistente de implantação tem a própria moldura (passos no lugar do menu): sem sidebar nem barra inferior.
  if (rota === "/implantacao" || rota.startsWith("/implantacao/")) return <GuardaDeRota>{children}</GuardaDeRota>;
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
            {marca.logo ? (
              // eslint-disable-next-line @next/next/no-img-element -- logo servido pela API (S-12): sempre <img>, nunca inline
              <img src={marca.logo.url} alt="" width={40} height={40} style={{ borderRadius: "inherit", objectFit: "contain" }} />
            ) : (
              marca.iniciais
            )}
          </div>
          <span className="text-heading">{marca.nome}</span>
        </div>
        <IconButton aria-label="Abrir menu" icone={<Icone de={Menu} />} onClick={() => setGaveta(true)} />
      </div>
      <Gaveta aberta={gaveta} aoFechar={() => setGaveta(false)} />

      <main className="min-w-0 flex-1 p-4 pb-[104px] md:p-0"><GuardaDeRota>{children}</GuardaDeRota></main>
      <BarraInferior />
    </div>
  );
}
