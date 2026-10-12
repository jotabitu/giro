"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { Button, Icone, Panel, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { clientes, ErroApi, locacoes, veiculos, type EntradaDaLocacao, type Periodicidade, type PlanoEspecial } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCompleta, dinheiro, dinheiroSemZeros, diaDe, instanteDeLocal, localDeInstante } from "@/lib/formatos";
import { agoraNoDia, useAgora, useAmbiente } from "@/lib/ambiente";
import { corpoDaLocacao, descontoValido, esquemaLocacao, FORMAS_DE_PAGAMENTO, opcoesDeParcelamento, retiradaPadrao, valoresDoRascunho, valoresIniciais, type Modalidade, type ValoresLocacao } from "@/lib/locacao-form";
import { textoDoPeriodo } from "@/lib/locacoes";
import { CartaoDoCliente, CartaoDoVeiculo, EscolherCliente, EscolherVeiculo } from "./SeletoresDaLocacao";

// Referência: docs/telas/html/Locacao-Desktop.dc.html e Locacao-Mobile.dc.html.
// A tela só envia o formulário; preço, parcelas, caução, desconto e impedimentos voltam da simulação da API (POST /api/locacoes/simular/).

const UNIDADE: Record<Periodicidade, { por: string; plural: string }> = {
  diaria: { por: "dia", plural: "diárias" },
  semanal: { por: "semana", plural: "semanas" },
  mensal: { por: "mês", plural: "meses" },
};

function useAtraso<T>(valor: T, ms = 300): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return atrasado;
}

function Etapas() {
  const etapas = ["1 · Dados", "2 · Vistoria", "3 · Assinatura"];
  return (
    <ol className="flex flex-wrap gap-2" aria-label="Etapas">
      {etapas.map((e, i) => (
        <li key={e} aria-current={i === 0 ? "step" : undefined} className={`wl-badge ${i === 0 ? "wl-badge--solid" : "wl-badge--surface"}`}>
          {e}
        </li>
      ))}
    </ol>
  );
}

function Plano({ ativo, nome, detalhe, onClick }: { ativo: boolean; nome: string; detalhe?: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={`flex min-h-[64px] flex-col items-start justify-center gap-0.5 rounded-lg px-4 py-3 text-left ${ativo ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
    >
      <span className="text-body font-medium">{nome}</span>
      {detalhe && <small className={`text-caption ${ativo ? "opacity-80" : "text-ink-muted"}`}>{detalhe}</small>}
    </button>
  );
}

function detalheDoPlano(p: PlanoEspecial): string {
  if (p.regra === "preco_fixo" && p.preco_centavos) return `${dinheiro(p.preco_centavos)} / ${UNIDADE[p.periodicidade].por}`;
  if (p.desconto_pct && p.a_partir_do_periodo) return `${Number(p.desconto_pct)}% a partir do ${p.a_partir_do_periodo}º ${UNIDADE[p.periodicidade].por}`;
  return p.condicoes;
}

/** Nova locação (etapa 1, Dados): simula a cada mudança, guarda o rascunho e confirma. */
export function NovaLocacao({ clienteInicial, veiculoInicial, rascunhoInicial }: { clienteInicial?: number; veiculoInicial?: number; rascunhoInicial?: number }) {
  const router = useRouter();
  const cache = useQueryClient();
  const [escolhendo, setEscolhendo] = useState<"cliente" | "veiculo" | null>(null);
  const [rascunhoId, setRascunhoId] = useState<number | null>(rascunhoInicial ?? null);
  const agoraDaPagina = useAgora();
  const agora = useRef(agoraDaPagina);

  const { register, handleSubmit, watch, setValue, reset, clearErrors, formState: { errors, dirtyFields } } = useForm<ValoresLocacao>({
    resolver: zodResolver(esquemaLocacao) as unknown as Resolver<ValoresLocacao>,
    defaultValues: valoresIniciais(clienteInicial ?? null, veiculoInicial ?? null, agora.current),
  });
  const v = watch();

  // O "hoje" da API pode chegar depois do primeiro desenho: a retirada padrão acompanha, se ninguém mexeu nela.
  const hojeDaApi = useAmbiente()?.hoje;
  useEffect(() => {
    if (!hojeDaApi || rascunhoInicial || dirtyFields.inicio) return;
    agora.current = agoraNoDia(hojeDaApi);
    setValue("inicio", retiradaPadrao(agora.current));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só quando o hoje da API muda
  }, [hojeDaApi]);

  const extras = useQuery({ queryKey: ["extras"], queryFn: () => locacoes.extras() });
  const planos = useQuery({ queryKey: ["planos-especiais"], queryFn: () => locacoes.planosEspeciais() });
  const listaPlanos = useMemo(() => planos.data?.resultados ?? [], [planos.data]);
  const cliente = useQuery({ queryKey: ["cliente", v.cliente_id], queryFn: () => clientes.obter(v.cliente_id ?? 0), enabled: !!v.cliente_id, retry: false });
  const veiculo = useQuery({ queryKey: ["veiculo", v.veiculo_id], queryFn: () => veiculos.obter(v.veiculo_id ?? 0), enabled: !!v.veiculo_id, retry: false });

  // Retomar um rascunho: o formulário volta do detalhe da locação.
  const rascunho = useQuery({ queryKey: ["locacao", rascunhoInicial], queryFn: () => locacoes.obter(rascunhoInicial ?? 0), enabled: !!rascunhoInicial, retry: false });
  const carregado = useRef(false);
  useEffect(() => {
    if (carregado.current || !rascunho.data || !extras.data) return;
    carregado.current = true;
    reset(valoresDoRascunho(rascunho.data, extras.data.resultados));
  }, [rascunho.data, extras.data, reset]);

  const corpo = useMemo(() => corpoDaLocacao(v, listaPlanos), [v, listaPlanos]);
  const corpoAtrasado = useAtraso(JSON.stringify(corpo));
  const simulacao = useQuery({
    queryKey: ["locacao-simulacao", corpoAtrasado],
    queryFn: () => locacoes.simular(JSON.parse(corpoAtrasado) as EntradaDaLocacao),
    enabled: corpoAtrasado !== "null" && planos.isSuccess,
    placeholderData: (anterior) => anterior,
    retry: false,
  });
  const sim = simulacao.data;
  const periodicidade: Periodicidade = corpo?.periodicidade ?? (v.modalidade.startsWith("especial:") ? (listaPlanos.find((p) => `especial:${p.id}` === v.modalidade)?.periodicidade ?? "semanal") : (v.modalidade as Periodicidade));
  const un = UNIDADE[periodicidade];
  const hoje = diaDe(agoraDaPagina.toISOString());

  const erroSim = (campo: string) => campoDoErro(simulacao.error, campo);
  const impedimentos = sim?.impedimentos ?? [];

  const salvar = useMutation({
    mutationFn: async (destino: "vistoria" | "reserva") => {
      if (!corpo) throw new ErroApi(400, "validacao", "Escolha o cliente e o veículo");
      const l = rascunhoId ? await locacoes.atualizar(rascunhoId, corpo) : await locacoes.criar(corpo);
      setRascunhoId(l.id);
      await locacoes.confirmar(l.id, { primeiro_vencimento: v.primeiro_vencimento || null });
      return { id: l.id, destino };
    },
    onSuccess: async ({ id, destino }) => {
      await cache.invalidateQueries({ queryKey: ["locacoes"] });
      router.push(destino === "vistoria" ? `/locacoes/${id}/vistoria` : `/locacoes/${id}`);
    },
  });
  const enviar = (destino: "vistoria" | "reserva") =>
    handleSubmit(
      () => salvar.mutate(destino),
      () => undefined,
    )();

  const descontoErro = !descontoValido(v.desconto) ? "Informe um percentual, como 5 ou 2,5" : erroSim("desconto_pct");
  const pronto = !!sim && !simulacao.isError && impedimentos.length === 0 && !salvar.isPending && !descontoErro;
  const erroDoEnvio = salvar.error instanceof ErroApi ? salvar.error : null;
  const linkDoErro = typeof erroDoEnvio?.detalhes?.link === "string" ? erroDoEnvio.detalhes.link : null;

  const escolherCliente = (id: number) => {
    setValue("cliente_id", id, { shouldValidate: true });
    clearErrors("cliente_id");
    setEscolhendo(null);
  };
  const escolherVeiculo = (id: number) => {
    setValue("veiculo_id", id, { shouldValidate: true });
    clearErrors("veiculo_id");
    setEscolhendo(null);
  };
  const preco = veiculo.data?.preco_vigente;
  const alternarExtra = (id: number) => setValue("extras", v.extras.includes(id) ? v.extras.filter((x) => x !== id) : [...v.extras, id]);
  const opcoes = opcoesDeParcelamento(periodicidade);
  const primeiroVencimento = v.primeiro_vencimento || sim?.parcelas_previstas[0]?.vencimento || "";
  const fimMostrado = v.fim || (sim?.fim_previsto ? localDeInstante(sim.fim_previsto) : "");
  const fimInvalido = v.fim !== "" && instanteDeLocal(v.fim) === null;

  if (rascunhoInicial && rascunho.isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-4">
        <p className="text-body">{mensagemDoErro(rascunho.error)}</p>
        <Link href="/locacoes" className="wl-btn">
          Voltar para Locações
        </Link>
      </div>
    );
  }

  const modalidade = (m: Modalidade) => () => {
    setValue("modalidade", m);
    setValue("fim", "");
    if (m !== "mensal") setValue("parcelamento_mensal", "a_vista");
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <nav aria-label="Caminho" className="hidden text-caption text-ink-muted md:block">
            <Link href="/locacoes" className="text-ink-muted">
              Locações
            </Link>{" "}
            / Nova
          </nav>
          <h1 className="text-title md:text-display">Nova locação</h1>
        </div>
        <div className="md:ml-auto">
          <Etapas />
        </div>
      </header>

      <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex min-w-0 flex-col gap-6">
          <Panel titulo="Cliente e veículo">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <CartaoDoCliente cliente={cliente.data} completo={cliente.data} hoje={hoje} onTrocar={() => setEscolhendo("cliente")} />
                {errors.cliente_id && <p role="alert" className="mt-2 text-caption text-critical">{errors.cliente_id.message}</p>}
                {cliente.isError && <p role="alert" className="mt-2 text-caption text-critical">{mensagemDoErro(cliente.error)}</p>}
              </div>
              <div>
                <CartaoDoVeiculo veiculo={veiculo.data} onTrocar={() => setEscolhendo("veiculo")} />
                {errors.veiculo_id && <p role="alert" className="mt-2 text-caption text-critical">{errors.veiculo_id.message}</p>}
                {veiculo.isError && <p role="alert" className="mt-2 text-caption text-critical">{mensagemDoErro(veiculo.error)}</p>}
              </div>
            </div>
          </Panel>

          <Panel titulo="Plano e período">
            <div className="flex flex-col gap-4">
              <div role="group" aria-label="Modalidade" className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <Plano ativo={v.modalidade === "diaria"} nome="Diária" detalhe={preco ? `${dinheiro(preco.diaria_centavos)} / dia` : undefined} onClick={modalidade("diaria")} />
                <Plano ativo={v.modalidade === "semanal"} nome="Semanal" detalhe={preco ? `${dinheiro(preco.semanal_centavos)} / semana` : undefined} onClick={modalidade("semanal")} />
                <Plano ativo={v.modalidade === "mensal"} nome="Mensal" detalhe={preco ? `${dinheiroSemZeros(preco.mensal_centavos)} / mês` : undefined} onClick={modalidade("mensal")} />
                {listaPlanos.map((p) => (
                  <Plano key={p.id} ativo={v.modalidade === `especial:${p.id}`} nome={p.nome} detalhe={detalheDoPlano(p)} onClick={modalidade(`especial:${p.id}`)} />
                ))}
              </div>
              {erroSim("plano_especial_id") && <p role="alert" className="text-caption text-critical">{erroSim("plano_especial_id")}</p>}
              <div className="grid gap-4 md:grid-cols-3">
                <TextField
                  cheio
                  mono
                  rotulo="Retirada"
                  type="datetime-local"
                  erro={errors.inicio?.message ?? erroSim("inicio")}
                  {...register("inicio")}
                />
                <TextField
                  cheio
                  mono
                  rotulo="Devolução prevista"
                  type="datetime-local"
                  value={fimMostrado}
                  onChange={(e) => setValue("fim", e.target.value)}
                  dica={sim ? `${textoDoPeriodo(sim.periodos, periodicidade)}${periodicidade === "diaria" ? "" : ` · renova a cada ${un.por}`}` : undefined}
                  erro={fimInvalido ? "Informe a data e a hora" : (erroSim("fim_previsto") ?? erroSim("periodos"))}
                />
                <TextField cheio rotulo="Franquia de km" value="Livre" readOnly dica="Km livre em todos os planos" />
              </div>
            </div>
          </Panel>

          <Panel titulo="Cobrança">
            <div className="grid gap-4 md:grid-cols-2">
              <CampoSelecao
                rotulo="Parcelamento"
                value={opcoes.some((o) => o.valor === v.parcelamento_mensal) ? v.parcelamento_mensal : "a_vista"}
                onChange={(e) => setValue("parcelamento_mensal", e.target.value as ValoresLocacao["parcelamento_mensal"])}
                opcoes={opcoes.map((o) => ({ valor: o.valor, rotulo: o.rotulo }))}
              />
              <CampoSelecao rotulo="Forma de pagamento" value={v.forma_pagamento} onChange={(e) => setValue("forma_pagamento", e.target.value as ValoresLocacao["forma_pagamento"])} opcoes={FORMAS_DE_PAGAMENTO.map((f) => ({ valor: f.valor, rotulo: f.rotulo }))} />
              <TextField
                cheio
                mono
                rotulo="Primeiro vencimento"
                type="date"
                value={primeiroVencimento}
                onChange={(e) => setValue("primeiro_vencimento", e.target.value)}
                dica={primeiroVencimento ? dataCompleta(primeiroVencimento) : undefined}
              />
              <TextField cheio rotulo="Caução" value={sim ? dinheiro(sim.caucao_centavos) : "—"} readOnly dica="Devolvida no encerramento sem pendências" />
              <TextField
                cheio
                rotulo="Desconto (%)"
                inputMode="decimal"
                erro={descontoErro}
                dica={sim?.precisa_aprovacao_desconto ? "Este desconto precisa da aprovação do gerente. As parcelas saem sem desconto até a decisão." : undefined}
                {...register("desconto")}
              />
            </div>
            <p className="mt-4 flex items-start gap-2 rounded-md bg-surface-sunken px-4 py-3 text-caption text-ink-muted">
              <Icone de={Info} />
              Com 15 dias de atraso numa parcela, o cliente é bloqueado e o gerente é avisado.
            </p>
          </Panel>

          <Panel titulo="Adicionais">
            {extras.isPending && <p className="text-body text-ink-muted">Carregando os adicionais…</p>}
            {extras.isError && <p role="alert" className="text-body">{mensagemDoErro(extras.error)}</p>}
            <div className="flex flex-col">
              {extras.data?.resultados.map((x) => (
                <label key={x.id} className="flex min-h-[44px] items-center gap-3 border-b border-line py-2 text-body last:border-b-0">
                  <input type="checkbox" className="h-5 w-5" checked={v.extras.includes(x.id)} onChange={() => alternarExtra(x.id)} />
                  <span className="flex-1">{x.nome}</span>
                  <span className="text-ink-muted">
                    {dinheiro(x.valor_centavos)} / {x.cobranca === "unica" ? "único" : un.por}
                  </span>
                </label>
              ))}
            </div>
          </Panel>
        </div>

        <aside className="flex min-w-0 flex-col gap-6 md:sticky md:top-6">
          <Panel titulo="Resumo">
            {!sim && !simulacao.isError && <p className="text-body text-ink-muted">{corpo ? "Calculando…" : "Escolha o cliente e o veículo para ver os valores."}</p>}
            {simulacao.isError && !(simulacao.error instanceof ErroApi && simulacao.error.campos) && <p role="alert" className="text-body">{mensagemDoErro(simulacao.error)}</p>}
            {sim && (
              <div aria-busy={simulacao.isFetching}>
                <dl>
                  {sim.linhas.map((l) => (
                    <div key={l.rotulo} className="flex justify-between gap-3 border-b border-line py-[11px] text-body">
                      <dt className="text-ink-muted">{l.rotulo}</dt>
                      <dd className="font-medium">{l.rotulo === "Desconto" ? `– ${dinheiro(l.valor_centavos)}` : dinheiro(l.valor_centavos)}</dd>
                    </div>
                  ))}
                  <div className="flex justify-between gap-3 py-[11px] text-body">
                    <dt className="text-ink-muted">Valor por {un.por}</dt>
                    <dd className="font-medium">{dinheiro(sim.valor_periodo_centavos)}</dd>
                  </div>
                </dl>
                <div className="mt-2 grid grid-cols-2 gap-3">
                  {periodicidade !== "diaria" && (
                    <div className="rounded-md bg-surface-sunken px-4 py-3">
                      <div className="text-caption text-ink-muted">Próximas {un.plural}</div>
                      <div className="text-body font-semibold">{dinheiro(sim.proximos_periodos_centavos)}</div>
                    </div>
                  )}
                  <div className={`rounded-md bg-solid px-4 py-3 text-on-solid ${periodicidade === "diaria" ? "col-span-2" : ""}`}>
                    <div className="text-caption opacity-80">Hoje, na retirada</div>
                    <div className="text-body font-semibold">{dinheiro(sim.hoje_na_retirada_centavos)}</div>
                  </div>
                </div>
                <p className="mt-3 text-caption text-ink-muted">{sim.texto_retirada}</p>
                {impedimentos.length > 0 && (
                  <ul role="alert" className="mt-4 flex flex-col gap-2 rounded-md bg-critical-soft px-4 py-3 text-caption text-critical-ink">
                    {impedimentos.map((i) => (
                      <li key={i.codigo}>{i.mensagem}</li>
                    ))}
                  </ul>
                )}
                {sim.avisos.length > 0 && (
                  <ul className="mt-4 flex flex-col gap-2 text-caption text-ink-muted">
                    {sim.avisos.map((a) => (
                      <li key={a.codigo}>
                        {a.mensagem}
                        {a.link && (
                          <>
                            {" "}
                            <Link href={a.link} className="underline">
                              Abrir
                            </Link>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Panel>

          <section className="wl-panel flex flex-col gap-3">
            {salvar.isError && (
              <p role="alert" className="text-body text-critical">
                {mensagemDoErro(salvar.error)}{" "}
                {linkDoErro && (
                  <Link href={linkDoErro} className="underline">
                    Abrir os modelos de contrato
                  </Link>
                )}
              </p>
            )}
            <Button variante="solido" disabled={!pronto} onClick={() => enviar("vistoria")}>
              {salvar.isPending ? "Salvando…" : "Continuar para vistoria"}
            </Button>
            <Button variante="quieto" disabled={!pronto} onClick={() => enviar("reserva")}>
              Salvar como reserva
            </Button>
          </section>
        </aside>
      </div>

      {escolhendo === "cliente" && <EscolherCliente aoFechar={() => setEscolhendo(null)} aoEscolher={(c) => escolherCliente(c.id)} />}
      {escolhendo === "veiculo" && <EscolherVeiculo aoFechar={() => setEscolhendo(null)} aoEscolher={(x) => escolherVeiculo(x.id)} />}
    </div>
  );
}

