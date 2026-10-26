"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { Button, Icone } from "@/design-system";
import { ModelosDeContrato } from "@/components/contratos/ModelosDeContrato";
import { RodapeDoPasso } from "./RodapeDoPasso";

// Referência: docs/telas/html/Onboarding-Contrato-Desktop.dc.html e Onboarding-Contrato-Mobile.dc.html.
// Mesmas rotas e mesmo painel da tela Modelos de contrato (/admin/contratos): modelo pronto, prévia, edição e publicar.
// O passo `contrato` é marcado pela API quando o primeiro modelo de locação é publicado (IMP-04, IMP-07).

/** Passo "Modelo de contrato" do assistente. `aoPublicar` relê o andamento: o "Continuar" vale quando a API marca o passo (só o modelo de locação conta, IMP-04). */
export function PassoContrato({ feito, voltarPara, pularPara, aoPublicar, aoContinuar }: { feito: boolean; voltarPara: string; pularPara: string; aoPublicar: () => void; aoContinuar: () => void }) {
  const [criando, setCriando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-6 md:wl-panel" aria-labelledby="passo-contrato-titulo">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1">
          <h1 id="passo-contrato-titulo" className="text-title md:text-display">
            Seu contrato de locação
          </h1>
          <p className="mt-1.5 mb-0 text-body text-ink-muted">Comece por um modelo pronto, veja a prévia, ajuste o texto se precisar e publique. Contratos já assinados mantêm o texto da versão em que foram assinados.</p>
        </div>
        <Button variante="solido" icone={<Icone de={Plus} />} onClick={() => setCriando(true)}>
          Novo modelo
        </Button>
      </div>

      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}
      {!feito && <p className="m-0 text-caption text-ink-muted">Para continuar, publique ao menos um modelo de locação.</p>}

      <ModelosDeContrato criando={criando} aoFecharCriacao={() => setCriando(false)} aoAvisar={setAviso} aoPublicar={aoPublicar} />

      <p className="m-0 text-caption text-ink-muted">Este é um modelo de partida. Peça ao seu advogado para revisar antes de usar com clientes.</p>

      <RodapeDoPasso voltarPara={voltarPara} pularPara={pularPara} podeContinuar={feito} aoContinuar={aoContinuar} />
    </section>
  );
}
