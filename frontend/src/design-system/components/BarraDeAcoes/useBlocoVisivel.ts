"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** O que a `BarraDeAcoes` precisa saber do bloco fixo de botões da tela (T-519). */
export type BlocoDosBotoes = {
  /** Marca o elemento do bloco. Uma tela com o bloco em dois lugares (cabeçalho no desktop, pé no celular) usa uma chave para cada. */
  ref: (chave?: string) => (el: Element | null) => void;
  /** Algum elemento do bloco aparece na tela agora. Antes da primeira medida, vale `true`: a barra nasce escondida e não pisca. */
  visivel: boolean;
};

type Observador = { observe(el: Element): void; disconnect(): void };
type FabricaDeObservador = new (aoMudar: (entradas: { target: Element; isIntersecting: boolean }[]) => void) => Observador;

/**
 * Observa os elementos e avisa `aoMudar(true)` quando algum aparece na tela. Sem elemento (a tela não tem o bloco, ou ele está
 * fora do ar) ou sem IntersectionObserver, avisa `false`: sem bloco para olhar, a barra fica à mostra. Devolve quem para de observar.
 */
export function observarBlocos(elementos: Element[], aoMudar: (visivel: boolean) => void, Fabrica: FabricaDeObservador | undefined = globalThis.IntersectionObserver as FabricaDeObservador | undefined): () => void {
  if (!Fabrica || elementos.length === 0) {
    aoMudar(false);
    return () => {};
  }
  const aparece = new Map<Element, boolean>(elementos.map((el) => [el, false]));
  const observador = new Fabrica((entradas) => {
    for (const e of entradas) aparece.set(e.target, e.isIntersecting);
    aoMudar([...aparece.values()].some(Boolean));
  });
  for (const el of elementos) observador.observe(el);
  return () => observador.disconnect();
}

/**
 * Diz se o bloco fixo de botões (no aside, no cabeçalho ou no fim do formulário) está na tela. A `BarraDeAcoes` recebe o retorno
 * em `blocos` e fica escondida enquanto o bloco aparece; ao rolar e ele sair, ela surge.
 */
export function useBlocoVisivel(): BlocoDosBotoes {
  const [elementos, setElementos] = useState<Record<string, Element>>({});
  const [visivel, setVisivel] = useState(true);
  const fabrica = useRef(new Map<string, (el: Element | null) => void>());

  const ref = useCallback((chave = "bloco") => {
    let f = fabrica.current.get(chave);
    if (!f) {
      f = (el) =>
        setElementos((atual) => {
          if (el === null) {
            if (!(chave in atual)) return atual;
            const resto = { ...atual };
            delete resto[chave];
            return resto;
          }
          return atual[chave] === el ? atual : { ...atual, [chave]: el };
        });
      fabrica.current.set(chave, f);
    }
    return f;
  }, []);

  useEffect(() => observarBlocos(Object.values(elementos), setVisivel), [elementos]);

  return { ref, visivel };
}
