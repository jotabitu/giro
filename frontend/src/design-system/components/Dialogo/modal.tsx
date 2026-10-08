"use client";

import { X } from "lucide-react";
import { useEffect, useId, useRef, type MouseEvent, type ReactNode } from "react";
import { cx } from "../../cx";
import { Icone } from "../../Icone";
import { IconButton } from "../Button/Button";

/**
 * Base de Dialogo e Gaveta: o elemento nativo <dialog> aberto com showModal().
 * O navegador cuida do foco preso, do Escape, do fundo inerte e de devolver o foco a quem abriu.
 * É controlado: quem usa decide `aberto`; Escape, o botão Fechar e o clique fora só chamam `aoFechar`.
 */
export function CaixaModal({
  aberto,
  aoFechar,
  titulo,
  descricao,
  classe,
  fecharAoClicarFora = true,
  children,
  acoes,
  rotuloFechar,
}: {
  aberto: boolean;
  aoFechar: () => void;
  titulo: string;
  descricao?: string;
  classe: string;
  fecharAoClicarFora?: boolean;
  children?: ReactNode;
  acoes?: ReactNode;
  rotuloFechar: string;
}) {
  const id = useId();
  const caixa = useRef<HTMLDialogElement>(null);
  const corpo = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const d = caixa.current;
    if (!d) return;
    if (aberto && !d.open) {
      d.showModal();
      // Foco inicial: o elemento marcado com data-autofocus; senão o próprio painel, para o leitor de tela
      // ler o título antes de o Tab chegar ao primeiro controle.
      const alvo = d.querySelector<HTMLElement>("[data-autofocus]") ?? corpo.current;
      alvo?.focus();
    } else if (!aberto && d.open) {
      d.close();
    }
  }, [aberto]);

  // Fecha o dialog se o componente sair da tela com ele aberto.
  useEffect(() => {
    const d = caixa.current;
    return () => {
      if (d?.open) d.close();
    };
  }, []);

  const aoClicar = (e: MouseEvent<HTMLDialogElement>) => {
    // O <dialog> não tem padding: um clique nele mesmo é um clique no fundo.
    if (fecharAoClicarFora && e.target === e.currentTarget) aoFechar();
  };

  return (
    <dialog
      ref={caixa}
      className={cx("wl-modal", classe)}
      aria-labelledby={`${id}-titulo`}
      aria-describedby={descricao ? `${id}-descricao` : undefined}
      onCancel={(e) => {
        e.preventDefault();
        aoFechar();
      }}
      onClick={aoClicar}
    >
      <div ref={corpo} className="wl-modal__corpo" tabIndex={-1}>
        <header className="wl-modal__cab">
          <h2 id={`${id}-titulo`} className="wl-modal__titulo">
            {titulo}
          </h2>
          <IconButton aria-label={rotuloFechar} icone={<Icone de={X} />} quieto compacto onClick={aoFechar} />
        </header>
        {descricao && (
          <p id={`${id}-descricao`} className="wl-modal__descricao">
            {descricao}
          </p>
        )}
        {aberto && <div className="wl-modal__conteudo">{children}</div>}
        {aberto && acoes && <footer className="wl-modal__acoes">{acoes}</footer>}
      </div>
    </dialog>
  );
}
