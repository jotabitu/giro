"use client";

// Blocos da ficha do veículo (desktop) que dependem do que a API manda além do básico (T-275, "Blocos da ficha" de
// veiculos.md). Cada bloco some quando a chave não vem: nada aqui é calculado nem inventado no cliente.
// Referência: docs/telas/html/Veiculo-Desktop.dc.html.
import { useMutation } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Button, Icone, Panel, ProgressBar, StatusBadge } from "@/design-system";
import { financeiro, type PosicaoDaFoto, type VeiculoDetalhe, type VistoriaRecente } from "@/lib/api";
import { dataCurta, dinheiro, iniciais, km } from "@/lib/formatos";
import { tomDoStatus } from "@/lib/tom";

const PERIODICIDADE = { diaria: "Diária", semanal: "Semanal", mensal: "Mensal" } as const;
const POSICAO: Record<PosicaoDaFoto, string> = { frente: "Frente", traseira: "Traseira", lado_esquerdo: "Esquerda", lado_direito: "Direita", painel: "Painel" };

/** Linha rótulo/valor dos cartões da referência (`.kv`, 15px, 6px de respiro). */
function Par({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[6px] text-body">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

const CARTAO = "flex flex-col gap-[10px] rounded-[22px] bg-surface-sunken p-[18px]";

function CartaoDaLocacao({ v }: { v: VeiculoDetalhe }) {
  const atual = v.locacao_atual;
  const [aviso, setAviso] = useState<string | null>(null);
  const pagamento = atual?.pagamento;
  const cobrar = useMutation({
    mutationFn: (contaId: number) => financeiro.cobrar(contaId),
    onSuccess: (r) => setAviso(r.enviadas > 0 ? `Cobrança enviada a ${atual?.cliente_nome}.` : `Nada foi enviado a ${atual?.cliente_nome}: a conta já foi cobrada hoje ou o cliente não tem contato.`),
  });
  if (!atual) return null;
  const plano = atual.plano?.valor_periodo_centavos != null ? `${PERIODICIDADE[atual.plano.periodicidade]} ${dinheiro(atual.plano.valor_periodo_centavos)}` : atual.plano ? PERIODICIDADE[atual.plano.periodicidade] : null;
  return (
    <div className={CARTAO}>
      <div className="flex items-center gap-3">
        <div aria-hidden="true" className="grid size-[36px] shrink-0 place-items-center rounded-sm bg-brand text-[12px] font-bold text-on-brand">
          {iniciais(atual.cliente_nome)}
        </div>
        <div className="min-w-0">
          <div className="font-semibold">{atual.cliente_nome}</div>
          <div className="text-[13px] text-ink-muted">{plano ? `${atual.codigo} · ${plano}` : atual.codigo}</div>
        </div>
      </div>
      <dl>
        <Par rotulo="Período">
          {dataCurta(atual.inicio)} → {dataCurta(atual.fim_previsto)}
        </Par>
        {pagamento && (
          <Par rotulo="Pagamentos">
            <StatusBadge tom={pagamento.situacao === "em_dia" ? "sucesso" : "alerta"} compacto>
              {pagamento.situacao === "em_dia" ? pagamento.rotulo : `${pagamento.rotulo} · ${dinheiro(pagamento.valor_centavos)}`}
            </StatusBadge>
          </Par>
        )}
        {atual.alerta && (
          <Par rotulo="Alerta">
            <StatusBadge tom="alerta" compacto>
              {atual.alerta}
            </StatusBadge>
          </Par>
        )}
      </dl>
      <div className="mt-1 flex gap-2">
        <Link href={`/locacoes/${atual.id}`} className="wl-btn wl-btn--sm no-underline" style={{ background: "var(--surface)" }}>
          Ver locação
        </Link>
        {pagamento?.cobrar && pagamento.conta_id != null && (
          <Button variante="solido" compacto disabled={cobrar.isPending} onClick={() => cobrar.mutate(pagamento.conta_id as number)}>
            Cobrar
          </Button>
        )}
      </div>
      {aviso && (
        <p role="status" className="text-[13px] text-ink-muted">
          {aviso}
        </p>
      )}
      {cobrar.isError && (
        <p role="alert" className="text-[13px]">
          Não foi possível enviar a cobrança. Tente de novo.
        </p>
      )}
    </div>
  );
}

function CartaoDaManutencao({ v }: { v: VeiculoDetalhe }) {
  const p = v.manutencao?.proxima;
  if (!p) return null;
  const progresso = p.progresso_pct != null ? Number(p.progresso_pct) : null;
  return (
    <div className={CARTAO}>
      <div className="flex items-baseline justify-between">
        <span className="font-semibold">Próxima manutenção</span>
        {p.intervalo_km != null && <span className="text-[13px] text-ink-muted">a cada {km(p.intervalo_km)}</span>}
      </div>
      <div className="text-[28px] font-semibold leading-8 tracking-[-0.02em]">{p.servico}</div>
      <div className="text-[14px] text-ink-muted">
        aos {km(p.km)}
        {p.faltam_km != null && (
          <>
            {" "}
            · faltam <b className="text-ink">{km(p.faltam_km)}</b>
            {p.dias_estimados != null && ` (cerca de ${p.dias_estimados} dias de uso)`}
          </>
        )}
      </div>
      {progresso != null && Number.isFinite(progresso) && (
        <div className="[&_.wl-progressbar]:bg-surface">
          <ProgressBar valor={progresso} rotulo="Andamento até a próxima manutenção" />
        </div>
      )}
      {(p.depois || p.nota) && (
        <div className="text-[13px] text-ink-muted">
          {p.depois && `Depois: ${p.depois.servico.toLowerCase()}, a ${km(p.depois.faltam_km)}.`}
          {p.depois && p.nota && " "}
          {p.nota}
        </div>
      )}
      {v.manutencao?.alerta && <div className="text-[13px] text-ink-muted">{v.manutencao.alerta}</div>}
    </div>
  );
}

/** "Agora": a locação em curso e a próxima manutenção, dois cartões lado a lado enquanto couberem (260px). */
export function AgoraDesktop({ v }: { v: VeiculoDetalhe }) {
  const atual = v.locacao_atual;
  if (!atual && !v.manutencao?.proxima) return null;
  return (
    <Panel
      titulo="Agora"
      acao={
        <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
          {atual ? `${v.situacao.rotulo} desde ${dataCurta(atual.inicio)}` : v.situacao.rotulo}
        </StatusBadge>
      }
    >
      <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]">
        <CartaoDaLocacao v={v} />
        <CartaoDaManutencao v={v} />
      </div>
    </Panel>
  );
}

function Miniatura({ posicao, url, avarias }: { posicao: PosicaoDaFoto; url: string; avarias: number }) {
  return (
    <div className="relative h-[96px] overflow-hidden rounded-[16px] bg-[linear-gradient(160deg,var(--surface-sunken),color-mix(in_srgb,var(--surface-sunken)_70%,var(--ink)_8%))]">
      {/* A URL é assinada e expira em 15 minutos (AUD-05): vale só enquanto a ficha está aberta. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {url ? <img src={url} alt={`Foto ${POSICAO[posicao].toLowerCase()}`} className="size-full object-cover" /> : (
        <div aria-hidden="true" className="absolute inset-0 grid place-items-center text-ink-muted opacity-[.55]">
          <Icone de={Camera} className="size-[18px]" />
        </div>
      )}
      {avarias > 0 && (
        <span className="absolute right-2 top-2 grid size-[22px] place-items-center rounded-full bg-warning text-[12px] font-bold text-on-warning">{avarias}</span>
      )}
      <span className="absolute bottom-2 left-2 whitespace-nowrap rounded-pill bg-surface px-2 py-[2px] text-[12px] font-medium">{POSICAO[posicao]}</span>
    </div>
  );
}

/** Contorno de moto, sem marcadores: a API não manda a posição da avaria (só a descrição). */
function Silhueta() {
  return (
    <svg viewBox="0 0 320 170" className="block h-[170px] w-full" role="img" aria-label="Contorno do veículo">
      <g fill="none" stroke="var(--ink-muted)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="62" cy="118" r="38" />
        <circle cx="62" cy="118" r="14" />
        <circle cx="258" cy="118" r="38" />
        <circle cx="258" cy="118" r="14" />
        <path d="M62 118 L112 70 L178 66 L212 84 L258 118" />
        <path d="M112 70 Q128 46 160 46 L196 48 Q206 50 210 62 L212 84" />
        <path d="M150 46 L176 34 L206 36" />
        <path d="M232 30 L244 70 L258 118" />
        <path d="M222 28 L246 24" />
        <path d="M240 46 L252 44" />
        <path d="M136 92 L196 92 L204 108 L144 108 Z" />
        <path d="M84 100 L140 102" />
      </g>
    </svg>
  );
}

function descricaoDaAvaria(a: VistoriaRecente["avarias"][number]): string {
  const quando = dataCurta(a.registrada_em);
  if (a.preexistente) return `${quando} · já existia, não cobrar`;
  return a.locacao_codigo ? `${quando} · registrado na saída da ${a.locacao_codigo}` : quando;
}

/** "Fotos e avarias" pela `vistoria_recente`. Sem a chave (financeiro, veículo sem vistoria) o painel não aparece. */
export function FotosEAvarias({ vistoria }: { vistoria: VistoriaRecente | null | undefined }) {
  if (!vistoria) return null;
  const { fotos, avarias } = vistoria;
  return (
    <Panel
      titulo="Fotos e avarias"
      acao={
        <span className="text-[13px] text-ink-muted">
          vistoria de {vistoria.tipo === "saida" ? "saída" : "devolução"} · {dataCurta(vistoria.concluida_em)}
          {vistoria.vistoriador ? ` · ${vistoria.vistoriador.nome}` : ""}
        </span>
      }
    >
      <div className="grid items-start gap-5 [grid-template-columns:repeat(auto-fit,minmax(300px,1fr))]">
        <div>
          {fotos.length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {fotos.map((f) => (
                <Miniatura key={f.id} posicao={f.posicao} url={f.url} avarias={avarias.filter((a) => a.foto_id === f.id).length} />
              ))}
            </div>
          )}
          {vistoria.total_fotos > 0 && (
            <Link href="/vistorias" className="mt-[10px] inline-block text-[14px] text-ink-muted underline">
              Ver as {vistoria.total_fotos} fotos da vistoria
            </Link>
          )}
        </div>
        <div className="rounded-[22px] bg-surface-sunken px-4 py-[14px]">
          <div className="mb-1 font-semibold">{avarias.length === 0 ? "Nenhuma avaria registrada" : avarias.length === 1 ? "1 avaria registrada" : `${avarias.length} avarias registradas`}</div>
          <Silhueta />
          {avarias.map((a, i) => (
            <div key={a.id} className="flex items-start gap-3 border-b border-line py-[10px]">
              <span className="grid size-6 shrink-0 place-items-center rounded-full bg-warning text-[12px] font-bold text-on-warning">{i + 1}</span>
              <div>
                <div className="font-medium">{a.descricao}</div>
                <div className="text-[13px] text-ink-muted">{descricaoDaAvaria(a)}</div>
              </div>
            </div>
          ))}
          {avarias.length > 0 && <div className="mt-2 text-[13px] text-ink-muted">Avaria registrada na saída não é cobrada do cliente na devolução.</div>}
        </div>
      </div>
    </Panel>
  );
}

/** "Movimentações" pelo bloco `movimentacoes`. Sem o bloco, o painel não aparece. */
export function MovimentacoesDoVeiculo({ v }: { v: VeiculoDetalhe }) {
  const m = v.movimentacoes;
  if (!m) return null;
  return (
    <Panel
      titulo="Movimentações"
      acao={
        <Link href="/veiculos/movimentacoes" className="text-[14px] text-ink-muted underline">
          ver todas
        </Link>
      }
    >
      {m.ultimas.length === 0 ? (
        <p className="py-1 text-[14px] text-ink-muted">Nenhuma movimentação.{v.acoes.motivo_movimentar ? ` ${v.acoes.motivo_movimentar}` : ""}</p>
      ) : (
        <ul>
          {m.ultimas.map((u) => (
            <li key={u.id} className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
              <span>
                <span className="wl-mono">{u.codigo}</span> · {[...u.paradas, u.destino_nome].join(" → ")}
              </span>
              <span className="text-ink-muted">{dataCurta(u.iniciada_em)}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** Celular: "Fotos e avarias" no cartão da ficha, sem a silhueta nem o link (Veiculo-Mobile). Some sem `vistoria_recente`. */
export function FotosEAvariasCelular({ vistoria }: { vistoria: VistoriaRecente | null | undefined }) {
  if (!vistoria) return null;
  const { fotos, avarias } = vistoria;
  return (
    <section className="rounded-lg bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-heading">Fotos e avarias</h2>
        <span className="text-[13px] text-ink-muted">
          {vistoria.tipo === "saida" ? "saída" : "devolução"} · {dataCurta(vistoria.concluida_em)}
        </span>
      </div>
      {fotos.length > 0 && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          {fotos.map((f) => (
            <Miniatura key={f.id} posicao={f.posicao} url={f.url} avarias={avarias.filter((a) => a.foto_id === f.id).length} />
          ))}
        </div>
      )}
      {avarias.length === 0 ? (
        <p className="mt-2 text-body text-ink-muted">Nenhuma avaria registrada.</p>
      ) : (
        avarias.map((a, i) => (
          <div key={a.id} className="flex items-start gap-3 border-b border-line py-[10px] last:border-b-0">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-warning text-[12px] font-bold text-on-warning">{i + 1}</span>
            <div>
              <div className="font-medium">{a.descricao}</div>
              <div className="text-[13px] text-ink-muted">{descricaoDaAvaria(a)}</div>
            </div>
          </div>
        ))
      )}
    </section>
  );
}

/** Celular: "Movimentações" como cartão simples, com os mesmos dados do desktop. Some sem o bloco `movimentacoes`. */
export function MovimentacoesCelular({ v }: { v: VeiculoDetalhe }) {
  const m = v.movimentacoes;
  if (!m) return null;
  return (
    <section className="rounded-lg bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-heading">Movimentações</h2>
        <Link href="/veiculos/movimentacoes" className="inline-flex min-h-11 items-center text-[14px] text-ink-muted underline">
          ver todas
        </Link>
      </div>
      {m.ultimas.length === 0 ? (
        <p className="text-body text-ink-muted">Nenhuma movimentação.{v.acoes.motivo_movimentar ? ` ${v.acoes.motivo_movimentar}` : ""}</p>
      ) : (
        <ul>
          {m.ultimas.map((u) => (
            <li key={u.id} className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
              <span>
                <span className="wl-mono">{u.codigo}</span> · {[...u.paradas, u.destino_nome].join(" → ")}
              </span>
              <span className="shrink-0 text-ink-muted">{dataCurta(u.iniciada_em)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
