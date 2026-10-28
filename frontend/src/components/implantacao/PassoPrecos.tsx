"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { Button, Icone } from "@/design-system";
import { CategoriasDePreco } from "@/components/precos/CategoriasDePreco";
import { RodapeDoPasso } from "./RodapeDoPasso";

// Referência: docs/telas/html/Onboarding-Precos-Desktop.dc.html e Onboarding-Precos-Mobile.dc.html.
// Mesmas rotas e mesmo painel da tela Precos (/admin/precos): o passo mostra só categorias e preço; extras e planos especiais ficam lá.
// O passo `precos` é marcado pela API quando a primeira categoria ganha preço vigente (IMP-07).

/** Passo "Tabela de preços" do assistente. */
export function PassoPrecos({ feito, voltarPara, pularPara, aoContinuar }: { feito: boolean; voltarPara: string; pularPara: string; aoContinuar: () => void }) {
  const [criando, setCriando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-6 md:wl-panel" aria-labelledby="passo-precos-titulo">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1">
          <h1 id="passo-precos-titulo" className="text-title md:text-display">
            Quanto você cobra?
          </h1>
          <p className="mt-1.5 mb-0 text-body text-ink-muted">Crie as categorias do seu veículo com a diária, a semanal, a mensal e a caução. Mudanças valem só para contratos novos.</p>
        </div>
        <Button variante="solido" icone={<Icone de={Plus} />} onClick={() => setCriando(true)}>
          Nova categoria
        </Button>
      </div>

      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}
      {!feito && <p className="m-0 text-caption text-ink-muted">Para continuar, crie ao menos uma categoria com preço.</p>}

      <CategoriasDePreco criando={criando} aoFecharCriacao={() => setCriando(false)} aoAvisar={setAviso} />

      <p className="m-0 text-caption text-ink-muted">Depois você cria tabelas por filial, extras e planos especiais em Configurações › Tabelas de preço.</p>

      <RodapeDoPasso voltarPara={voltarPara} pularPara={pularPara} podeContinuar={feito} aoContinuar={aoContinuar} />
    </section>
  );
}
