"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { relatorios, type Periodo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useSessao } from "@/lib/sessao";
import { InicioFinanceiro } from "./InicioFinanceiro";
import { InicioGeral } from "./InicioGeral";
import { InicioGerente } from "./InicioGerente";
import { InicioImplantacao } from "./InicioImplantacao";
import { InicioVendedor } from "./InicioVendedor";
import { InicioVistoriador } from "./InicioVistoriador";

/**
 * Rota única `/inicio` (USR-08): a variante vem de `eu.navegacao.inicio.variante` e o conteúdo, de GET /api/painel/inicio/.
 * O período só muda os números da variante `geral`.
 */
export function InicioPorPerfil() {
  const { eu } = useSessao();
  const variante = eu.navegacao.inicio.variante;
  const [periodo, setPeriodo] = useState<Periodo>("7d");
  const consulta = useQuery({
    queryKey: ["inicio", variante, variante === "geral" ? periodo : null],
    queryFn: () => relatorios.inicio(periodo),
    placeholderData: (anterior) => anterior,
  });

  if (consulta.isError) {
    return (
      <p role="alert" className="wl-panel text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  }
  const d = consulta.data;
  if (!d) {
    return (
      <p className="wl-panel text-body text-ink-muted" aria-busy="true">
        Carregando o início…
      </p>
    );
  }

  switch (d.variante) {
    case "geral":
      return <InicioGeral d={d} periodo={periodo} aoMudarPeriodo={setPeriodo} />;
    case "implantacao":
      return <InicioImplantacao d={d} />;
    case "gerente":
      return <InicioGerente d={d} />;
    case "vendedor":
      return <InicioVendedor d={d} />;
    case "vistoriador":
      return <InicioVistoriador d={d} />;
    case "financeiro":
      return <InicioFinanceiro d={d} />;
  }
}
