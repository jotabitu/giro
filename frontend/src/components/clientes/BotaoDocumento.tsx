"use client";

import { Camera, Check } from "lucide-react";
import { useRef } from "react";
import { Icone } from "@/design-system";
import type { TipoDocumentoCliente } from "@/lib/api";

export const ROTULO_DOCUMENTO: Record<TipoDocumentoCliente, string> = {
  cnh_frente: "CNH · frente",
  cnh_verso: "CNH · verso",
  selfie_documento: "Selfie com documento",
  comprovante_residencia: "Comprovante de residência",
};

/**
 * Envio de um documento do cliente (JPG, PNG ou PDF, até 10 MB; a API confere). No celular abre a câmera.
 * Sem `aoEscolher` o botão fica parado: o documento só pode ser enviado depois que o cadastro é salvo.
 */
export function BotaoDocumento({
  tipo,
  enviado,
  enviando,
  erro,
  aoEscolher,
}: {
  tipo: TipoDocumentoCliente;
  enviado: boolean;
  enviando?: boolean;
  erro?: string;
  aoEscolher?: (arquivo: File) => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const parado = !aoEscolher;
  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        disabled={parado || enviando}
        onClick={() => entrada.current?.click()}
        className={`flex min-h-[56px] items-center gap-3 rounded-md px-4 py-3 text-left text-body disabled:opacity-60 ${enviado ? "bg-surface-sunken" : "border border-dashed border-line bg-surface"}`}
      >
        <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-pill ${enviado ? "bg-success-soft text-success-ink" : "bg-surface-sunken text-ink-muted"}`}>
          <Icone de={enviado ? Check : Camera} />
        </span>
        <span>
          <span className="block">{ROTULO_DOCUMENTO[tipo]}</span>
          <span className="block text-caption text-ink-muted">{enviando ? "Enviando…" : enviado ? "Enviado. Toque para trocar" : parado ? "Salve o cadastro para enviar" : "Toque para enviar"}</span>
        </span>
      </button>
      <input
        ref={entrada}
        type="file"
        hidden
        accept="image/jpeg,image/png,application/pdf"
        aria-label={ROTULO_DOCUMENTO[tipo]}
        onChange={(e) => {
          const arquivo = e.target.files?.[0];
          if (arquivo) aoEscolher?.(arquivo);
          e.target.value = "";
        }}
      />
      {erro && (
        <span role="alert" className="text-caption text-critical-ink">
          {erro}
        </span>
      )}
    </div>
  );
}
