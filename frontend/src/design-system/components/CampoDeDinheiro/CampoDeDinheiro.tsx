"use client";

import type { ClipboardEvent, FormEvent, InputHTMLAttributes } from "react";
import { TextField, type TextFieldProps } from "../TextField/TextField";
import { centavosDoColado, mascaraDinheiro } from "./logica";

type PropsDoDinheiro = { prefixo?: boolean; onChange?: InputHTMLAttributes<HTMLInputElement>["onChange"]; onPaste?: InputHTMLAttributes<HTMLInputElement>["onPaste"] };

const gravar = (input: HTMLInputElement, valor: string): void => {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  setter?.call(input, valor);
  input.dispatchEvent(new Event("input", { bubbles: true }));
};

/**
 * Props do input de dinheiro: a máscara é aplicada no próprio evento, antes de `onChange` ler `e.target.value`,
 * então serve a campo controlado, a `register` do React Hook Form e a `Controller`. Colar "5.000,00" ou "5000" dá R$ 5.000,00.
 */
export function propsDeDinheiro({ prefixo = false, onChange, onPaste }: PropsDoDinheiro) {
  return {
    inputMode: "numeric" as const,
    autoComplete: "off",
    onChange: (e: FormEvent<HTMLInputElement> & { target: HTMLInputElement }) => {
      const mascarado = mascaraDinheiro(e.target.value, prefixo);
      if (e.target.value !== mascarado) e.target.value = mascarado;
      onChange?.(e as never);
    },
    onPaste: (e: ClipboardEvent<HTMLInputElement>) => {
      onPaste?.(e);
      if (e.defaultPrevented) return;
      e.preventDefault();
      gravar(e.currentTarget, mascaraDinheiro(centavosDoColado(e.clipboardData.getData("text")), prefixo));
    },
  };
}

export type CampoDeDinheiroProps = TextFieldProps & {
  /** Mostra "R$ " na frente do número. Só onde a tela já mostrava; sem ele, só "5.000,00". */
  prefixo?: boolean;
};

/** Campo de valor em reais com a máscara ao vivo. O texto do campo é o que `centavosDoTexto` e `centavosDoCampo` leem. */
export function CampoDeDinheiro({ prefixo, onChange, onPaste, ...resto }: CampoDeDinheiroProps) {
  return <TextField {...resto} {...propsDeDinheiro({ prefixo, onChange, onPaste })} />;
}

/** O mesmo comportamento num `<input>` solto, para as linhas de tabela e planos que montam o próprio rótulo. */
export function InputDeDinheiro({ prefixo, onChange, onPaste, className, ...resto }: InputHTMLAttributes<HTMLInputElement> & { prefixo?: boolean }) {
  return <input {...resto} className={className ?? "wl-input"} {...propsDeDinheiro({ prefixo, onChange, onPaste })} />;
}
