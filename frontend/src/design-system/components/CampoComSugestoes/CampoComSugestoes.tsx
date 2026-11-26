"use client";

import { Check } from "lucide-react";
import { useEffect, useId, useRef, useState, type InputHTMLAttributes, type Ref } from "react";
import { cx } from "../../cx";
import { Icone } from "../../Icone";
import { aoDigitar, aoTeclar, FECHADO, type EstadoDasSugestoes } from "./logica";

export type OpcaoDeSugestao = {
  /** O texto que vai para o campo ao escolher. */
  valor: string;
  /** Linha de apoio em texto menor (a marca, no modelo do veículo). */
  apoio?: string;
  /** Chave única na lista, quando o `valor` se repete (o mesmo modelo em duas marcas). */
  chave?: string;
};

export type CampoComSugestoesProps = Omit<InputHTMLAttributes<HTMLInputElement>, "className" | "id" | "role" | "list"> & {
  rotulo: string;
  dica?: string;
  erro?: string;
  mono?: boolean;
  cheio?: boolean;
  /** As sugestões, já filtradas por quem usa (a API busca). Lista vazia: o campo funciona como um campo de texto. */
  opcoes: ReadonlyArray<OpcaoDeSugestao>;
  /** A pessoa escolheu uma sugestão (clique, toque ou Enter). Quem usa grava o valor no formulário. */
  aoEscolher: (opcao: OpcaoDeSugestao) => void;
  /** Nome da lista para o leitor de tela. */
  rotuloDaLista?: string;
  /** A opção marcada como escolhida, pela chave (ou pelo valor). */
  escolhida?: string;
  /** Só para o catálogo e as capturas: começa com a lista aberta. */
  abertoNoInicio?: boolean;
  ref?: Ref<HTMLInputElement>;
};

const chaveDe = (o: OpcaoDeSugestao) => o.chave ?? o.valor;

/**
 * Campo de texto com uma lista de sugestões própria (combobox), no lugar do `datalist` do navegador.
 * Focar ou digitar abre a lista abaixo; setas movem, Enter escolhe, Escape fecha, clique fora fecha.
 * Digitar livre continua valendo: o texto do campo é o que se grava, escolhido da lista ou não.
 */
export function CampoComSugestoes({ rotulo, dica, erro, mono, cheio, opcoes, aoEscolher, rotuloDaLista, escolhida, abertoNoInicio = false, ref, onFocus, onChange, onKeyDown, onBlur, ...resto }: CampoComSugestoesProps) {
  const id = useId();
  const [estado, setEstado] = useState<EstadoDasSugestoes>(abertoNoInicio ? aoDigitar() : FECHADO);
  const raiz = useRef<HTMLDivElement>(null);
  const lista = useRef<HTMLUListElement>(null);
  const visivel = estado.aberto && opcoes.length > 0;
  const indice = estado.indice < opcoes.length ? estado.indice : -1;
  const apoio = erro ?? dica;
  const idOpcao = (i: number) => `${id}-opcao-${i}`;

  useEffect(() => {
    if (!estado.aberto) return;
    const aoClicarFora = (e: PointerEvent) => {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setEstado(FECHADO);
    };
    document.addEventListener("pointerdown", aoClicarFora);
    return () => document.removeEventListener("pointerdown", aoClicarFora);
  }, [estado.aberto]);

  // A opção em foco fica à vista quando a lista rola.
  useEffect(() => {
    if (visivel && indice >= 0) lista.current?.querySelector(`#${CSS.escape(idOpcao(indice))}`)?.scrollIntoView?.({ block: "nearest" });
  });

  const escolher = (i: number) => {
    const opcao = opcoes[i];
    setEstado(FECHADO);
    if (opcao) aoEscolher(opcao);
  };

  return (
    <div ref={raiz} className={cx("wl-field", erro && "wl-field--error", cheio && "wl-field--cheio")}>
      <label className="wl-field__label" htmlFor={id}>
        {rotulo}
      </label>
      <div className="wl-sugestoes">
        <input
          ref={ref}
          id={id}
          className={cx("wl-input", mono && "wl-mono")}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={visivel}
          aria-controls={`${id}-lista`}
          aria-activedescendant={visivel && indice >= 0 ? idOpcao(indice) : undefined}
          aria-invalid={erro ? true : undefined}
          aria-describedby={apoio ? `${id}-dica` : undefined}
          autoComplete="off"
          {...resto}
          onFocus={(e) => {
            setEstado(aoDigitar());
            onFocus?.(e);
          }}
          onChange={(e) => {
            setEstado(aoDigitar());
            onChange?.(e);
          }}
          onKeyDown={(e) => {
            const r = aoTeclar(estado, e.key, opcoes.length);
            if (r.daLista) {
              e.preventDefault();
              // Não deixa o Escape fechar também a gaveta ou o diálogo em volta.
              e.stopPropagation();
            }
            setEstado(r.estado);
            if (r.escolher !== null) escolher(r.escolher);
            onKeyDown?.(e);
          }}
          onBlur={(e) => {
            setEstado(FECHADO);
            onBlur?.(e);
          }}
        />
        <ul ref={lista} id={`${id}-lista`} role="listbox" aria-label={rotuloDaLista ?? rotulo} className="wl-menu" hidden={!visivel}>
          {opcoes.map((o, i) => {
            const marcada = escolhida !== undefined && escolhida === chaveDe(o);
            return (
              <li
                key={chaveDe(o)}
                id={idOpcao(i)}
                role="option"
                aria-selected={marcada}
                className={cx("wl-menu__item", i === indice && "wl-menu__item--foco")}
                // Segura o foco no campo: o clique escolhe sem o blur fechar a lista antes.
                onPointerDown={(e) => e.preventDefault()}
                onClick={() => escolher(i)}
                onPointerMove={() => i !== indice && setEstado({ aberto: true, indice: i })}
              >
                <span className="wl-menu__texto">
                  <span>{o.valor}</span>
                  {o.apoio && <span className="wl-sugestoes__apoio">{o.apoio}</span>}
                </span>
                {marcada && <Icone de={Check} />}
              </li>
            );
          })}
        </ul>
      </div>
      {apoio && (
        <span id={`${id}-dica`} className="wl-field__hint">
          {apoio}
        </span>
      )}
    </div>
  );
}
