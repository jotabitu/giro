"use client";

import { Search } from "lucide-react";
import { useEffect, useRef, useState, type InputHTMLAttributes } from "react";
import { cx } from "../../cx";
import { Icone } from "../../Icone";

export type SearchFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "className" | "type" | "aria-label"> & {
  /** Diga o que dá para buscar ("Buscar placa, cliente ou contrato"). */
  placeholder: string;
  /** Ctrl+K (⌘K no Mac) foca a busca. Padrão: ligado. */
  atalho?: boolean;
  cheio?: boolean;
};

export function SearchField({ placeholder, atalho = true, cheio, ...resto }: SearchFieldProps) {
  const ref = useRef<HTMLInputElement>(null);
  const [rotuloAtalho, setRotuloAtalho] = useState("Ctrl K");

  useEffect(() => {
    if (!atalho) return;
    if (/Mac|iPhone|iPad/.test(navigator.platform)) setRotuloAtalho("⌘K");
    const aoTeclar = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [atalho]);

  return (
    <label className={cx("wl-search", cheio && "wl-search--cheio")}>
      <Icone de={Search} />
      <input ref={ref} type="search" placeholder={placeholder} aria-label="Buscar" {...resto} />
      {atalho && (
        <span className="wl-kbd" aria-hidden="true">
          {rotuloAtalho}
        </span>
      )}
    </label>
  );
}
