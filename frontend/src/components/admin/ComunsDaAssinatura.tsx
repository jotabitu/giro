"use client";

import { Copy } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";
import { Button, Icone } from "@/design-system";

/** Copia um link de pagamento do parceiro (boleto ou página do cartão). */
export function LinkDePagamento({ rotulo, link }: { rotulo: string; link: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        compacto
        icone={<Icone de={Copy} />}
        onClick={() => {
          void navigator.clipboard?.writeText(link).then(() => setCopiado(true));
        }}
      >
        {rotulo}
      </Button>
      {copiado && (
        <span role="status" className="text-caption text-ink-muted">
          Copiado.
        </span>
      )}
    </div>
  );
}

/** Código de pagamento (Pix copia e cola ou linha digitável) com o botão Copiar; o QR é desenhado a partir do copia e cola. */
export function CodigoDePagamento({ rotulo, codigo, comQr = false, botao = "Copiar" }: { rotulo: string; codigo: string; comQr?: boolean; botao?: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <div className="flex flex-col gap-2 rounded-md bg-surface-sunken p-4">
      <span className="text-caption text-ink-muted">{rotulo}</span>
      {comQr && (
        <div className="self-center rounded-md bg-white p-3" role="img" aria-label="QR do Pix">
          <QRCodeSVG value={codigo} size={168} bgColor="#ffffff" fgColor="#111114" />
        </div>
      )}
      <code className="wl-mono break-all text-caption">{codigo}</code>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          compacto
          icone={<Icone de={Copy} />}
          onClick={() => {
            void navigator.clipboard?.writeText(codigo).then(() => setCopiado(true));
          }}
        >
          {botao}
        </Button>
        {copiado && (
          <span role="status" className="text-caption text-ink-muted">
            Copiado.
          </span>
        )}
      </div>
    </div>
  );
}
