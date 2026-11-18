"use client";

import type { MouseEvent, ReactNode } from "react";

export const ID_TITULO_PLANOS = "planos-titulo";

/**
 * Botão geral "Começar teste grátis" da landing (T-490, decisão do dono): desce até a seção Planos da própria
 * página, com rolagem suave (instantânea em prefers-reduced-motion) e o foco no título da seção. Sem JavaScript,
 * o href="#planos" faz o mesmo salto. Quem vem da landing não vê os planos duas vezes: o botão de cada plano é que
 * abre a /compra já com ele.
 */
export function IrParaPlanos({ className, children }: { className: string; children: ReactNode }) {
  function aoClicar(evento: MouseEvent<HTMLAnchorElement>) {
    const secao = document.getElementById("planos");
    const titulo = document.getElementById(ID_TITULO_PLANOS);
    if (!secao || !titulo) return;
    evento.preventDefault();
    const reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    secao.scrollIntoView({ behavior: reduzir ? "auto" : "smooth", block: "start" });
    titulo.focus({ preventScroll: true });
    history.replaceState(null, "", "#planos");
  }
  return (
    <a className={className} href="#planos" onClick={aoClicar}>
      {children}
    </a>
  );
}
