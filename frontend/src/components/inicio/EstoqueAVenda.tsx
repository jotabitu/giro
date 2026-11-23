"use client";

// Blocos do estoque à venda e do ticket médio no início (T-486, T-487; VEI-18, VEI-19, VEI-20, VEN-12).
// Referência: docs/telas/html/Main.dc.html, Gerente-Desktop.dc.html, Gerente-Mobile.dc.html e Dashboard-Mobile.dc.html.
// Tudo vem calculado e com os textos da API; aqui só se mostra. Sem o bloco na resposta, nada aparece.
import Link from "next/link";
import type { CSSProperties } from "react";
import { Aviso, KpiTile, Panel, StatusBadge } from "@/design-system";
import type { EstoqueAVenda, ParadosAVenda, TicketMedio } from "@/lib/api";
import { dinheiro, placa } from "@/lib/formatos";
import { diasEmEstoque } from "@/lib/frota";
import { Vazio } from "./comuns";

const LISTA_A_VENDA = "/veiculos?status=a_venda";
const GRADE = "grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]";

/** A margem negativa vem com o sinal e pede o tom crítico (VEI-20); o cartão é o mesmo `wl-kpi` do KpiTile. */
function KpiDaMargem({ e }: { e: EstoqueAVenda }) {
  const valor = e.margem_texto ?? "—";
  const critico: CSSProperties | undefined = e.margem_negativa ? { color: "var(--critical-ink)" } : undefined;
  return (
    <div className="wl-kpi">
      <div className="wl-kpi__label">Margem potencial</div>
      <div className="wl-kpi__value" style={{ "--chars": Math.max(valor.length, 1), ...critico } as CSSProperties}>
        {valor}
      </div>
      {e.legenda_margem && (
        <div className="wl-kpi__meta" style={critico}>
          {e.legenda_margem}
        </div>
      )}
    </div>
  );
}

/** "Estoque à venda" (VEI-20): capital imobilizado, custo médio e margem potencial, com os avisos dos que ficaram fora. */
export function BlocoEstoqueAVenda({ e }: { e: EstoqueAVenda }) {
  const semCompra = e.custo_medio_centavos == null;
  return (
    <Panel titulo="Estoque à venda" subtitulo={e.subtitulo}>
      <div className="flex flex-col gap-3">
        {semCompra ? (
          <KpiTile rotulo="Capital imobilizado" valor={dinheiro(e.capital_imobilizado_centavos)} contexto={e.legenda_capital} />
        ) : (
          <div className={GRADE}>
            <KpiTile rotulo="Capital imobilizado" valor={dinheiro(e.capital_imobilizado_centavos)} contexto={e.legenda_capital} destaque />
            <KpiTile rotulo="Custo médio por unidade" valor={dinheiro(e.custo_medio_centavos ?? 0)} contexto={e.legenda_custo_medio ?? undefined} />
            {e.margem_texto && <KpiDaMargem e={e} />}
          </div>
        )}
        {(e.avisos.length > 0 || e.quantidade > 0) && (
          <div className="flex flex-wrap items-center gap-3">
            {e.avisos.map((aviso) => (
              <div key={aviso} className="min-w-0 flex-[1_1_300px]">
                <Aviso tom="info">{aviso}</Aviso>
              </div>
            ))}
            {e.quantidade > 0 && (
              <Link href={LISTA_A_VENDA} className="wl-btn wl-btn--quiet wl-btn--sm">
                Ver na lista
              </Link>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}

/** "Parados à venda" (VEI-18, VEI-19): os 5 com mais dias da filial; o parado em tom de alerta. */
export function BlocoParadosAVenda({ p }: { p: ParadosAVenda }) {
  return (
    <Panel
      titulo="Parados à venda"
      subtitulo={p.itens.length > 0 ? p.subtitulo : undefined}
      acao={
        <Link href={LISTA_A_VENDA} className="wl-btn wl-btn--quiet wl-btn--sm">
          Ver todos
        </Link>
      }
    >
      {p.itens.length === 0 ? (
        <Vazio>Nenhum veículo à venda nesta filial.</Vazio>
      ) : (
        <ul aria-label="Parados à venda" className="flex flex-col">
          {p.itens.map((item) => (
            <li key={item.id} className="border-b border-line last:border-b-0">
              <Link href={`/veiculos/${item.id}`} className="flex items-center gap-3 py-3 text-ink no-underline">
                <span className="wl-mono w-[92px] shrink-0 font-medium">{placa(item.placa)}</span>
                <span className="min-w-0 flex-1 truncate">{item.veiculo}</span>
                <StatusBadge tom={item.parado ? "alerta" : "neutro"} compacto>
                  {diasEmEstoque(item.dias_em_estoque)}
                </StatusBadge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** "Ticket médio do mês" (VEN-12). Até o fluxo de venda concluir vendas, a API manda o mês sem vendas. */
export function BlocoTicketMedio({ t }: { t: TicketMedio }) {
  return (
    <Panel titulo="Ticket médio do mês" subtitulo={t.subtitulo}>
      {t.ticket_centavos == null ? (
        <div className="wl-kpi">
          <div className="wl-kpi__label">Ticket médio do mês</div>
          <div className="mt-1">{t.vazio}</div>
        </div>
      ) : (
        <>
          <KpiTile rotulo={t.rotulo} valor={dinheiro(t.ticket_centavos)} contexto={t.resumo ?? undefined} />
          {t.comparacao && <p className="mt-3 text-body text-ink-muted">{t.comparacao}</p>}
        </>
      )}
    </Panel>
  );
}
