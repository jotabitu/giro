"use client";

import { useId, useRef, type ClipboardEvent, type KeyboardEvent } from "react";
import { cx } from "../../cx";
import { aplicarApagar, aplicarEntrada, aplicarExcluir, completo, destinoDaTecla, soDigitos, TAMANHO_PADRAO } from "./logica";

export type CodigoVerificacaoProps = {
  /** Só dígitos, da esquerda para a direita, sem buracos. */
  valor: string;
  aoMudar: (valor: string) => void;
  /** Chamado uma vez quando o último dígito entra (digitado, colado ou preenchido pelo celular). */
  aoCompletar?: (valor: string) => void;
  /** Texto do rótulo, acima das caixas ("Código do aplicativo"). */
  rotulo: string;
  /** Diz o problema e como resolver ("Código incorreto. Confira o horário do celular e tente de novo."). */
  erro?: string;
  tamanho?: number;
  disabled?: boolean;
  autoFocus?: boolean;
};

/**
 * Campo de código de verificação (2 etapas): uma caixa por dígito.
 * Aceita colar o código inteiro, preenchimento automático do celular (one-time-code),
 * avanço ao digitar e volta com Backspace, setas, Home e End.
 */
export function CodigoVerificacao({ valor, aoMudar, aoCompletar, rotulo, erro, tamanho = TAMANHO_PADRAO, disabled, autoFocus }: CodigoVerificacaoProps) {
  const id = useId();
  const caixas = useRef<Array<HTMLInputElement | null>>([]);

  const irPara = (i: number) => {
    const caixa = caixas.current[i];
    if (!caixa) return;
    caixa.focus();
    caixa.select();
  };

  const aplicar = (r: { valor: string; foco: number }) => {
    if (r.valor !== valor) {
      aoMudar(r.valor);
      if (completo(r.valor, tamanho)) aoCompletar?.(r.valor);
    }
    irPara(r.foco);
  };

  const aoTeclar = (e: KeyboardEvent<HTMLInputElement>, i: number) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "Backspace") {
      e.preventDefault();
      aplicar(aplicarApagar(valor, i, tamanho));
    } else if (e.key === "Delete") {
      e.preventDefault();
      aplicar(aplicarExcluir(valor, i));
    } else {
      const destino = destinoDaTecla(e.key, i, tamanho);
      if (destino !== null) {
        e.preventDefault();
        irPara(destino);
      }
    }
  };

  const aoColar = (e: ClipboardEvent<HTMLInputElement>, i: number) => {
    e.preventDefault();
    const texto = soDigitos(e.clipboardData.getData("text"));
    // Colar na primeira caixa substitui o código todo; nas outras, a partir dela.
    if (texto) aplicar(aplicarEntrada(valor, i, texto, tamanho));
  };

  const descricaoId = erro ? `${id}-erro` : undefined;

  return (
    <div className="wl-otp-campo">
      <div className="wl-field__label" id={`${id}-rotulo`}>
        {rotulo}
      </div>
      <div className="wl-otp" role="group" aria-labelledby={`${id}-rotulo`} aria-describedby={descricaoId}>
        {Array.from({ length: tamanho }, (_, i) => (
          <input
            key={i}
            ref={(el) => {
              caixas.current[i] = el;
            }}
            className={cx("wl-otp__digito", erro && "wl-otp__digito--erro")}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            autoComplete="one-time-code"
            autoFocus={autoFocus && i === 0}
            maxLength={i === 0 ? tamanho : 1}
            value={valor[i] ?? ""}
            disabled={disabled}
            aria-label={`Dígito ${i + 1} de ${tamanho}`}
            aria-invalid={erro ? true : undefined}
            onFocus={(e) => e.currentTarget.select()}
            onChange={(e) => {
              const inserido = (e.nativeEvent as InputEvent).data ?? e.target.value;
              aplicar(aplicarEntrada(valor, i, inserido, tamanho));
            }}
            onKeyDown={(e) => aoTeclar(e, i)}
            onPaste={(e) => aoColar(e, i)}
          />
        ))}
      </div>
      {erro && (
        <div id={descricaoId} className="wl-otp__erro" role="alert">
          {erro}
        </div>
      )}
    </div>
  );
}
