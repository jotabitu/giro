"use client";

import { Aviso, InputDeDinheiro, LigaDesliga, SegmentedControl, StatusBadge } from "@/design-system";
import type { PrecosDoVeiculo } from "@/lib/api";
import { dinheiro } from "@/lib/formatos";
import {
  DICA_SEM_CUSTO_COMPRA,
  MARCA_SEM_CUSTO_COMPRA,
  MODOS_DA_PARCELA,
  ROTULO_DA_PERIODICIDADE_DA_COMPRA,
  pluralDaCompra,
  porPeriodoDaCompra,
  textoDaMargem,
  textoDeMeses,
  textoDosJuros,
  tomDaMargem,
  type CompraRascunho,
  type ErrosDeCampo,
} from "@/lib/precos-veiculo";
import { SetaDoBloco, useBlocoRecolhivel } from "./SetaDoBloco";

// Referência: Veiculo-Precos-Desktop|Mobile.dc.html, painel "Locação com compra". Todo número do resultado (parcela do cliente,
// recebe pela moto, lucro, margem, juros no prazo, parcelas nas outras periodicidades, alertas) vem da API pelo `simular`.

const OPCOES = (Object.keys(ROTULO_DA_PERIODICIDADE_DA_COMPRA) as CompraRascunho["periodicidade"][]).map((valor) => ({ valor, rotulo: ROTULO_DA_PERIODICIDADE_DA_COMPRA[valor] }));
const SEG_CHEIO = "max-md:[&_.wl-seg]:flex max-md:[&_.wl-seg]:w-full max-md:[&_.wl-seg>button]:flex-1 max-md:[&_.wl-seg>button]:px-1";

function Campo({ rotulo, dica, erro, children }: { rotulo: string; dica?: string; erro?: string; children: React.ReactNode }) {
  const apoio = erro ?? dica;
  return (
    <label className={`wl-field wl-field--cheio min-w-0 ${erro ? "wl-field--error" : ""}`}>
      <span className="wl-field__label">{rotulo}</span>
      {children}
      {apoio && <span className="wl-field__hint">{apoio}</span>}
    </label>
  );
}

function Linha({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[9px] text-[14px] last:border-b-0">
      <span className="text-ink-muted">{rotulo}</span>
      <span className="text-right font-medium">{children}</span>
    </div>
  );
}

export function LocacaoComCompra({
  c,
  atual,
  alertas,
  pagoNaMoto,
  erros,
  somenteLeitura,
  ocupado,
  aoEditar,
  aoLigar,
}: {
  c: CompraRascunho;
  atual: PrecosDoVeiculo["plano_compra"];
  alertas: PrecosDoVeiculo["alertas"];
  pagoNaMoto: number | null | undefined;
  erros: ErrosDeCampo;
  somenteLeitura: boolean;
  ocupado: boolean;
  aoEditar: (mudanca: Partial<CompraRascunho>) => void;
  aoLigar: (ligado: boolean) => void;
}) {
  const r = atual?.resultado ?? null;
  const e = (campo: string) => erros[`compra.${campo}`];
  const digitando = c.modo === "digitar";
  const unidade = pluralDaCompra(c.periodicidade);
  // A divisão da barra vem da API (VEI-16); sem os dois campos (vendedor), a barra não aparece.
  const pagoPct = r?.pago_sobre_recebe_pct == null ? null : Number(r.pago_sobre_recebe_pct);
  const lucroPct = r?.lucro_sobre_recebe_pct == null ? null : Number(r.lucro_sobre_recebe_pct);
  // T-508: a mesma seta do aluguel. Aberto por padrão; com a compra desligada, começa recolhido. Erro na compra abre.
  const comErro = Object.keys(erros).some((k) => k.startsWith("compra."));
  const { aberto, alternar } = useBlocoRecolhivel(!c.ligado, comErro);

  return (
    <section className="wl-panel" aria-label="Locação com compra">
      <div className="wl-panel__head">
        <div className="flex min-w-0 items-center gap-3">
          <LigaDesliga ligado={c.ligado} rotulo="Oferecer locação com compra" desabilitado={somenteLeitura || ocupado} aoMudar={aoLigar} />
          <div className="min-w-0">
            <h2 className="wl-panel__title">Locação com compra</h2>
            <p className="wl-panel__sub">O cliente paga o valor de venda em parcelas e a moto é dele no fim.</p>
          </div>
        </div>
        <SetaDoBloco aberto={aberto} oQue="a locação com compra" controla="locacao-com-compra" aoAlternar={alternar} />
      </div>
      {e("ligado") && (
        <div className="mt-3">
          <Aviso tom="critico">{e("ligado")}</Aviso>
        </div>
      )}
      <div id="locacao-com-compra" hidden={!aberto}>
      <div className="mt-4 grid gap-5 md:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <div className={SEG_CHEIO}>
            <span className="wl-field__label mb-[6px] block">Parcelas</span>
            <SegmentedControl rotulo="Periodicidade" opcoes={OPCOES} valor={c.periodicidade} aoMudar={(v) => !somenteLeitura && aoEditar({ periodicidade: v })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Campo rotulo="Quantidade de parcelas" erro={e("parcelas")} dica={r ? `${c.parcelas} ${unidade} = ${textoDeMeses(r.meses_do_prazo)}` : undefined}>
              <input className="wl-input" inputMode="numeric" value={c.parcelas} disabled={somenteLeitura} onChange={(ev) => aoEditar({ parcelas: ev.target.value })} />
            </Campo>
            <Campo rotulo="Entrada" erro={e("entrada_centavos")} dica={r ? `Financia ${dinheiro(r.financiado_centavos)}` : undefined}>
              <InputDeDinheiro prefixo value={c.entrada} disabled={somenteLeitura} onChange={(ev) => aoEditar({ entrada: ev.target.value })} />
            </Campo>
            <Campo rotulo="Juros ao mês" erro={e("juros_mes_pct")} dica={r ? `${textoDosJuros(r.taxa_periodo_pct)} ${porPeriodoDaCompra(c.periodicidade)} · Price` : undefined}>
              <input
                className="wl-input"
                inputMode="decimal"
                value={digitando && r ? textoDosJuros(r.juros_mes_pct) : c.juros}
                readOnly={digitando}
                disabled={somenteLeitura}
                onChange={(ev) => aoEditar({ juros: ev.target.value })}
              />
            </Campo>
            <Campo rotulo="Valor da parcela" erro={e("parcela_moto_centavos")} dica={digitando ? "Digitado por você" : "Calculado pelos juros"}>
              <InputDeDinheiro prefixo
                className="wl-input"
                value={digitando ? c.parcelaMoto : r ? dinheiro(r.parcela_moto_centavos) : ""}
                readOnly={!digitando}
                disabled={somenteLeitura}
                onChange={(ev) => aoEditar({ parcelaMoto: ev.target.value })}
              />
            </Campo>
          </div>
          <div className={SEG_CHEIO}>
            <SegmentedControl
              rotulo="Como definir a parcela"
              opcoes={MODOS_DA_PARCELA}
              valor={c.modo}
              aoMudar={(modo) => !somenteLeitura && aoEditar({ modo, ...(modo === "digitar" && !c.parcelaMoto && r ? { parcelaMoto: dinheiro(r.parcela_moto_centavos) } : {}) })}
            />
          </div>
          <p className="-mt-2 text-[13px] leading-[18px] text-ink-muted">Digitando a parcela, o sistema mostra os juros que ela representa. Ex.: R$ 170,00 por semana = 1,46% ao mês.</p>
          <div className="grid grid-cols-2 gap-3">
            <Campo rotulo="Adicional por parcela" erro={e("adicional_centavos")} dica="Seguro e rastreador seguem com a locadora">
              <InputDeDinheiro prefixo value={c.adicional} disabled={somenteLeitura} onChange={(ev) => aoEditar({ adicional: ev.target.value })} />
            </Campo>
            <Campo rotulo="Caução" erro={e("caucao_centavos")} dica="Abatida da última parcela">
              <InputDeDinheiro prefixo value={c.caucao} disabled={somenteLeitura} onChange={(ev) => aoEditar({ caucao: ev.target.value })} />
            </Campo>
          </div>
        </div>

        <div className="flex flex-col gap-1 rounded-lg bg-surface-sunken p-4 md:p-5" aria-live="polite">
          {r ? (
            <>
              <span className="text-[14px] text-ink-muted">O cliente paga</span>
              <div className="text-[32px] font-semibold leading-[38px] tracking-[-0.02em] md:text-[36px] md:leading-[42px]">
                {dinheiro(r.parcela_cliente_centavos)}{" "}
                <small className="text-[14px] font-normal tracking-normal text-ink-muted md:text-[15px]">
                  {porPeriodoDaCompra(c.periodicidade)} · {atual?.parcelas}×
                </small>
              </div>
              <span className="text-[13px] text-ink-muted">
                {dinheiro(r.parcela_moto_centavos)} da moto + {dinheiro(r.adicional_centavos)} de adicional
              </span>
              {pagoPct != null && lucroPct != null && r.lucro_centavos != null && (
                <div className="mt-[10px] mb-1 flex h-3 overflow-hidden rounded-pill" role="img" aria-label={`Pago na moto ${dinheiro(pagoNaMoto ?? 0)} e lucro ${dinheiro(r.lucro_centavos)} do total recebido`}>
                  <i className="block h-full bg-line" style={{ width: `${pagoPct}%` }} />
                  <i className="block h-full bg-solid" style={{ width: `${lucroPct}%` }} />
                </div>
              )}
              <Linha rotulo="Recebe pela moto">{dinheiro(r.recebe_pela_moto_centavos)}</Linha>
              {pagoNaMoto != null && <Linha rotulo="Pago na moto">{dinheiro(pagoNaMoto)}</Linha>}
              {r.lucro_centavos != null && <Linha rotulo="Lucro">{dinheiro(r.lucro_centavos)}</Linha>}
              {r.margem_sobre_pago_pct != null && (
                <Linha rotulo="Margem sobre o pago">
                  <StatusBadge tom={tomDaMargem(r.venda_abaixo_do_pago)} compacto>
                    {textoDaMargem(r.margem_sobre_pago_pct)}
                  </StatusBadge>
                </Linha>
              )}
              <Linha rotulo="Juros no prazo">{dinheiro(r.juros_no_prazo_centavos)}</Linha>
              {r.sem_custo_compra && (
                <div className="mt-2">
                  <Aviso tom="info">
                    <b>Lucro e margem {MARCA_SEM_CUSTO_COMPRA}.</b> {DICA_SEM_CUSTO_COMPRA}
                  </Aviso>
                </div>
              )}
            </>
          ) : (
            <p className="text-body text-ink-muted">Informe o valor de venda, as parcelas e a entrada para ver o resultado.</p>
          )}
          {alertas.map((a) => (
            <div key={a.codigo} className="mt-2">
              <Aviso>{a.mensagem}</Aviso>
            </div>
          ))}
        </div>
      </div>

      {r && (
        <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4" role="group" aria-label="Mesma condição em outras periodicidades">
          {r.nas_periodicidades.map((o) => (
            <div key={o.periodicidade} className={`flex flex-col gap-[2px] rounded-md border-[1.5px] px-3 py-[10px] text-[13px] ${o.periodicidade === c.periodicidade ? "border-ink" : "border-line"}`}>
              <span className="text-ink-muted">
                {ROTULO_DA_PERIODICIDADE_DA_COMPRA[o.periodicidade]} · {o.parcelas}×
              </span>
              <b className="text-[15px]">{dinheiro(o.parcela_cliente_centavos)}</b>
            </div>
          ))}
        </div>
      )}
      </div>
    </section>
  );
}
