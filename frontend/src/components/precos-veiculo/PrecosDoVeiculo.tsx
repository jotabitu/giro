"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import { Aviso, Button, Dialogo, Panel } from "@/design-system";
import { ErroApi, veiculos, type PrecosDoVeiculo as Precos, type PrecosEntrada } from "@/lib/api";
import { useAmbiente } from "@/lib/ambiente";
import { useAtrasado, useCelular } from "@/lib/atrasado";
import { mensagemDoErro } from "@/lib/erros";
import { dinheiro, placa as placaComHifen } from "@/lib/formatos";
import {
  TEXTO_DESLIGAR,
  TEXTO_DESLIGAR_O_ULTIMO,
  centavosDoCampo,
  chaveDoPlano,
  compraParaRascunho,
  corpoDaCompra,
  corpoDaDiferenca,
  corpoDoPlano,
  ehOUltimoLigado,
  errosDaApi,
  planoParaRascunho,
  rascunhoDoDocumento,
  textoDaOcupacao,
  type CompraRascunho,
  type CorpoMontado,
  type ErrosDeCampo,
  type PlanoRascunho,
  type RegrasRascunho,
  type Rascunho,
} from "@/lib/precos-veiculo";
import { CustosMensais } from "./CustosMensais";
import { LocacaoComCompra } from "./LocacaoComCompra";
import { PlanosDeAluguel, type AcoesDoPlano } from "./PlanosDeAluguel";

// Referência: docs/telas/html/Veiculo-Precos-Desktop.dc.html e Veiculo-Precos-Mobile.dc.html (T-496, ADR 0041, VEI-12 a VEI-17).
// A tela guarda o que a pessoa digita (rascunho) e chama `POST .../simular/` a cada mudança, com espera de 400 ms. Todo número
// calculado (margem, parcela, juros, "recebe pela moto", alertas) vem da API; aqui só se formata.

const CHAVE = (id: number) => ["veiculo-precos", id] as const;

function Quadro({ rotulo, children, apoio }: { rotulo: string; children: ReactNode; apoio?: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-[2px] rounded-md bg-surface-sunken px-4 py-[14px]">
      <span className="text-[13px] text-ink-muted">{rotulo}</span>
      {children}
      {apoio && <span className="text-[13px] text-ink-muted">{apoio}</span>}
    </div>
  );
}

const NUMERO_GRANDE = "text-[22px] font-semibold leading-7 tracking-[-0.01em]";

type Confirmacao = { tipo: "plano" | "compra"; chave: string; nome: string; ultimo: boolean };
type Juros = { mensagem: string; aoConfirmar: () => void };

function Tela({ id, dados }: { id: number; dados: Precos }) {
  const cliente = useQueryClient();
  const celular = useCelular();
  const hoje = useAmbiente()?.hoje ?? new Date().toISOString().slice(0, 10);
  const base = useMemo(() => rascunhoDoDocumento(dados), [dados]);
  const [rascunho, setRascunho] = useState<Rascunho>(base);
  const [errosSalvar, setErrosSalvar] = useState<ErrosDeCampo>({});
  const [tentouSalvar, setTentouSalvar] = useState(false);
  const [tentaram, setTentaram] = useState<Set<string>>(new Set());
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [custos, setCustos] = useState(false);
  const [confirmando, setConfirmando] = useState<Confirmacao | null>(null);
  const [juros, setJuros] = useState<Juros | null>(null);
  const somenteLeitura = !dados.pode_editar;

  // Simulação: o documento com as mudanças, debounced. Sem mudança (ou com texto inválido) vale o que a API mostrou por último.
  const montado = useMemo(() => corpoDaDiferenca(rascunho, base), [rascunho, base]);
  const simulavel = !somenteLeitura && montado.mudou && Object.keys(montado.erros).length === 0;
  const chaveSim = useAtrasado(simulavel ? JSON.stringify({ corpo: montado.corpo, enviados: montado.planosEnviados }) : null);
  const simulado = useQuery({
    queryKey: ["veiculo-precos-simular", id, chaveSim],
    queryFn: () => veiculos.simularPrecos(id, (JSON.parse(chaveSim as string) as { corpo: PrecosEntrada }).corpo),
    enabled: chaveSim !== null,
    placeholderData: keepPreviousData,
    retry: false,
  });
  const exibido: Precos = montado.mudou && simulado.data ? simulado.data : dados;
  const errosDaSimulacao: ErrosDeCampo = useMemo(() => {
    if (!(simulado.error instanceof ErroApi) || !chaveSim) return {};
    const todos = errosDaApi(simulado.error.campos, (JSON.parse(chaveSim) as { enviados: string[] }).enviados);
    // Ao vivo, só o que a pessoa vê enquanto digita a compra e a venda; o resto aparece ao salvar ou ligar.
    return Object.fromEntries(Object.entries(todos).filter(([k]) => k.startsWith("compra.") || k === "valor_venda_centavos"));
  }, [simulado.error, chaveSim]);
  const erros: ErrosDeCampo = { ...(tentouSalvar ? montado.erros : {}), ...errosDaSimulacao, ...errosSalvar };

  const gravar = useMutation({ mutationFn: (corpo: PrecosEntrada) => veiculos.salvarPrecos(id, corpo) });

  function guardar(resposta: Precos) {
    cliente.setQueryData(CHAVE(id), resposta);
    void cliente.invalidateQueries({ queryKey: ["veiculo", id] });
    void cliente.invalidateQueries({ queryKey: ["veiculos"] });
  }

  function tratarErro(e: unknown, m: CorpoMontado, retomar: () => void) {
    if (e instanceof ErroApi && e.status === 409 && e.codigo === "VEI-16") {
      setJuros({ mensagem: e.message, aoConfirmar: retomar });
      return;
    }
    if (e instanceof ErroApi && e.campos) {
      const mapeados = errosDaApi(e.campos, m.planosEnviados);
      setErrosSalvar(mapeados);
      setTentouSalvar(true);
      setTentaram((t) => new Set([...t, ...m.planosEnviados]));
      return;
    }
    setErroGeral(mensagemDoErro(e));
  }

  async function salvar(confirmarJuros = false) {
    setErroGeral(null);
    setAviso(null);
    const m = corpoDaDiferenca(rascunho, base, { confirmarJuros });
    if (Object.keys(m.erros).length) return setTentouSalvar(true);
    if (!m.mudou) return;
    if (!confirmarJuros && exibido.pede_confirmacao_juros) {
      const alerta = exibido.alertas.find((a) => a.codigo === "VEI-16");
      return setJuros({ mensagem: alerta?.mensagem ?? "Juros acima de 1% ao mês pedem confirmação.", aoConfirmar: () => void salvar(true) });
    }
    setOcupado("tela");
    try {
      const resposta = await gravar.mutateAsync(m.corpo);
      guardar(resposta);
      setRascunho(rascunhoDoDocumento(resposta));
      setErrosSalvar({});
      setTentouSalvar(false);
      setTentaram(new Set());
      setAviso("Preços salvos.");
    } catch (e) {
      tratarErro(e, m, () => void salvar(true));
    } finally {
      setOcupado(null);
    }
  }

  /** Liga e desliga: grava só aquele plano (ou a compra) e só então o interruptor muda. */
  async function gravarLiga(chave: string, m: CorpoMontado, depois: (r: Precos) => void, retomar: () => void) {
    setErroGeral(null);
    setAviso(null);
    if (Object.keys(m.erros).length) {
      setErrosSalvar(m.erros);
      setTentaram((t) => new Set([...t, chave]));
      return;
    }
    setOcupado(chave);
    try {
      const resposta = await gravar.mutateAsync(m.corpo);
      guardar(resposta);
      depois(resposta);
      setErrosSalvar((e) => Object.fromEntries(Object.entries(e).filter(([k]) => !k.startsWith(`plano.${chave}.`) && !(chave === "compra" && k.startsWith("compra.")))));
    } catch (e) {
      tratarErro(e, m, retomar);
    } finally {
      setOcupado(null);
    }
  }

  async function mudarLigadoDoPlano(chave: string, ligado: boolean) {
    const p = rascunho.planos.find((x) => x.chave === chave);
    if (!p) return;
    const m: CorpoMontado = ligado || p.id == null ? corpoDoPlano({ ...p, ligado }) : { corpo: { planos: [{ id: p.id, ligado: false }], confirmar_juros: false }, erros: {}, planosEnviados: [chave], mudou: true };
    await gravarLiga(
      chave,
      m,
      (resposta) => {
        const novo = resposta.planos.find((x) => chaveDoPlano(x) === chave || (p.tipo !== "outro" && x.tipo === p.tipo));
        if (novo) setRascunho((r) => ({ ...r, planos: r.planos.map((x) => (x.chave === chave ? planoParaRascunho(novo) : x)) }));
      },
      () => void mudarLigadoDoPlano(chave, ligado),
    );
  }

  async function mudarLigadoDaCompra(ligado: boolean, confirmarJuros = false) {
    const m = corpoDaCompra({ ...rascunho.compra, ligado }, { confirmarJuros });
    await gravarLiga("compra", m, (resposta) => setRascunho((r) => ({ ...r, compra: compraParaRascunho(resposta.plano_compra) })), () => void mudarLigadoDaCompra(ligado, true));
  }

  function pedirParaLigar(chave: string, ligado: boolean) {
    if (ligado) return void mudarLigadoDoPlano(chave, true);
    const p = rascunho.planos.find((x) => x.chave === chave);
    setConfirmando({ tipo: "plano", chave, nome: p?.rotulo.toLowerCase() ?? "", ultimo: ehOUltimoLigado(dados, chave) });
  }

  async function mudarAgendado(chave: string, agendado: { valor: string; data: string } | null) {
    const p = rascunho.planos.find((x) => x.chave === chave);
    if (!p) return;
    setErroGeral(null);
    const centavos = agendado ? centavosDoCampo(agendado.valor) : null;
    if (agendado && centavos === undefined) return setErrosSalvar({ [`plano.${chave}.agendado`]: "Informe um valor em reais, como 289,00." });
    const m: CorpoMontado = {
      corpo: { planos: [{ ...(p.id != null ? { id: p.id } : { tipo: p.tipo }), agendado: agendado ? { valor_centavos: centavos as number, a_partir_de: agendado.data } : null }], confirmar_juros: false },
      erros: {},
      planosEnviados: [chave],
      mudou: true,
    };
    setOcupado(chave);
    try {
      guardar(await gravar.mutateAsync(m.corpo));
      setErrosSalvar((e) => Object.fromEntries(Object.entries(e).filter(([k]) => k !== `plano.${chave}.agendado`)));
    } catch (e) {
      tratarErro(e, m, () => undefined);
    } finally {
      setOcupado(null);
    }
  }

  const editarPlano = (chave: string, mudanca: Partial<PlanoRascunho>) => {
    setRascunho((r) => ({ ...r, planos: r.planos.map((p) => (p.chave === chave ? { ...p, ...mudanca } : p)) }));
    setAviso(null);
    setErrosSalvar((e) => Object.fromEntries(Object.entries(e).filter(([k]) => !k.startsWith(`plano.${chave}.`))));
  };
  const editarCompra = (mudanca: Partial<CompraRascunho>) => {
    setRascunho((r) => ({ ...r, compra: { ...r.compra, ...mudanca } }));
    setAviso(null);
    setErrosSalvar((e) => Object.fromEntries(Object.entries(e).filter(([k]) => !k.startsWith("compra."))));
  };
  const editarRegra = (campo: keyof RegrasRascunho, valor: string) => {
    setRascunho((r) => ({ ...r, regras: { ...r.regras, [campo]: valor } }));
    setAviso(null);
    setErrosSalvar((e) => Object.fromEntries(Object.entries(e).filter(([k]) => !k.startsWith("regras."))));
  };

  const acoes: AcoesDoPlano = {
    editar: editarPlano,
    ligar: pedirParaLigar,
    agendar: (chave, valor, data) => void mudarAgendado(chave, { valor, data }),
    desfazerAgendado: (chave) => void mudarAgendado(chave, null),
  };

  const v = exibido.veiculo;
  const nomeDoVeiculo = `${v.marca} ${v.modelo}`;
  const botoes = (
    <>
      <Link href={`/veiculos/${v.id}`} className="wl-btn wl-btn--quiet">
        Cancelar
      </Link>
      <Button variante="solido" disabled={!montado.mudou || ocupado === "tela"} onClick={() => void salvar()}>
        {ocupado === "tela" ? "Salvando…" : "Salvar preços"}
      </Button>
    </>
  );
  const campoDaRegra = (rotulo: string, campo: keyof RegrasRascunho, apoio?: string) => {
    const erro = erros[`regras.${campo === "kmExcedente" ? "km_excedente_centavos" : campo === "diaAtraso" ? "dia_atraso_centavos" : campo === "multaMinima" ? "multa_minima_centavos" : campo === "descontoPct" ? "desconto_sem_aprovacao_pct" : "prazo_devolucao_caucao_dias"}`];
    return (
      <label className={`wl-field wl-field--cheio min-w-0 ${erro ? "wl-field--error" : ""}`}>
        <span className="wl-field__label">{rotulo}</span>
        <input className="wl-input" value={rascunho.regras[campo]} disabled={somenteLeitura} onChange={(e) => editarRegra(campo, e.target.value)} />
        {(erro ?? apoio) && <span className="wl-field__hint">{erro ?? apoio}</span>}
      </label>
    );
  };
  const venda = erros["valor_venda_centavos"];

  return (
    <div className="flex flex-col gap-4 md:gap-6">
      <nav aria-label="Caminho" className="hidden gap-[6px] text-[14px] text-ink-muted md:flex">
        <Link href="/veiculos" className="text-ink-muted no-underline">
          Veículos
        </Link>{" "}
        /{" "}
        <Link href={`/veiculos/${v.id}`} className="text-ink-muted no-underline">
          {placaComHifen(v.placa)}
        </Link>{" "}
        / <span>Preços</span>
      </nav>

      <header className="flex flex-wrap items-center gap-3 md:items-end md:gap-4">
        <Link href={`/veiculos/${v.id}`} aria-label="Voltar" className="wl-icon-btn md:hidden" style={{ width: 44, height: 44 }}>
          <svg className="wl-i" viewBox="0 0 24 24" aria-hidden="true">
            <path d="m15 6-6 6 6 6" />
          </svg>
        </Link>
        <div className="min-w-0 flex-1 md:flex-none">
          <h1 className="text-[20px] font-semibold leading-6 md:text-display">Planos e preços</h1>
          <div className="mt-[2px] text-[13px] text-ink-muted md:mt-[6px] md:text-[15px]">
            {nomeDoVeiculo} · <span className="wl-mono">{placaComHifen(v.placa)}</span>
          </div>
        </div>
        {!somenteLeitura && !celular && <div className="ml-auto flex gap-2">{botoes}</div>}
      </header>

      {exibido.aviso_preco && <Aviso>{exibido.aviso_preco}</Aviso>}
      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}
      {erroGeral && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {erroGeral}
        </p>
      )}
      {somenteLeitura && <p className="text-[13px] text-ink-muted">Você vê os preços desta moto, mas só o administrador altera.</p>}

      <Panel
        titulo="Custo e venda"
        subtitulo="Base de todas as margens desta moto."
        acao={
          exibido.custos && !somenteLeitura ? (
            <Button variante="quieto" compacto onClick={() => setCustos(true)}>
              Editar custos mensais
            </Button>
          ) : undefined
        }
      >
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          {exibido.pago_na_moto && (
            <Quadro
              rotulo="Pago na moto"
              apoio={
                exibido.pago_na_moto.compra_centavos != null ? (
                  <>
                    compra {dinheiro(exibido.pago_na_moto.compra_centavos)} + despesas {dinheiro(exibido.pago_na_moto.despesas_centavos)} ·{" "}
                    <Link href="/financeiro/despesas" className="text-ink-muted">
                      ver
                    </Link>
                  </>
                ) : (
                  <>
                    só despesas {dinheiro(exibido.pago_na_moto.despesas_centavos)} · <Link href="/financeiro/despesas" className="text-ink-muted">ver</Link>
                  </>
                )
              }
            >
              <b className={NUMERO_GRANDE}>{exibido.pago_na_moto.total_centavos != null ? dinheiro(exibido.pago_na_moto.total_centavos) : "—"}</b>
            </Quadro>
          )}
          <label className={`flex min-w-0 flex-col gap-[2px] rounded-md bg-surface-sunken px-4 py-[14px] ${venda ? "wl-field--error" : ""}`}>
            <span className="text-[13px] text-ink-muted">Valor de venda</span>
            <input
              className="wl-input w-full bg-surface text-[18px] font-semibold"
              inputMode="decimal"
              placeholder="R$ 0,00"
              value={rascunho.valorVenda}
              disabled={somenteLeitura}
              aria-invalid={venda ? true : undefined}
              onChange={(e) => {
                setRascunho((r) => ({ ...r, valorVenda: e.target.value }));
                setAviso(null);
                setErrosSalvar((x) => Object.fromEntries(Object.entries(x).filter(([k]) => k !== "valor_venda_centavos")));
              }}
            />
            <span className={`text-[13px] ${venda ? "text-critical-ink" : "text-ink-muted"}`}>{venda ?? (exibido.fipe_centavos != null ? `FIPE ${dinheiro(exibido.fipe_centavos)}` : "")}</span>
          </label>
          {exibido.custos && (
            <Quadro rotulo="Custos por mês" apoio="manutenção, seguro, IPVA, rastreador">
              <b className={NUMERO_GRANDE}>{dinheiro(exibido.custos.custo_mes_centavos)}</b>
            </Quadro>
          )}
          {exibido.custos && (
            <Quadro rotulo="Ocupação esperada" apoio={`frota nos últimos 90 dias: ${textoDaOcupacao(exibido.ocupacao_real_90d_pct)}`}>
              <b className={NUMERO_GRANDE}>{exibido.custos.ocupacao_esperada_pct != null ? textoDaOcupacao(exibido.custos.ocupacao_esperada_pct) : "—"}</b>
            </Quadro>
          )}
        </div>
      </Panel>

      <PlanosDeAluguel
        rascunho={rascunho.planos}
        exibidos={exibido.planos}
        erros={erros}
        somenteLeitura={somenteLeitura}
        acoes={acoes}
        ocupado={ocupado}
        tentaram={tentaram}
        hoje={hoje}
        mensagemDaLiga={null}
      />

      <LocacaoComCompra
        c={rascunho.compra}
        atual={exibido.plano_compra}
        alertas={exibido.alertas}
        pagoNaMoto={exibido.pago_na_moto?.total_centavos}
        erros={erros}
        somenteLeitura={somenteLeitura}
        ocupado={ocupado === "compra"}
        aoEditar={editarCompra}
        aoLigar={(ligado) => (ligado ? void mudarLigadoDaCompra(true) : setConfirmando({ tipo: "compra", chave: "compra", nome: "locação com compra", ultimo: ehOUltimoLigado(dados, "compra") }))}
      />

      <Panel titulo="Regras desta moto">
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          {campoDaRegra("Km excedente", "kmExcedente")}
          {campoDaRegra("Atraso na devolução", "diaAtraso")}
          {campoDaRegra("Desconto sem aprovação", "descontoPct")}
          {campoDaRegra("Devolver a caução em", "prazoCaucao")}
          {campoDaRegra("Multa mínima da devolução antecipada", "multaMinima", "Mínimo da multa ao encerrar antes do fim")}
        </div>
      </Panel>

      {!somenteLeitura && celular && (
        <div className="sticky bottom-[88px] z-20 flex flex-col-reverse gap-3 rounded-lg bg-surface p-3 shadow-pop [&_.wl-btn]:h-[52px] [&_.wl-btn]:w-full [&_.wl-btn]:justify-center">{botoes}</div>
      )}

      {exibido.custos && (
        <CustosMensais
          aberto={custos}
          aoFechar={() => setCustos(false)}
          veiculoId={id}
          atual={exibido.custos}
          ocupacaoReal={exibido.ocupacao_real_90d_pct}
          aoSalvar={(resposta) => {
            guardar(resposta);
            setAviso("Custos salvos.");
          }}
        />
      )}

      <Dialogo
        aberto={confirmando !== null}
        aoFechar={() => setConfirmando(null)}
        tamanho="pequeno"
        titulo={confirmando?.ultimo ? "Desligar o último plano?" : confirmando?.tipo === "compra" ? "Desligar a locação com compra?" : `Desligar o plano ${confirmando?.nome ?? ""}?`}
        descricao={confirmando?.ultimo ? TEXTO_DESLIGAR_O_ULTIMO : TEXTO_DESLIGAR}
        acoes={
          <>
            <Button variante="quieto" onClick={() => setConfirmando(null)}>
              Continuar ligado
            </Button>
            <Button
              variante="solido"
              onClick={() => {
                const c = confirmando;
                setConfirmando(null);
                if (!c) return;
                if (c.tipo === "compra") void mudarLigadoDaCompra(false);
                else void mudarLigadoDoPlano(c.chave, false);
              }}
            >
              Desligar plano
            </Button>
          </>
        }
      />

      <Dialogo
        aberto={juros !== null}
        aoFechar={() => setJuros(null)}
        tamanho="pequeno"
        titulo="Juros acima de 1% ao mês"
        descricao={juros?.mensagem}
        acoes={
          <>
            <Button variante="quieto" onClick={() => setJuros(null)}>
              Voltar
            </Button>
            <Button
              variante="solido"
              onClick={() => {
                const j = juros;
                setJuros(null);
                j?.aoConfirmar();
              }}
            >
              Confirmar e salvar
            </Button>
          </>
        }
      />
    </div>
  );
}

/** `/veiculos/[id]/precos`: planos, regras, custos e locação com compra de um veículo. */
export function PrecosDoVeiculo({ id }: { id: number }) {
  const consulta = useQuery({ queryKey: CHAVE(id), queryFn: () => veiculos.precos(id) });
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  if (!consulta.data)
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Carregando os preços…
      </p>
    );
  return <Tela id={id} dados={consulta.data} />;
}
