"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Aviso, Button, Dialogo, LigaDesliga, Panel, StatusBadge } from "@/design-system";
import { ErroApi, veiculos, type PlanoCompraEntrada, type PlanoDoVeiculo, type PrecosDoVeiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dinheiro, placa } from "@/lib/formatos";
import {
  DICA_SEM_CUSTO_COMPRA,
  MARCA_SEM_CUSTO_COMPRA,
  textosDaConfirmacao,
  chaveDoPlano,
  ehOUltimoLigado,
  porPeriodo,
  porPeriodoDaCompra,
  textoDaFranquia,
  textoDaMargem,
  textoDaOcupacao,
  textoDasFormas,
  textoDoAgendado,
  textoDoPagamento,
  textoDoPrazoMinimo,
  tomDaMargem,
} from "@/lib/precos-veiculo";

// Referência: docs/telas/html/Veiculo-Componente-PrecosDaMoto.dc.html. Só leitura mais o liga e desliga confirmado; quem edita
// é a tela de preços. Todo número (margem, lucro, parcela, recebe pela moto) vem da API.

function Linha({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[7px] text-[14px] last:border-b-0">
      <span className="text-ink-muted">{rotulo}</span>
      <span className="text-right font-medium">{children}</span>
    </div>
  );
}

const CARTAO = "flex flex-col gap-1 rounded-lg p-[18px]";
const LIGADO = `${CARTAO} bg-surface-sunken`;
const DESLIGADO = `${CARTAO} border-[1.5px] border-dashed border-line bg-surface`;

function Desligado({ nome, ligado, desabilitado, aoLigar, erro }: { nome: string; ligado: boolean; desabilitado: boolean; aoLigar: (l: boolean) => void; erro?: string }) {
  return (
    <div className={DESLIGADO}>
      <div className="flex items-center justify-between font-semibold">
        <span>{nome}</span>
        <LigaDesliga ligado={ligado} rotulo={`Oferecer plano ${nome.toLowerCase()}`} desabilitado={desabilitado} aoMudar={aoLigar} />
      </div>
      <div className="mb-1 text-[28px] font-semibold leading-[34px] tracking-[-0.02em] text-ink-muted">Desligado</div>
      <p className="text-[14px] leading-5 text-ink-muted">Não aparece na nova locação. Ligue e defina valor, caução e franquia só para esta moto.</p>
      {erro && (
        <p role="alert" className="mt-1 text-[13px] text-critical-ink">
          {erro}
        </p>
      )}
    </div>
  );
}

function CartaoDoPlano({ p, desabilitado, aoLigar, erro }: { p: PlanoDoVeiculo; desabilitado: boolean; aoLigar: (l: boolean) => void; erro?: string }) {
  const periodo = p.periodo ?? "semana";
  const caucao = p.caucao_centavos == null ? "—" : `${dinheiro(p.caucao_centavos)} ${p.caucao_parcelas <= 1 ? "à vista" : `em ${p.caucao_parcelas}x`}`;
  return (
    <div className={LIGADO}>
      <div className="flex items-center justify-between font-semibold">
        <span>{p.rotulo}</span>
        <LigaDesliga ligado rotulo={`Oferecer plano ${p.rotulo.toLowerCase()}`} desabilitado={desabilitado} aoMudar={aoLigar} />
      </div>
      <div className="mb-1 text-[28px] font-semibold leading-[34px] tracking-[-0.02em]">
        {dinheiro(p.valor_centavos)} <small className="text-[14px] font-normal tracking-normal text-ink-muted">{porPeriodo(periodo)}</small>
      </div>
      {p.agendado && (
        <div>
          <StatusBadge tom="info" compacto>
            {textoDoAgendado(p.agendado)}
          </StatusBadge>
        </div>
      )}
      <Linha rotulo="Pagamento">{p.como_paga ? textoDoPagamento(p.como_paga, p.parcela_do_mes) : "—"}</Linha>
      <Linha rotulo="Formas">{textoDasFormas(p.formas_aceitas)}</Linha>
      {p.prazo_minimo_periodos != null && <Linha rotulo="Prazo mínimo">{textoDoPrazoMinimo(p.prazo_minimo_periodos, periodo)}</Linha>}
      <Linha rotulo="Caução">{caucao}</Linha>
      <Linha rotulo="Franquia">{textoDaFranquia(p.franquia_km, periodo)}</Linha>
      {p.margem && (
        <div className="mt-[6px] flex items-center justify-between gap-2 rounded-md bg-surface px-3 py-2 text-[13px]">
          <span className="text-ink-muted" title={p.margem.sem_custo_compra ? DICA_SEM_CUSTO_COMPRA : undefined}>
            Lucro {dinheiro(p.margem.lucro_mes_centavos)} por mês{p.margem.sem_custo_compra ? ` · ${MARCA_SEM_CUSTO_COMPRA}` : ""}
          </span>
          {p.margem.margem_pct != null && (
            <StatusBadge tom={tomDaMargem(p.margem.abaixo_da_minima, p.margem.sem_custo_compra)} compacto>
              margem {textoDaMargem(p.margem.margem_pct)}
            </StatusBadge>
          )}
        </div>
      )}
      {erro && (
        <p role="alert" className="mt-1 text-[13px] text-critical-ink">
          {erro}
        </p>
      )}
    </div>
  );
}

function CartaoDaCompra({ d, desabilitado, aoLigar, erro }: { d: PrecosDoVeiculo; desabilitado: boolean; aoLigar: (l: boolean) => void; erro?: string }) {
  const c = d.plano_compra;
  if (!c) return null;
  const r = c.resultado;
  return (
    <div className={`${LIGADO} md:col-span-full`} style={{ gridColumn: "1 / -1" }}>
      <div className="flex items-center justify-between font-semibold">
        <span>
          Locação com compra{" "}
          <span className="ml-[6px]">
            <StatusBadge compacto>a moto vira do cliente</StatusBadge>
          </span>
        </span>
        <LigaDesliga ligado={c.ligado} rotulo="Oferecer locação com compra" desabilitado={desabilitado} aoMudar={aoLigar} />
      </div>
      {c.ligado && r ? (
        <>
          <div className="mb-1 text-[28px] font-semibold leading-[34px] tracking-[-0.02em]">
            {dinheiro(r.parcela_cliente_centavos)}{" "}
            <small className="text-[14px] font-normal tracking-normal text-ink-muted">
              {porPeriodoDaCompra(c.periodicidade)} · {c.parcelas}× · juros {r.juros_mes_pct.replace(".", ",")}% ao mês
            </small>
          </div>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
            {d.valor_venda_centavos != null && (
              <div className="flex flex-col gap-[2px] border-b border-line py-[7px] text-[14px]">
                <span className="text-ink-muted">Valor de venda</span>
                <span className="font-medium">{dinheiro(d.valor_venda_centavos)}</span>
              </div>
            )}
            {d.pago_na_moto?.total_centavos != null && (
              <div className="flex flex-col gap-[2px] border-b border-line py-[7px] text-[14px]">
                <span className="text-ink-muted">Pago na moto</span>
                <span className="font-medium">{dinheiro(d.pago_na_moto.total_centavos)}</span>
              </div>
            )}
            <div className="flex flex-col gap-[2px] border-b border-line py-[7px] text-[14px]">
              <span className="text-ink-muted">Recebe pela moto</span>
              <span className="font-medium">{dinheiro(r.recebe_pela_moto_centavos)}</span>
            </div>
            {r.lucro_centavos != null && (
              <div className="flex flex-col gap-[2px] border-b border-line py-[7px] text-[14px]">
                <span className="text-ink-muted">Lucro</span>
                <span className="font-medium">{dinheiro(r.lucro_centavos)}</span>
              </div>
            )}
          </div>
          {(d.alertas.length > 0 || r.margem_sobre_pago_pct != null) && (
            <div className="mt-[6px] flex items-center justify-between gap-2 rounded-md bg-surface px-3 py-2 text-[13px]">
              <span className="text-ink-muted">{d.alertas.find((a) => a.codigo === "venda_abaixo_do_pago")?.mensagem ?? ""}</span>
              {r.margem_sobre_pago_pct != null && (
                <StatusBadge tom={tomDaMargem(r.venda_abaixo_do_pago)} compacto>
                  margem {textoDaMargem(r.margem_sobre_pago_pct)}
                </StatusBadge>
              )}
            </div>
          )}
          <div className="mt-2 flex gap-4 text-[14px]">
            <Link href={`/veiculos/${d.veiculo.id}/precos`} className="text-ink-muted">
              Ajustar venda, parcelas e juros
            </Link>
          </div>
        </>
      ) : (
        <p className="text-[14px] leading-5 text-ink-muted">Desligada. Não aparece na nova locação.</p>
      )}
      {erro && (
        <p role="alert" className="mt-1 text-[13px] text-critical-ink">
          {erro}
        </p>
      )}
    </div>
  );
}

type Confirmar = { quem: "compra" | PlanoDoVeiculo; ligar: boolean; ultimo: boolean };

/** Painel "Preços desta moto" da ficha: os planos como cartões, as regras e a locação com compra. Só o administrador liga e desliga. */
export function PrecosNaFicha({ id }: { id: number }) {
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: ["veiculo-precos", id], queryFn: () => veiculos.precos(id), retry: false });
  const [confirmar, setConfirmar] = useState<Confirmar | null>(null);
  const [erros, setErros] = useState<Record<string, string>>({});

  const gravar = useMutation({
    mutationFn: async ({ quem, ligar, d }: { quem: "compra" | PlanoDoVeiculo; ligar: boolean; d: PrecosDoVeiculo }) => {
      if (quem === "compra") {
        const c = d.plano_compra as NonNullable<PrecosDoVeiculo["plano_compra"]>;
        const corpo: PlanoCompraEntrada = {
          ligado: ligar,
          periodicidade: c.periodicidade,
          parcelas: c.parcelas,
          entrada_centavos: c.entrada_centavos,
          juros_mes_pct: c.juros_mes_pct,
          modo: c.modo,
          parcela_moto_centavos: c.parcela_moto_centavos,
          adicional_centavos: c.adicional_centavos,
          caucao_centavos: c.caucao_centavos,
        };
        return veiculos.salvarPrecos(id, { plano_compra: corpo, confirmar_juros: false });
      }
      if (quem.id == null) throw new Error("Plano sem cadastro.");
      return veiculos.ligarPlano(id, quem.id, ligar);
    },
  });

  // 403 (vistoriador não vê dinheiro, USR-09): o painel não aparece.
  if (consulta.error instanceof ErroApi && consulta.error.status === 403) return null;
  if (consulta.isError)
    return (
      <Panel titulo="Preços desta moto">
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      </Panel>
    );
  const d = consulta.data;
  if (!d)
    return (
      <Panel titulo="Preços desta moto">
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando os preços…
        </p>
      </Panel>
    );

  const somenteLeitura = !d.pode_editar;
  const chaveDe = (quem: "compra" | PlanoDoVeiculo) => (quem === "compra" ? "compra" : chaveDoPlano(quem));

  async function executar(c: Confirmar) {
    const chave = chaveDe(c.quem);
    setErros((e) => ({ ...e, [chave]: "" }));
    try {
      const resposta = await gravar.mutateAsync({ quem: c.quem, ligar: c.ligar, d: d as PrecosDoVeiculo });
      cliente.setQueryData(["veiculo-precos", id], resposta);
      void cliente.invalidateQueries({ queryKey: ["veiculo", id] });
      void cliente.invalidateQueries({ queryKey: ["veiculos"] });
    } catch (e) {
      // O interruptor só muda quando a API responde 200: aqui ele fica como estava e o erro aparece no cartão.
      const campos = e instanceof ErroApi ? Object.values(e.campos ?? {}) : [];
      setErros((x) => ({ ...x, [chave]: campos.length ? campos.join(" ") : e instanceof ErroApi && e.status === 409 && e.codigo === "VEI-16" ? `${e.message} Confirme na tela de preços.` : mensagemDoErro(e) }));
    }
  }

  function pedir(quem: "compra" | PlanoDoVeiculo, ligar: boolean) {
    setConfirmar({ quem, ligar, ultimo: !ligar && ehOUltimoLigado(d as PrecosDoVeiculo, chaveDe(quem)) });
  }

  const ligados = d.planos.filter((p) => p.ligado);
  const desligados = d.planos.filter((p) => !p.ligado);
  const textos = (c: Confirmar) => textosDaConfirmacao({ alvo: c.quem === "compra" ? "compra" : "plano", nome: c.quem === "compra" ? "" : c.quem.rotulo, ligar: c.ligar, ultimo: c.ultimo });
  const custoMes = d.custos?.custo_mes_centavos;

  return (
    <Panel
      titulo="Preços desta moto"
      subtitulo={
        <>
          Você escolhe os planos, o valor, como o cliente paga e a caução. Vale só para a {placa(d.veiculo.placa)}.
          {custoMes != null && d.custos?.ocupacao_esperada_pct != null && ` Margem calculada sobre o custo desta moto: ${dinheiro(custoMes)} por mês, com ocupação de ${textoDaOcupacao(d.custos.ocupacao_esperada_pct)}.`}
        </>
      }
      acao={
        !somenteLeitura ? (
          <Link href={`/veiculos/${id}/precos`} className="wl-btn wl-btn--sm">
            Editar preços
          </Link>
        ) : undefined
      }
    >
      {d.aviso_preco && (
        <div className="mb-3 mt-3">
          <Aviso>{d.aviso_preco}</Aviso>
        </div>
      )}
      <div className="mt-3 grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(230px,1fr))]">
        {ligados.map((p) => (
          <CartaoDoPlano key={chaveDoPlano(p)} p={p} desabilitado={somenteLeitura || gravar.isPending} aoLigar={(l) => pedir(p, l)} erro={erros[chaveDoPlano(p)]} />
        ))}
        <CartaoDaCompra d={d} desabilitado={somenteLeitura || gravar.isPending} aoLigar={(l) => pedir("compra", l)} erro={erros["compra"]} />
        {desligados.map((p) => (
          <Desligado key={chaveDoPlano(p)} nome={p.rotulo} ligado={false} desabilitado={somenteLeitura || gravar.isPending || p.id == null} aoLigar={(l) => pedir(p, l)} erro={erros[chaveDoPlano(p)]} />
        ))}
      </div>
      <div className="mt-3 grid gap-x-6 [grid-template-columns:repeat(auto-fit,minmax(220px,1fr))]">
        <Linha rotulo="Km excedente">{dinheiro(d.regras.km_excedente_centavos)} por km</Linha>
        <Linha rotulo="Atraso na devolução">{dinheiro(d.regras.dia_atraso_centavos)} por dia</Linha>
        <Linha rotulo="Desconto sem aprovação">até {Number(d.regras.desconto_sem_aprovacao_pct).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%</Linha>
        <Linha rotulo="Devolução da caução">{d.regras.prazo_devolucao_caucao_dias == null ? "sem prazo" : `até ${d.regras.prazo_devolucao_caucao_dias} dias após a devolução`}</Linha>
        <Linha rotulo="Multa mínima da devolução antecipada">{dinheiro(d.regras.multa_minima_centavos)}</Linha>
      </div>
      <p className="mt-[10px] text-[13px] text-ink-muted">Mudar um preço vale para as próximas locações.</p>

      <Dialogo
        aberto={confirmar !== null}
        aoFechar={() => setConfirmar(null)}
        tamanho="pequeno"
        titulo={confirmar ? textos(confirmar).titulo : ""}
        descricao={confirmar ? textos(confirmar).texto : undefined}
        acoes={
          <>
            <Button variante="quieto" onClick={() => setConfirmar(null)}>
              {confirmar ? textos(confirmar).cancelar : ""}
            </Button>
            <Button
              variante="solido"
              onClick={() => {
                const c = confirmar;
                setConfirmar(null);
                if (c) void executar(c);
              }}
            >
              {confirmar ? textos(confirmar).confirmar : ""}
            </Button>
          </>
        }
      />
    </Panel>
  );
}
