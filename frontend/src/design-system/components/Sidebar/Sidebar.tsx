import { ChevronDown, Store } from "lucide-react";
import type { ComponentType, ReactNode } from "react";
import { Icone } from "../../Icone";
import { Contador } from "../StatusBadge/StatusBadge";

export type ItemMenu = {
  rotulo: string;
  href: string;
  /** Ícone de 20px (use <Icone />). */
  icone: ReactNode;
  ativo?: boolean;
  /** Pendências reais (contratos a vencer, OS abertas). Sem pendência, sem contador. */
  contador?: number;
};

export type GrupoMenu = {
  /** Rótulo do grupo (Operação, Financeiro). Sem rótulo, os itens ficam soltos no topo. */
  rotulo?: string;
  itens: ReadonlyArray<ItemMenu>;
};

export type MarcaDaSidebar = {
  nome: string;
  /** SVG ou imagem quadrada da empresa. Sem logo, o slot mostra as iniciais. */
  logoSrc?: string;
  iniciais?: string;
};

export type FilialAtiva = { nome: string; cidade: string };

function iniciaisDe(nome: string): string {
  return nome
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function Sidebar({
  marca,
  filial,
  seletorDeFilial,
  grupos,
  componenteLink: Link = "a",
}: {
  marca: MarcaDaSidebar;
  /** Filial ativa, só para mostrar. Esconda quando a empresa tiver uma filial só. */
  filial?: FilialAtiva;
  /** Seletor que troca de filial (<SeletorDeFilial />); tem prioridade sobre `filial`. */
  seletorDeFilial?: ReactNode;
  grupos: ReadonlyArray<GrupoMenu>;
  /** Troque por next/link nas telas (padrão: a). */
  componenteLink?: ComponentType<{ href: string; className?: string; "aria-current"?: "page"; children?: ReactNode }> | "a";
}) {
  return (
    <nav className="wl-sidebar" aria-label="Menu principal">
      <div className="wl-brand-row">
        <div className="wl-logo-slot" aria-hidden="true">
          {marca.logoSrc ? (
            // eslint-disable-next-line @next/next/no-img-element -- logo da empresa vem de URL externa (S3)
            <img src={marca.logoSrc} alt="" width={40} height={40} style={{ borderRadius: "inherit", objectFit: "cover" }} />
          ) : (
            (marca.iniciais ?? iniciaisDe(marca.nome))
          )}
        </div>
        <div className="wl-brand-name">{marca.nome}</div>
      </div>
      {seletorDeFilial}
      {!seletorDeFilial && filial && (
        <div className="wl-switcher">
          <div className="wl-switcher__icon">
            <Icone de={Store} />
          </div>
          <div className="wl-switcher__text">
            <span className="wl-switcher__name">{filial.nome}</span>
            <span className="wl-switcher__sub">{filial.cidade}</span>
          </div>
          <Icone de={ChevronDown} className="wl-muted" />
        </div>
      )}
      {grupos.map((g, i) => (
        <div key={g.rotulo ?? i} style={{ display: "contents" }}>
          {g.rotulo && <div className="wl-nav-label">{g.rotulo}</div>}
          {g.itens.map((item) => (
            <Link key={item.href} href={item.href} className="wl-nav-item" aria-current={item.ativo ? "page" : undefined}>
              {item.icone}
              {item.rotulo}
              {item.contador ? <Contador>{item.contador}</Contador> : null}
            </Link>
          ))}
        </div>
      ))}
    </nav>
  );
}
