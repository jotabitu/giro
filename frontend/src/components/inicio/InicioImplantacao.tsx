"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { Icone, KpiGrid, KpiTile, Panel, StatusBadge } from "@/design-system";
import type { InicioDe } from "@/lib/api";
import { dinheiro } from "@/lib/formatos";
import { hrefDoDestino } from "@/lib/menu";
import { percentual, rotuloDoPerfil } from "@/lib/painel";
import { CabecalhoInicio, LinhaDoPainel, ListaDoPainel, Vazio } from "./comuns";

const CONVITE: Record<string, { rotulo: string; tom: "sucesso" | "alerta" | "neutro" }> = {
  aceito: { rotulo: "Aceitou", tom: "sucesso" },
  pendente: { rotulo: "Pendente", tom: "alerta" },
};

/** Início da implantação (USR-08, IMP-01): administrador antes da 1ª locação ou venda. Passos e convites vêm da API. */
export function InicioImplantacao({ d }: { d: InicioDe<"implantacao"> }) {
  const p = d.primeiros_passos ?? { concluidos: 0, total: 0, pct: "0", itens: [] };
  const convites = d.convites ?? [];
  const ind = d.indicadores ?? { frota_cadastrada: 0, alugados_agora: 0, clientes: 0, a_receber_centavos: 0 };
  return (
    <div className="flex flex-col gap-6">
      {d.teste && (
        <div className="wl-panel flex flex-wrap items-center justify-between gap-3">
          <p className="text-body">{d.teste.texto}</p>
          <Link href="/admin/assinatura" className="wl-btn wl-btn--solid">
            Escolher pagamento
          </Link>
        </div>
      )}
      <CabecalhoInicio saudacao={d.saudacao} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel titulo="Primeiros passos" subtitulo={`${p.concluidos} de ${p.total} concluídos`}>
          <div className="mb-4 h-2 overflow-hidden rounded-pill bg-surface-sunken" role="progressbar" aria-label="Primeiros passos" aria-valuenow={Math.round(Number(p.pct))} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full bg-solid" style={{ width: `${p.pct}%` }} />
          </div>
          <span className="sr-only">{percentual(p.pct)} concluído</span>
          <ListaDoPainel rotulo="Primeiros passos">
            {p.itens.map((i) => {
              const href = i.acao ? hrefDoDestino(i.acao.destino) : undefined;
              return (
                <LinhaDoPainel
                  key={i.chave}
                  titulo={
                    <span className="flex items-center gap-2">
                      {i.concluido && <Icone de={Check} />}
                      <span className={i.concluido ? "text-ink-muted line-through" : undefined}>{i.rotulo}</span>
                      {i.concluido && <span className="sr-only">(concluído)</span>}
                    </span>
                  }
                  apoio={i.detalhe}
                  fim={
                    !i.concluido && i.acao && href ? (
                      <Link href={href} className="wl-btn wl-btn--solid wl-btn--sm">
                        {i.acao.rotulo}
                      </Link>
                    ) : undefined
                  }
                />
              );
            })}
          </ListaDoPainel>
        </Panel>

        <Panel titulo="Convites" acao={<Link href="/admin/usuarios" className="wl-btn wl-btn--quiet wl-btn--sm">Ver usuários</Link>}>
          {convites.length === 0 ? (
            <Vazio>Nenhum convite enviado ainda.</Vazio>
          ) : (
            <ListaDoPainel rotulo="Convites">
              {convites.map((c) => {
                const s = CONVITE[c.status] ?? { rotulo: c.status, tom: "neutro" as const };
                return (
                  <LinhaDoPainel
                    key={c.contato}
                    titulo={c.nome}
                    apoio={`${rotuloDoPerfil(c.perfil)} · ${c.contato}`}
                    fim={
                      <StatusBadge tom={s.tom} compacto>
                        {s.rotulo}
                      </StatusBadge>
                    }
                  />
                );
              })}
            </ListaDoPainel>
          )}
        </Panel>
      </div>

      <KpiGrid>
        <KpiTile rotulo="Frota cadastrada" valor={String(ind.frota_cadastrada)} />
        <KpiTile rotulo="Alugados agora" valor={String(ind.alugados_agora)} />
        <KpiTile rotulo="Clientes" valor={String(ind.clientes)} />
        <KpiTile rotulo="A receber" valor={dinheiro(ind.a_receber_centavos)} />
      </KpiGrid>
    </div>
  );
}
