"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { LifeBuoy } from "lucide-react";
import { Button, Icone } from "@/design-system";
import { contas } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useSessao } from "@/lib/sessao";
import { ROTA_DEPOIS_DE_SAIR, rotulosDaFaixa } from "@/lib/suporte";

// Referência: docs/telas/html/Modo-Suporte-Desktop.dc.html e Modo-Suporte-Mobile.dc.html. Contrato: docs/api/contas.md, "Modo suporte".

/** Faixa fixa no topo enquanto `eu.suporte` não for `null` (PLT-07). Não fecha; os textos vêm da API e a tela não calcula tempo. */
export function FaixaDoSuporte() {
  const { eu } = useSessao();
  const suporte = eu.suporte;
  if (!suporte) return null;
  return <FaixaPreenchida suporte={suporte} />;
}

function FaixaPreenchida({ suporte }: { suporte: NonNullable<ReturnType<typeof useSessao>["eu"]["suporte"]> }) {
  const router = useRouter();
  const cliente = useQueryClient();
  const sair = useMutation({
    mutationFn: () => contas.sairDoSuporte(),
    onSuccess: async () => {
      await cliente.cancelQueries();
      cliente.clear();
      router.replace(ROTA_DEPOIS_DE_SAIR);
    },
  });
  const { permissao, fim } = rotulosDaFaixa(suporte);

  return (
    <div role="status" className="sticky top-0 z-50 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-warning bg-warning-soft px-4 py-3 text-warning-ink md:px-6">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <Icone de={LifeBuoy} />
        <div className="min-w-0">
          <div className="font-semibold">Modo suporte</div>
          <div className="text-caption">
            {suporte.nome} · Equipe Giro · Motivo: {suporte.motivo}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-caption">
        <span className="font-medium">{permissao}</span>
        {fim && <span>{fim}</span>}
        <Button compacto variante="solido" disabled={sair.isPending} onClick={() => sair.mutate()}>
          {sair.isPending ? "Saindo…" : "Sair do suporte"}
        </Button>
      </div>
      {sair.isError && (
        <p role="alert" className="m-0 w-full text-caption">
          {mensagemDoErro(sair.error)}
        </p>
      )}
    </div>
  );
}
