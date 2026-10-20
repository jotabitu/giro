"use client";

import { Button } from "@/design-system";
import type { MarcaEmpresa } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { CORES_DO_ASSISTENTE } from "@/lib/marca-edicao";
import { EscolhaDaCor } from "../marca/EscolhaDaCor";
import { EscolhaDoLogo } from "../marca/EscolhaDoLogo";
import { PreviaDaMarca } from "../marca/PreviaDaMarca";
import { useEdicaoDaMarca } from "../marca/useEdicaoDaMarca";

// Referência: docs/telas/html/Onboarding-Marca-Desktop.dc.html e Onboarding-Marca-Mobile.dc.html. CNPJ, razão social, nome fantasia
// e endereço de acesso ficam fora (sem contrato, docs/api/empresas.md). Pronto para a casca do assistente: ela entrega a marca
// lida de GET /api/marca/ e decide o que fazer em `aoContinuar` (passo seguinte) e `aoPular` (o passo continua aberto, IMP-05).

/** Passo "Marca" do assistente: logo e cor de destaque. "Continuar" sempre chama o PATCH, também sem mudança, e isso marca o passo. */
export function PassoMarca({ guardada, aoContinuar, aoPular }: { guardada: MarcaEmpresa; aoContinuar: () => void; aoPular: () => void }) {
  const m = useEdicaoDaMarca(guardada);
  const salvando = m.salvar.isPending;

  return (
    <form
      className="flex flex-col gap-6 md:flex-row md:flex-wrap md:items-start"
      onSubmit={(e) => {
        e.preventDefault();
        if (!salvando) m.salvar.mutate(undefined, { onSuccess: aoContinuar });
      }}
    >
      <section className="wl-panel flex min-w-0 flex-col gap-[22px] md:flex-[999_1_480px] md:p-8" aria-labelledby="passo-marca-titulo">
        <div>
          <h1 id="passo-marca-titulo" className="text-title md:text-display">
            Sua empresa e sua marca
          </h1>
          <p className="mt-2 mb-0 text-body text-ink-muted">Envie o logo e escolha a cor que sua equipe e seus clientes vão ver.</p>
        </div>
        {m.erroGeral !== null && (
          <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
            {mensagemDoErro(m.erroGeral)}
          </p>
        )}
        <EscolhaDoLogo logoUrl={m.logoUrl} iniciais={m.previa.iniciais} variante="assistente" desligado={salvando} erro={m.erro("logo")} aoEscolher={m.escolherLogo} aoRemover={m.removerLogo} />
        <EscolhaDaCor rotulo="Cor de destaque" cores={CORES_DO_ASSISTENTE} atual={m.edicao.cor} erro={m.erro("cor")} dica="A cor do texto sobre o destaque é ajustada sozinha para continuar legível." aoEscolher={m.escolherCor} />
        <div className="mt-auto flex flex-wrap gap-3 border-t border-line pt-4">
          <Button variante="quieto" onClick={aoPular} disabled={salvando}>
            Pular por agora
          </Button>
          <span className="ml-auto">
            <Button type="submit" variante="solido" disabled={salvando}>
              {salvando ? "Salvando…" : "Continuar"}
            </Button>
          </span>
        </div>
      </section>

      <section className="flex min-w-0 flex-col gap-3 md:flex-[1_1_400px]" aria-labelledby="passo-marca-previa">
        <div id="passo-marca-previa" className="pl-2 text-body text-ink-muted">
          Pré-visualização
        </div>
        <PreviaDaMarca marca={m.previa} logoUrl={m.logoUrl} />
      </section>
    </form>
  );
}
