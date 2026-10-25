"use client";

import { ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Icone } from "@/design-system";
import { useSessao } from "@/lib/sessao";
import { ModelosDeContrato } from "./ModelosDeContrato";

// Referência: docs/telas/html/Contratos-Modelos-Desktop.dc.html e Contratos-Modelos-Mobile.dc.html.
// Lista, texto, campos automáticos e versões vêm de /api/contratos/modelos* (IMP-04, S-09, LOC-15); a tela não monta contrato.

/** Administração › Modelos de contrato (T-363). */
export function TelaDeModelosDeContrato() {
  const { eu } = useSessao();
  const [criando, setCriando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  if (!eu.pode.administracao)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador mexe nos modelos de contrato.
      </p>
    );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end gap-4">
        <Link href="/admin/configuracoes" aria-label="Voltar" className="wl-icon-btn size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Modelos de contrato</h1>
          <p className="m-0 mt-1.5 text-body text-ink-muted">Os textos usados ao gerar o contrato. Contratos já assinados mantêm o texto da versão em que foram assinados.</p>
        </div>
        <div className="ml-auto">
          <Button variante="solido" icone={<Icone de={Plus} />} onClick={() => setCriando(true)}>
            Novo modelo
          </Button>
        </div>
      </header>

      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}

      <ModelosDeContrato criando={criando} aoFecharCriacao={() => setCriando(false)} aoAvisar={setAviso} />
    </div>
  );
}
