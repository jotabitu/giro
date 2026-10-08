"use client";

import { Building2, Check, ChevronDown, Store } from "lucide-react";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { cx } from "../../cx";
import { Icone } from "../../Icone";
import { deveMostrar, destinoNaLista, itemAtivo, montarItens, TODAS, type OpcaoFilial } from "./logica";

export type SeletorDeFilialProps = {
  /** Só as filiais da pessoa (USR-07); a API já filtra. */
  filiais: ReadonlyArray<OpcaoFilial>;
  /** Id da filial ativa, ou "todas". */
  valor: string;
  aoMudar: (id: string) => void;
  /** Administrador pode escolher "Todas as filiais". */
  permiteTodas?: boolean;
};

/**
 * Seletor de filial do topo do menu: o botão mostra a filial ativa e abre a lista.
 * Com uma filial só (e sem "Todas"), não aparece. Teclado: Enter, espaço ou seta para baixo abre;
 * setas, Home e End movem; Enter ou espaço escolhe; Escape fecha e devolve o foco ao botão.
 */
export function SeletorDeFilial({ filiais, valor, aoMudar, permiteTodas = false }: SeletorDeFilialProps) {
  const id = useId();
  const [aberto, setAberto] = useState(false);
  const [indice, setIndice] = useState(0);
  const raiz = useRef<HTMLDivElement>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const lista = useRef<HTMLUListElement>(null);

  const itens = montarItens(filiais, permiteTodas);
  const ativo = itemAtivo(itens, valor);

  useEffect(() => {
    if (!aberto) return;
    const aoClicarFora = (e: PointerEvent) => {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("pointerdown", aoClicarFora);
    return () => document.removeEventListener("pointerdown", aoClicarFora);
  }, [aberto]);

  useEffect(() => {
    if (aberto) lista.current?.focus();
  }, [aberto]);

  if (!deveMostrar(filiais, permiteTodas) || !ativo) return null;

  const abrir = () => {
    setIndice(Math.max(0, itens.findIndex((i) => i.id === ativo.id)));
    setAberto(true);
  };

  const fechar = (devolverFoco: boolean) => {
    setAberto(false);
    if (devolverFoco) botao.current?.focus();
  };

  const escolher = (i: number) => {
    const item = itens[i];
    if (item && item.id !== ativo.id) aoMudar(item.id);
    fechar(true);
  };

  const aoTeclarNoBotao = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      abrir();
    }
  };

  const aoTeclarNaLista = (e: KeyboardEvent<HTMLUListElement>) => {
    if (e.key === "Escape") {
      // Não deixa o Escape fechar também a gaveta ou o diálogo em volta.
      e.preventDefault();
      e.stopPropagation();
      fechar(true);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      escolher(indice);
    } else if (e.key === "Tab") {
      fechar(false);
    } else {
      const destino = destinoNaLista(e.key, indice, itens.length);
      if (destino !== null) {
        e.preventDefault();
        setIndice(destino);
      }
    }
  };

  const idOpcao = (i: number) => `${id}-opcao-${i}`;

  return (
    <div ref={raiz} className="wl-seletor">
      <button
        ref={botao}
        type="button"
        className="wl-switcher wl-switcher--botao"
        aria-haspopup="listbox"
        aria-expanded={aberto}
        aria-controls={`${id}-lista`}
        onClick={() => (aberto ? fechar(false) : abrir())}
        onKeyDown={aoTeclarNoBotao}
      >
        <span className="wl-switcher__icon">
          <Icone de={ativo.id === TODAS ? Building2 : Store} />
        </span>
        <span className="wl-switcher__text">
          <span className="wl-switcher__name">{ativo.nome}</span>
          <span className="wl-switcher__sub">{ativo.detalhe}</span>
        </span>
        <Icone de={ChevronDown} className="wl-muted" />
      </button>
      {aberto && (
        <ul
          ref={lista}
          id={`${id}-lista`}
          className="wl-menu"
          role="listbox"
          aria-label="Filial"
          tabIndex={-1}
          aria-activedescendant={idOpcao(indice)}
          onKeyDown={aoTeclarNaLista}
        >
          {itens.map((item, i) => (
            <li
              key={item.id}
              id={idOpcao(i)}
              role="option"
              aria-selected={item.id === ativo.id}
              className={cx("wl-menu__item", i === indice && "wl-menu__item--foco")}
              onClick={() => escolher(i)}
              onPointerMove={() => setIndice(i)}
            >
              <span className="wl-menu__texto">
                <span className="wl-switcher__name">{item.nome}</span>
                <span className="wl-switcher__sub">{item.detalhe}</span>
              </span>
              {item.id === ativo.id && <Icone de={Check} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
