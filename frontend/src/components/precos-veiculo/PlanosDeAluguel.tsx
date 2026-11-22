"use client";

import { useState } from "react";
import { Aviso, Button, LigaDesliga, Panel, StatusBadge } from "@/design-system";
import type { PlanoDoVeiculo } from "@/lib/api";
import { dinheiro } from "@/lib/formatos";
import {
  DICA_SEM_CUSTO_COMPRA,
  FORMAS,
  MARCA_SEM_CUSTO_COMPRA,
  OPCOES_DE_PARCELAS_DA_CAUCAO,
  PAGAMENTOS_DO_PERIODO,
  ROTULO_DA_FORMA,
  porPeriodo,
  periodoPlural,
  textoDaCaucaoEm,
  textoDaCaucaoParcelada,
  textoDaFranquia,
  textoDaMargem,
  textoDoAgendado,
  textoDoPagamento,
  tomDaMargem,
  type ErrosDeCampo,
  type PlanoRascunho,
} from "@/lib/precos-veiculo";

// Referência: docs/telas/html/Veiculo-Precos-Desktop.dc.html e Veiculo-Precos-Mobile.dc.html, painel "Aluguel".
// Uma árvore só: a linha é uma grade de 7 colunas no desktop e um cartão de duas colunas no celular (ordem pelas classes).
// A margem, o lucro e o preço agendado vêm da API; a tela só formata.

export type AcoesDoPlano = {
  editar: (chave: string, mudanca: Partial<PlanoRascunho>) => void;
  ligar: (chave: string, ligado: boolean) => void;
  agendar: (chave: string, valor: string, data: string) => void;
  desfazerAgendado: (chave: string) => void;
};

const COLUNAS = "md:grid-cols-[52px_minmax(0,1.4fr)_130px_190px_130px_120px_120px]";

function Campo({ rotulo, erro, dica, children, classe = "" }: { rotulo: string; erro?: string; dica?: string; children: React.ReactNode; classe?: string }) {
  const apoio = erro ?? dica;
  return (
    <label className={`wl-field wl-field--cheio min-w-0 ${erro ? "wl-field--error" : ""} ${classe}`}>
      <span className="wl-field__label md:sr-only">{rotulo}</span>
      {children}
      {apoio && <span className="wl-field__hint">{apoio}</span>}
    </label>
  );
}

function DetalheDoPlano({ p, atual, erros, somenteLeitura, acoes, ocupado, hoje }: { p: PlanoRascunho; atual: PlanoDoVeiculo | undefined; erros: ErrosDeCampo; somenteLeitura: boolean; acoes: AcoesDoPlano; ocupado: boolean; hoje: string }) {
  const k = (c: string) => `plano.${p.chave}.${c}`;
  const agendado = atual?.agendado ?? null;
  const [valor, setValor] = useState(agendado ? dinheiro(agendado.valor_centavos) : "");
  const [data, setData] = useState(agendado?.a_partir_de ?? "");
  // A data é a partir de amanhã (VEI-12); `min` é só a ajuda do campo, a API confere.
  const amanha = new Date(`${hoje}T12:00:00-03:00`);
  amanha.setDate(amanha.getDate() + 1);
  const minimo = amanha.toISOString().slice(0, 10);

  return (
    <div className="col-span-2 flex flex-col gap-4 rounded-md bg-surface-sunken p-4 md:order-last md:col-span-6 md:col-start-2">
      <div className="grid gap-x-6 gap-y-3 md:grid-cols-2">
        <div>
          <span className="wl-field__label mb-2 block">Formas aceitas</span>
          <div className="flex flex-wrap gap-x-5">
            {FORMAS.map((f) => (
              <label key={f} className="inline-flex min-h-11 cursor-pointer items-center gap-2 text-body md:min-h-0 md:text-[14px]">
                <input
                  type="checkbox"
                  className="h-[22px] w-[22px] accent-solid md:h-[18px] md:w-[18px]"
                  checked={p.formas.includes(f)}
                  disabled={somenteLeitura}
                  onChange={(e) => acoes.editar(p.chave, { formas: e.target.checked ? [...p.formas, f] : p.formas.filter((x) => x !== f) })}
                />
                {ROTULO_DA_FORMA[f]}
              </label>
            ))}
          </div>
          <span className={`wl-field__hint ${erros[k("formas_aceitas")] ? "text-critical-ink" : ""}`}>{erros[k("formas_aceitas")] ?? "Pelo menos uma."}</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className={`wl-field wl-field--cheio min-w-0 ${erros[k("franquia_km")] ? "wl-field--error" : ""}`}>
            <span className="wl-field__label">Franquia {porPeriodo(p.periodo)}</span>
            <input className="wl-input" value={p.franquia} placeholder="livre" disabled={somenteLeitura} onChange={(e) => acoes.editar(p.chave, { franquia: e.target.value })} />
            <span className="wl-field__hint">{erros[k("franquia_km")] ?? 'Ou "livre"'}</span>
          </label>
          <label className={`wl-field wl-field--cheio min-w-0 ${erros[k("prazo_minimo_periodos")] ? "wl-field--error" : ""}`}>
            <span className="wl-field__label">Prazo mínimo</span>
            <input className="wl-input" inputMode="numeric" value={p.prazoMinimo} placeholder="Sem mínimo" disabled={somenteLeitura} onChange={(e) => acoes.editar(p.chave, { prazoMinimo: e.target.value })} />
            <span className="wl-field__hint">{erros[k("prazo_minimo_periodos")] ?? `Em ${periodoPlural(p.periodo)}`}</span>
          </label>
        </div>
      </div>
      {!somenteLeitura && p.ligado && p.id != null && (
        <div className="flex flex-col gap-3 border-t border-line pt-4 md:grid md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-end md:gap-3">
          <div>
            <span className="wl-field__label mb-1 block">Preço agendado</span>
            <span className="text-[13px] text-ink-muted">Entra em vigor no começo do dia marcado, a partir de amanhã. Até lá, vale o preço de hoje.</span>
          </div>
          <div className="grid grid-cols-2 gap-3 md:contents">
            <label className="wl-field wl-field--cheio min-w-0">
              <span className="wl-field__label">Novo valor {porPeriodo(p.periodo)}</span>
              <input className="wl-input" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} />
            </label>
            <label className={`wl-field wl-field--cheio min-w-0 ${erros[k("agendado")] ? "wl-field--error" : ""}`}>
              <span className="wl-field__label">A partir de</span>
              <input className="wl-input" type="date" min={minimo} value={data} onChange={(e) => setData(e.target.value)} />
            </label>
          </div>
          <div className="flex flex-col-reverse gap-3 md:flex-row md:gap-2">
            {agendado && (
              <Button variante="quieto" compacto disabled={ocupado} onClick={() => acoes.desfazerAgendado(p.chave)}>
                Desfazer agendamento
              </Button>
            )}
            <Button compacto disabled={ocupado || !valor || !data} onClick={() => acoes.agendar(p.chave, valor, data)}>
              Agendar preço
            </Button>
          </div>
          {erros[k("agendado")] && (
            <span role="alert" className="wl-field__hint text-critical-ink md:col-span-4">
              {erros[k("agendado")]}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function LinhaDoPlano({ p, atual, erros, somenteLeitura, acoes, aberto, aoAbrir, ocupado, tentou, hoje }: { p: PlanoRascunho; atual: PlanoDoVeiculo | undefined; erros: ErrosDeCampo; somenteLeitura: boolean; acoes: AcoesDoPlano; aberto: boolean; aoAbrir: () => void; ocupado: boolean; tentou: boolean; hoje: string }) {
  const k = (c: string) => `plano.${p.chave}.${c}`;
  const margem = atual?.margem;
  const mostrarCampos = p.ligado || p.valor !== "" || tentou;
  const comErroNoDetalhe = Boolean(erros[k("formas_aceitas")] || erros[k("franquia_km")] || erros[k("prazo_minimo_periodos")]);
  const opcoesDePagamento = PAGAMENTOS_DO_PERIODO[p.periodo];
  const franquia = atual ? textoDaFranquia(atual.franquia_km, p.periodo) : "livre";

  return (
    <div className={`grid grid-cols-2 items-start gap-3 border-b border-line py-4 last:border-b-0 md:items-center md:py-2 ${COLUNAS} ${p.ligado ? "" : "text-ink-muted"}`} data-plano={p.chave}>
      <div className="min-w-0 md:order-2">
        <button type="button" className="cursor-pointer border-0 bg-transparent p-0 text-left font-sans text-body font-semibold text-ink" aria-expanded={aberto || comErroNoDetalhe} onClick={aoAbrir}>
          <span className={p.ligado ? "" : "text-ink-muted"}>{p.rotulo}</span>
        </button>
        <div className="text-[13px] text-ink-muted">{p.ligado ? (atual?.franquia_km == null && !p.franquia ? "franquia livre" : franquia) : "desligado"}</div>
      </div>
      <div className="justify-self-end md:order-1 md:justify-self-start">
        <LigaDesliga ligado={p.ligado} rotulo={`Oferecer ${p.rotulo.toLowerCase()}`} desabilitado={somenteLeitura || ocupado} aoMudar={(v) => acoes.ligar(p.chave, v)} />
      </div>

      {mostrarCampos ? (
        <>
          <Campo rotulo="Valor" erro={erros[k("valor_centavos")]} classe="md:order-3">
            <input className="wl-input" inputMode="decimal" placeholder="R$ 0,00" aria-label={`Valor ${p.rotulo.toLowerCase()}`} aria-invalid={erros[k("valor_centavos")] ? true : undefined} value={p.valor} disabled={somenteLeitura} onChange={(e) => acoes.editar(p.chave, { valor: e.target.value })} />
            {atual?.agendado && <span className="text-[13px] text-ink-muted">{textoDoAgendado(atual.agendado)}</span>}
          </Campo>
          <Campo rotulo="Caução" erro={erros[k("caucao_centavos")]} classe="md:order-5">
            <input className="wl-input" inputMode="decimal" placeholder="R$ 0,00" aria-label={`Caução ${p.rotulo.toLowerCase()}`} aria-invalid={erros[k("caucao_centavos")] ? true : undefined} value={p.caucao} disabled={somenteLeitura} onChange={(e) => acoes.editar(p.chave, { caucao: e.target.value })} />
          </Campo>
          <Campo rotulo="Como o cliente paga" erro={erros[k("como_paga")]} classe="col-span-2 md:order-4 md:col-span-1">
            <select className="wl-input" aria-label={`Pagamento ${p.rotulo.toLowerCase()}`} value={p.comoPaga} disabled={somenteLeitura} onChange={(e) => acoes.editar(p.chave, { comoPaga: e.target.value as PlanoRascunho["comoPaga"] })}>
              {opcoesDePagamento.map((o) => (
                <option key={o} value={o}>
                  {textoDoPagamento(o, o === atual?.como_paga ? atual?.parcela_do_mes : null)}
                </option>
              ))}
            </select>
          </Campo>
          <Campo rotulo="Caução em" classe="col-span-2 md:order-6 md:col-span-1" dica={atual?.caucao_parcelada ? textoDaCaucaoParcelada(atual.caucao_parcelada) : undefined}>
            <select className="wl-input" aria-label={`Parcelas da caução ${p.rotulo.toLowerCase()}`} value={String(p.caucaoParcelas)} disabled={somenteLeitura} onChange={(e) => acoes.editar(p.chave, { caucaoParcelas: Number(e.target.value) })}>
              {OPCOES_DE_PARCELAS_DA_CAUCAO.map((n) => (
                <option key={n} value={n}>
                  {textoDaCaucaoEm(n)}
                </option>
              ))}
            </select>
          </Campo>
        </>
      ) : (
        <div className="col-span-2 text-[13px] text-ink-muted md:order-3 md:col-span-5">Ligue para definir valor, prazo mínimo e caução.</div>
      )}

      {mostrarCampos && (
        <div className="col-span-2 flex items-center justify-between gap-2 rounded-md bg-surface px-3 py-2 text-[13px] md:order-7 md:col-span-1 md:flex-col md:items-end md:justify-center md:bg-transparent md:p-0">
          {margem === undefined ? null : margem === null ? (
            <span className="text-ink-muted">Informe a ocupação</span>
          ) : (
            <>
              <span className="text-ink-muted md:order-2">{dinheiro(margem.lucro_mes_centavos)}/mês</span>
              {margem.margem_pct != null && (
                <StatusBadge tom={tomDaMargem(margem.abaixo_da_minima, margem.sem_custo_compra)} compacto>
                  <span className="md:hidden">margem </span>
                  {textoDaMargem(margem.margem_pct)}
                </StatusBadge>
              )}
              {margem.sem_custo_compra && (
                <span className="text-ink-muted md:order-3" title={DICA_SEM_CUSTO_COMPRA}>
                  {MARCA_SEM_CUSTO_COMPRA}
                </span>
              )}
            </>
          )}
        </div>
      )}

      {(aberto || comErroNoDetalhe) && mostrarCampos && <DetalheDoPlano key={atual?.agendado ? `${atual.agendado.valor_centavos}-${atual.agendado.a_partir_de}` : "sem"} p={p} atual={atual} erros={erros} somenteLeitura={somenteLeitura} acoes={acoes} ocupado={ocupado} hoje={hoje} />}
      {erros[k("ligado")] && (
        <span role="alert" className="col-span-2 text-[13px] text-critical-ink md:col-span-6 md:col-start-2">
          {erros[k("ligado")]}
        </span>
      )}
    </div>
  );
}

/** Painel "Aluguel": um plano por linha, com o que a pessoa edita no rascunho e o que a API calculou ao lado. */
export function PlanosDeAluguel({ rascunho, exibidos, erros, somenteLeitura, acoes, ocupado, tentaram, hoje, mensagemDaLiga }: { rascunho: PlanoRascunho[]; exibidos: PlanoDoVeiculo[]; erros: ErrosDeCampo; somenteLeitura: boolean; acoes: AcoesDoPlano; ocupado: string | null; tentaram: Set<string>; hoje: string; mensagemDaLiga: string | null }) {
  const [abertos, setAbertos] = useState<Set<string>>(() => new Set(rascunho.filter((p) => p.tipo === "semanal" && p.ligado).map((p) => p.chave)));
  const alternar = (chave: string) =>
    setAbertos((s) => {
      const novo = new Set(s);
      if (!novo.delete(chave)) novo.add(chave);
      return novo;
    });
  const chaveDe = (x: PlanoDoVeiculo) => (x.id != null ? String(x.id) : x.tipo);

  return (
    <Panel titulo="Aluguel" subtitulo="Ligue os planos que esta moto oferece. Margem = lucro por mês ÷ receita, já com a desvalorização até a venda.">
      {mensagemDaLiga && (
        <div className="mb-3">
          <Aviso tom="critico">{mensagemDaLiga}</Aviso>
        </div>
      )}
      <div className="overflow-x-auto">
        <div className="min-w-0 md:min-w-[820px]">
          <div className={`hidden gap-3 border-b border-line py-2 text-[13px] text-ink-muted md:grid ${COLUNAS}`} aria-hidden="true">
            <span />
            <span>Plano</span>
            <span>Valor</span>
            <span>Como o cliente paga</span>
            <span>Caução</span>
            <span>Caução em</span>
            <span className="text-right">Margem</span>
          </div>
          {rascunho.map((p) => (
            <LinhaDoPlano
              key={p.chave}
              p={p}
              atual={exibidos.find((x) => chaveDe(x) === p.chave)}
              erros={erros}
              somenteLeitura={somenteLeitura}
              acoes={acoes}
              aberto={abertos.has(p.chave)}
              aoAbrir={() => alternar(p.chave)}
              ocupado={ocupado === p.chave}
              tentou={tentaram.has(p.chave)}
              hoje={hoje}
            />
          ))}
        </div>
      </div>
      <p className="mt-3 text-[13px] text-ink-muted">Formas aceitas, franquia e prazo mínimo ficam em cada linha ao tocar no plano. Mudar um preço vale só para as próximas locações.</p>
    </Panel>
  );
}
