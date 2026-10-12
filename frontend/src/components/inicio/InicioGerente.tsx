"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { FleetBar, Icone, Panel, StatusBadge } from "@/design-system";
import type { InicioDe } from "@/lib/api";
import { rotuloDoPerfil } from "@/lib/painel";
import { useSessao } from "@/lib/sessao";
import { CabecalhoInicio, KpisDoPainel, LinhaDoPainel, ListaDoPainel, Vazio } from "./comuns";

function iniciais(nome: string) {
  return nome.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

/** Início do gerente (USR-08): aprovações da filial, indicadores, equipe de hoje e frota. */
export function InicioGerente({ d }: { d: InicioDe<"gerente"> }) {
  const { eu } = useSessao();
  const aprovacoes = d.aprovacoes ?? { total: 0, mais_antigo: null, itens: [] };
  const equipe = d.equipe_hoje ?? [];
  const segmentosDaFrota = d.frota_filial?.segmentos ?? [];
  return (
    <div className="flex flex-col gap-6">
      <CabecalhoInicio saudacao={d.saudacao} subtitulo={eu.filiais.length === 1 ? eu.filiais[0]?.nome : undefined}>
        {eu.pode.locacoes_criar && (
          <Link href="/locacoes/nova" className="wl-btn wl-btn--solid">
            <Icone de={Plus} />
            Nova locação
          </Link>
        )}
      </CabecalhoInicio>

      <Panel
        titulo={aprovacoes.total > 0 ? `${aprovacoes.total} ${aprovacoes.total === 1 ? "pedido esperando" : "pedidos esperando"} sua aprovação` : "Aprovações"}
        subtitulo={aprovacoes.mais_antigo ? `mais antigo ${aprovacoes.mais_antigo}` : undefined}
        acao={
          <Link href="/aprovacoes" className="wl-btn wl-btn--quiet wl-btn--sm">
            Ver todas
          </Link>
        }
      >
        {aprovacoes.itens.length === 0 ? (
          <Vazio>Nenhum pedido esperando sua aprovação.</Vazio>
        ) : (
          <ListaDoPainel rotulo="Pedidos esperando aprovação">
            {aprovacoes.itens.map((p) => (
              <LinhaDoPainel
                key={p.id}
                titulo={p.titulo}
                apoio={p.detalhe}
                fim={
                  <Link href={`/aprovacoes/${p.id}`} className="wl-btn wl-btn--quiet wl-btn--sm">
                    Ver detalhes
                  </Link>
                }
              />
            ))}
          </ListaDoPainel>
        )}
      </Panel>

      <KpisDoPainel kpis={d.kpis} />

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel titulo="Equipe hoje">
          {equipe.length === 0 ? (
            <Vazio>Ninguém da equipe está ligado a esta filial.</Vazio>
          ) : (
            <ListaDoPainel rotulo="Equipe de hoje">
              {equipe.map((p) => (
                <LinhaDoPainel
                  key={p.usuario_id}
                  titulo={
                    <span className="flex items-center gap-3">
                      <span className="wl-logo-slot rounded-full" aria-hidden="true">
                        {iniciais(p.nome)}
                      </span>
                      {p.nome}
                    </span>
                  }
                  apoio={`${rotuloDoPerfil(p.perfil)} · ${p.resumo}`}
                  fim={
                    <StatusBadge tom={p.online ? "sucesso" : "neutro"} compacto ponto={p.online}>
                      {p.online ? "Online" : "Offline"}
                    </StatusBadge>
                  }
                />
              ))}
            </ListaDoPainel>
          )}
        </Panel>
        <Panel titulo="Frota da filial">
          <FleetBar
            titulo={`${d.frota_filial?.total ?? 0} veículos`}
            segmentos={segmentosDaFrota.map((s, i) => ({ chave: s.rotulo, rotulo: s.rotulo, contagem: s.quantidade, destaque: i === 1 ? "marca" : undefined }))}
          />
        </Panel>
      </div>
    </div>
  );
}
