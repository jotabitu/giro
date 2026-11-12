"use client";

import { useQuery } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import Link from "next/link";
import { Icone } from "@/design-system";
import { assinatura } from "@/lib/api";
import { useSessao } from "@/lib/sessao";

// Regras: PLT-02 (suspensa), PLT-06 (pausada). Contrato: docs/api/plataforma.md, `faixa_aviso`, e docs/api/assinatura.md.

const STATUS_COM_FAIXA = ["suspensa", "pausada"];

/** Só aparece quando a empresa está só para consulta por assinatura: `suspensa` ou `pausada` (a `cancelada` nem entra no sistema). */
export function empresaComFaixa(status: string, somenteLeitura: boolean): boolean {
  return somenteLeitura && STATUS_COM_FAIXA.includes(status);
}

/** O texto é o `faixa_aviso` da API; só se ele faltar entra o texto fixo do contrato. A tela não monta datas nem valores. */
export function textoDaFaixa(status: string, faixaAviso: string | null | undefined): string {
  if (faixaAviso) return faixaAviso;
  return status === "pausada" ? "Assinatura pausada. Você só consulta os dados." : "Assinatura suspensa. Você só consulta os dados até pagar a fatura.";
}

/** Faixa fixa no topo de todas as telas da empresa enquanto ela estiver `suspensa` ou `pausada`. Não fecha e não é pop-up. */
export function FaixaDaAssinatura() {
  const { eu } = useSessao();
  const ativa = empresaComFaixa(eu.empresa.status, eu.empresa.somente_leitura);
  const consulta = useQuery({ queryKey: ["assinatura"], queryFn: () => assinatura.obter(), enabled: ativa });
  if (!ativa) return null;
  return <FaixaPreenchida status={eu.empresa.status} faixaAviso={consulta.data?.faixa_aviso} administra={eu.pode.administracao} />;
}

export function FaixaPreenchida({ status, faixaAviso, administra }: { status: string; faixaAviso?: string | null; administra: boolean }) {
  const suspensa = status === "suspensa";
  // Celular: faixa baixa. Texto numa linha própria, o aviso e o botão embaixo; a partir do desktop, tudo na mesma linha.
  return (
    <div role="status" data-faixa-assinatura={status} className="flex flex-col gap-2 border-b border-warning bg-warning-soft px-4 py-2 text-warning-ink md:flex-row md:flex-wrap md:items-center md:justify-between md:gap-x-4 md:px-6 md:py-3">
      <div className="flex min-w-0 items-start gap-2 md:flex-1 md:items-center md:gap-3">
        <Icone de={Lock} />
        <p className="m-0 min-w-0 text-caption font-medium md:text-body">{textoDaFaixa(status, faixaAviso)}</p>
      </div>
      {administra ? (
        <Link href="/admin/assinatura" className="wl-btn wl-btn--sm w-full no-underline md:w-auto">
          {suspensa ? "Pagar a fatura" : "Ver a assinatura"}
        </Link>
      ) : (
        <span className="text-caption">Fale com o administrador da empresa.</span>
      )}
    </div>
  );
}
