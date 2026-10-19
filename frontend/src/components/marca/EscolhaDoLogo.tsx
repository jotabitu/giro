"use client";

import { Upload } from "lucide-react";
import { useRef } from "react";
import { Button, Icone } from "@/design-system";
import { ACEITA_LOGO, AJUDA_DO_LOGO } from "@/lib/marca-edicao";
import { LogoOuIniciais } from "./PreviaDaMarca";

/**
 * Logo da marca. `admin`: "Trocar logo" e "Remover" (Admin-Marca). `assistente`: "Enviar logo" tracejado e a frase
 * "Sem logo, usamos as iniciais" (Onboarding-Marca). O formato e o tamanho quem confere é a API.
 */
export function EscolhaDoLogo({
  logoUrl,
  iniciais,
  variante,
  desligado,
  erro,
  aoEscolher,
  aoRemover,
}: {
  logoUrl: string | null;
  iniciais: string;
  variante: "admin" | "assistente";
  desligado?: boolean;
  erro?: string;
  aoEscolher: (arquivo: File) => void;
  aoRemover: () => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const assistente = variante === "assistente";
  return (
    <div className={erro ? "wl-field wl-field--error" : "wl-field"}>
      <span className="wl-field__label" id={`logo-${variante}`}>
        Logo
      </span>
      <div className="flex flex-wrap items-center gap-4">
        <LogoOuIniciais logoUrl={logoUrl} iniciais={iniciais} tamanho={72} fonte={22} />
        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap gap-2">
            <Button compacto={!assistente} variante={assistente ? "quieto" : "padrao"} icone={assistente ? <Icone de={Upload} /> : undefined} disabled={desligado} onClick={() => entrada.current?.click()}>
              {assistente ? "Enviar logo" : "Trocar logo"}
            </Button>
            {!assistente && logoUrl && (
              <Button compacto variante="quieto" disabled={desligado} onClick={aoRemover}>
                Remover
              </Button>
            )}
          </div>
          <span className="wl-field__hint">{erro ?? (assistente ? "PNG ou SVG, fundo transparente. Sem logo, usamos as iniciais." : AJUDA_DO_LOGO)}</span>
        </div>
        <input
          ref={entrada}
          type="file"
          accept={ACEITA_LOGO}
          hidden
          aria-labelledby={`logo-${variante}`}
          onChange={(e) => {
            const arquivo = e.target.files?.[0];
            if (arquivo) aoEscolher(arquivo);
            e.target.value = "";
          }}
        />
      </div>
    </div>
  );
}
