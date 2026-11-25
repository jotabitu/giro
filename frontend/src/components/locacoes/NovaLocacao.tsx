"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { BarraDeAcoes, Button, Icone, Panel, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { clientes, ErroApi, locacoes, veiculos, type EntradaDaLocacao, type Periodicidade } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCompleta, dinheiro, diaDe, instanteDeLocal, localDeInstante } from "@/lib/formatos";
import { agoraNoDia, useAgora, useAmbiente } from "@/lib/ambiente";
import { useFilial } from "@/lib/filial-escolhida";
import { corpoDaLocacao, descontoValido, esquemaLocacao, formasDoPlano, linhasDoPlano, periodicidadeDoPlano, retiradaPadrao, valoresDoRascunho, valoresIniciais, valorDoPlano, type ValoresLocacao } from "@/lib/locacao-form";
import { textoDoPeriodo } from "@/lib/locacoes";
import { porPeriodoDaCompra, textoDaCaucaoParcelada, textoDoPagamento } from "@/lib/precos-veiculo";
import { CartaoDoCliente, CartaoDoVeiculo, EscolherCliente, EscolherVeiculo } from "./SeletoresDaLocacao";

// Referência: docs/telas/html/Locacao-Desktop.dc.html e Locacao-Mobile.dc.html.
// Os planos, o valor, a caução, a franquia e o prazo mínimo são os do veículo (LOC-01, VEI-12, ADR 0041): a tela só manda o id do plano.
// A tela só envia o formulário; preço, parcelas, caução, desconto e impedimentos voltam da simulação da API (POST /api/locacoes/simular/).

const UNIDADE: Record<Periodicidade, { por: string; plural: string }> = {
  diaria: { por: "dia", plural: "diárias" },
  semanal: { por: "semana", plural: "semanas" },
  quinzenal: { por: "quinzena", plural: "quinzenas" },
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

/** VEI-15: o texto da regra, para o veículo que a API não mandou com aviso. */
const AVISO_SEM_PLANO = "A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda.";

function Plano({ ativo, nome, detalhe, linhas, onClick }: { ativo: boolean; nome: string; detalhe?: string; linhas?: string[]; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={`flex min-h-[64px] flex-col items-start justify-center gap-0.5 rounded-lg px-4 py-3 text-left ${ativo ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
    >
      <span className="text-body font-medium">{nome}</span>
      {detalhe && <small className={`text-caption ${ativo ? "opacity-80" : "text-ink-muted"}`}>{detalhe}</small>}
      {linhas?.map((l) => (
        <small key={l} className={`text-caption ${ativo ? "opacity-80" : "text-ink-muted"}`}>
          {l}
        </small>
      ))}
    </button>
  );
}

/** Nova locação (etapa 1, Dados): simula a cada mudança, guarda o rascunho e confirma. */
export function NovaLocacao({ clienteInicial, veiculoInicial, rascunhoInicial, tipoInicial, planoInicial }: { clienteInicial?: number; veiculoInicial?: number; rascunhoInicial?: number; tipoInicial?: "comum" | "intencao_compra"; planoInicial?: number }) {
  const router = useRouter();
  const cache = useQueryClient();
  const [escolhendo, setEscolhendo] = useState<"cliente" | "veiculo" | null>(null);
  const [rascunhoId, setRascunhoId] = useState<number | null>(rascunhoInicial ?? null);
  const agoraDaPagina = useAgora();
  // "Todas as filiais" não cria locação: ela nasce numa filial só (a API pede o X-Filial de uma).
  const todasAsFiliais = useFilial()?.todas ?? false;
  const agora = useRef(agoraDaPagina);

  const { register, handleSubmit, watch, setValue, reset, clearErrors, formState: { errors, dirtyFields } } = useForm<ValoresLocacao>({
    resolver: zodResolver(esquemaLocacao) as unknown as Resolver<ValoresLocacao>,
    defaultValues: { ...valoresIniciais(clienteInicial ?? null, veiculoInicial ?? null, agora.current), tipo: tipoInicial ?? "comum", plano_veiculo_id: planoInicial ?? null },
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
  const compra = v.tipo === "intencao_compra";
  const cliente = useQuery({ queryKey: ["cliente", v.cliente_id], queryFn: () => clientes.obter(v.cliente_id ?? 0), enabled: !!v.cliente_id, retry: false });
  const veiculo = useQuery({ queryKey: ["veiculo", v.veiculo_id], queryFn: () => veiculos.obter(v.veiculo_id ?? 0), enabled: !!v.veiculo_id, retry: false });
  // Os planos ligados do veículo (e o plano de compra dele) vêm da API; plano desligado não aparece (VEI-12).
  const precos = useQuery({ queryKey: ["veiculo-precos", v.veiculo_id], queryFn: () => veiculos.precos(v.veiculo_id ?? 0), enabled: !!v.veiculo_id, retry: false });
  // VEI-21: com o aluguel desligado, nenhum plano de aluguel; a locação com compra fica.
  const ligados = useMemo(() => (precos.data?.aluguel_ligado === false ? [] : (precos.data?.planos ?? []).filter((p) => p.ligado)), [precos.data]);
  const plano = ligados.find((p) => p.id === v.plano_veiculo_id);
  const planoDeCompra = precos.data?.plano_compra?.ligado ? precos.data.plano_compra : null;
  const avisoDoVeiculo = precos.data && ligados.length === 0 ? (precos.data.aviso_aluguel ?? precos.data.aviso_preco ?? AVISO_SEM_PLANO) : null;

  // Retomar um rascunho: o formulário volta do detalhe da locação.
  const rascunho = useQuery({ queryKey: ["locacao", rascunhoInicial], queryFn: () => locacoes.obter(rascunhoInicial ?? 0), enabled: !!rascunhoInicial, retry: false });
  const carregado = useRef(false);
  useEffect(() => {
    if (carregado.current || !rascunho.data || !extras.data) return;
    carregado.current = true;
    reset(valoresDoRascunho(rascunho.data, extras.data.resultados));
  }, [rascunho.data, extras.data, reset]);

  const corpo = useMemo(() => corpoDaLocacao(v, plano), [v, plano]);
  const corpoAtrasado = useAtraso(JSON.stringify(corpo));
  const simulacao = useQuery({
    queryKey: ["locacao-simulacao", corpoAtrasado],
    queryFn: () => locacoes.simular(JSON.parse(corpoAtrasado) as EntradaDaLocacao),
    enabled: corpoAtrasado !== "null" && (compra ? !!planoDeCompra : precos.isSuccess) && !todasAsFiliais,
    placeholderData: (anterior) => anterior,
    retry: false,
  });
  const sim = simulacao.data;
  const periodicidade: Periodicidade = compra ? ((sim?.compra?.periodicidade as Periodicidade | undefined) ?? planoDeCompra?.periodicidade ?? "semanal") : periodicidadeDoPlano(plano?.periodo ?? sim?.plano?.periodo);
  const un = UNIDADE[periodicidade];
  const hoje = diaDe(agoraDaPagina.toISOString());

  const erroSim = (campo: string) => campoDoErro(simulacao.error, campo);
  const avisoDeFilial = todasAsFiliais ? "Escolha uma filial no menu para criar a locação." : erroSim("filial");
  // Erro de campo que nenhum campo da tela mostra: aparece no resumo, para o botão não ficar desligado sem explicação.
  const camposDaTela = ["filial", "plano_veiculo_id", "veiculo_id", "inicio", "fim_previsto", "periodos", "desconto_pct"];
  const erroSemCampo = simulacao.error instanceof ErroApi && simulacao.error.campos ? Object.entries(simulacao.error.campos).find(([c]) => !camposDaTela.includes(c))?.[1] : undefined;
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
  const escolhido = compra ? !!planoDeCompra : !!plano;
  const pronto = escolhido && !todasAsFiliais && !!sim && !simulacao.isError && impedimentos.length === 0 && !salvar.isPending && !descontoErro;
  const erroDoEnvio = salvar.error instanceof ErroApi ? salvar.error : null;
  const linkDoErro = typeof erroDoEnvio?.detalhes?.link === "string" ? erroDoEnvio.detalhes.link : null;
  // LOC-16: sem modelo publicado de locação com intenção de compra, o atalho leva a publicar o modelo.
  const semModeloDeCompra = erroDoEnvio?.codigo === "LOC-16" && !!linkDoErro;

  const escolherCliente = (id: number) => {
    setValue("cliente_id", id, { shouldValidate: true });
    clearErrors("cliente_id");
    setEscolhendo(null);
  };
  const escolherVeiculo = (id: number) => {
    setValue("veiculo_id", id, { shouldValidate: true });
    setValue("plano_veiculo_id", null);
    clearErrors("veiculo_id");
    setEscolhendo(null);
  };
  const alternarExtra = (id: number) => setValue("extras", v.extras.includes(id) ? v.extras.filter((x) => x !== id) : [...v.extras, id]);
  const formas = formasDoPlano(compra ? undefined : plano);
  // Plano novo, forma de pagamento que ele aceita: a API recusa a que ficou de fora (VEI-12).
  useEffect(() => {
    if (!formas.some((f) => f.valor === v.forma_pagamento) && formas[0]) setValue("forma_pagamento", formas[0].valor);
  }, [formas, v.forma_pagamento, setValue]);
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

  const escolherTipo = (tipo: "comum" | "intencao_compra") => () => {
    setValue("tipo", tipo);
    setValue("fim", "");
    salvar.reset();
  };

  const escolherPlano = (id: number | null) => () => {
    setValue("plano_veiculo_id", id);
    setValue("fim", "");
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
          <Panel titulo="Tipo de locação">
            <div role="group" aria-label="Tipo de locação" className="grid grid-cols-2 gap-2">
              <Plano ativo={!compra} nome="Comum" onClick={escolherTipo("comum")} />
              <Plano ativo={compra} nome="Com intenção de compra" onClick={escolherTipo("intencao_compra")} />
            </div>
          </Panel>

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
                {erroSim("veiculo_id") && <p role="alert" className="mt-2 text-caption text-critical">{erroSim("veiculo_id")}</p>}
              </div>
            </div>
          </Panel>

          {compra && (
            <Panel titulo="Plano de compra">
              <div className="flex flex-col gap-4">
                {!v.veiculo_id && <p className="text-body text-ink-muted">Escolha o veículo para ver o plano de compra.</p>}
                {precos.isPending && !!v.veiculo_id && <p className="text-body text-ink-muted">Carregando o plano de compra…</p>}
                {precos.isError && <p role="alert" className="text-body">{mensagemDoErro(precos.error)}</p>}
                {precos.isSuccess && !planoDeCompra && (
                  <p role="status" className="text-body text-ink-muted">
                    Este veículo não tem locação com compra ligada.{" "}
                    <Link href={`/veiculos/${v.veiculo_id}/precos`} className="underline">
                      Abrir Planos e preços
                    </Link>
                  </p>
                )}
                {planoDeCompra && (
                  <div role="group" aria-label="Plano de compra" className="grid gap-2 md:grid-cols-2">
                    <Plano
                      ativo
                      nome="Locação com compra"
                      detalhe={planoDeCompra.resultado ? `${dinheiro(planoDeCompra.resultado.parcela_cliente_centavos)} ${porPeriodoDaCompra(planoDeCompra.periodicidade)}` : undefined}
                      linhas={[`${planoDeCompra.parcelas} parcelas`, ...(planoDeCompra.entrada_centavos > 0 ? [`Entrada ${dinheiro(planoDeCompra.entrada_centavos)}`] : [])]}
                      onClick={() => undefined}
                    />
                  </div>
                )}
                <div className="grid gap-4 md:grid-cols-2">
                  <TextField cheio mono rotulo="Retirada" type="datetime-local" erro={errors.inicio?.message ?? erroSim("inicio")} {...register("inicio")} />
                  <TextField
                    cheio
                    mono
                    rotulo="Fim previsto"
                    type="datetime-local"
                    value={sim?.fim_previsto ? localDeInstante(sim.fim_previsto) : ""}
                    readOnly
                    dica={sim ? `${textoDoPeriodo(sim.periodos, periodicidade)} · o veículo passa ao cliente na última parcela` : undefined}
                  />
                </div>
              </div>
            </Panel>
          )}

          {!compra && (
          <Panel titulo="Plano e período">
            <div className="flex flex-col gap-4">
              {!v.veiculo_id && <p className="text-body text-ink-muted">Escolha o veículo para ver os planos.</p>}
              {precos.isPending && !!v.veiculo_id && <p className="text-body text-ink-muted">Carregando os planos…</p>}
              {precos.isError && <p role="alert" className="text-body">{mensagemDoErro(precos.error)}</p>}
              {avisoDoVeiculo && (
                <p role="status" className="rounded-md bg-surface-sunken px-4 py-3 text-body">
                  {avisoDoVeiculo}{" "}
                  <Link href={`/veiculos/${v.veiculo_id}/precos`} className="underline">
                    Abrir Planos e preços
                  </Link>
                </p>
              )}
              {ligados.length > 0 && (
                <div role="group" aria-label="Plano do veículo" className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  {ligados.map((p) => (
                    <Plano key={p.id} ativo={v.plano_veiculo_id === p.id} nome={p.rotulo} detalhe={valorDoPlano(p)} linhas={linhasDoPlano(p)} onClick={escolherPlano(p.id)} />
                  ))}
                </div>
              )}
              {ligados.length > 0 && !plano && <p className="text-caption text-ink-muted">Escolha o plano para ver a cobrança.</p>}
              {erroSim("plano_veiculo_id") && <p role="alert" className="text-caption text-critical">{erroSim("plano_veiculo_id")}</p>}
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
                <TextField cheio rotulo="Franquia de km" value={plano ? (plano.franquia_km == null ? "Livre" : `${new Intl.NumberFormat("pt-BR").format(plano.franquia_km)} km por ${un.por}`) : "—"} readOnly dica={plano?.franquia_km == null && plano ? "Km livre neste plano" : undefined} />
              </div>
            </div>
          </Panel>
          )}

          {compra && planoDeCompra && (
            <Panel titulo="Cobrança">
              <div className="grid gap-4 md:grid-cols-2">
                <CampoSelecao rotulo="Forma de pagamento" value={v.forma_pagamento} onChange={(e) => setValue("forma_pagamento", e.target.value as ValoresLocacao["forma_pagamento"])} opcoes={formas.map((f) => ({ valor: f.valor, rotulo: f.rotulo }))} />
                {!!sim?.compra?.entrada_centavos && <TextField cheio rotulo="Entrada" value={dinheiro(sim.compra.entrada_centavos)} readOnly dica="Cobrada na retirada" />}
                <TextField cheio rotulo="Primeiro vencimento" mono type="date" value={sim?.parcelas_previstas[0]?.vencimento ?? ""} readOnly dica={sim?.parcelas_previstas[0] ? dataCompleta(sim.parcelas_previstas[0].vencimento) : undefined} />
                <TextField cheio rotulo="Caução" value={sim ? dinheiro(sim.caucao_centavos) : "—"} readOnly dica="Abatida da última parcela" />
              </div>
              <p className="mt-4 flex items-start gap-2 rounded-md bg-surface-sunken px-4 py-3 text-caption text-ink-muted">
                <Icone de={Info} />
                Com 15 dias de atraso numa parcela, o cliente é bloqueado e o gerente é avisado.
              </p>
            </Panel>
          )}

          {!compra && !!plano && (
            <Panel titulo="Cobrança">
              <div className="grid gap-4 md:grid-cols-2">
                <TextField cheio rotulo="Como o cliente paga" value={plano ? textoDoPagamento(plano.como_paga ?? "tudo_na_retirada", plano.parcela_do_mes) : ""} readOnly dica="Definido no plano deste veículo" />
                <CampoSelecao rotulo="Forma de pagamento" value={v.forma_pagamento} onChange={(e) => setValue("forma_pagamento", e.target.value as ValoresLocacao["forma_pagamento"])} opcoes={formas.map((f) => ({ valor: f.valor, rotulo: f.rotulo }))} />
                <TextField
                  cheio
                  mono
                  rotulo="Primeiro vencimento"
                  type="date"
                  value={primeiroVencimento}
                  onChange={(e) => setValue("primeiro_vencimento", e.target.value)}
                  dica={primeiroVencimento ? dataCompleta(primeiroVencimento) : undefined}
                />
                <TextField cheio rotulo="Caução" value={sim ? dinheiro(sim.caucao_centavos) : "—"} readOnly dica={plano?.caucao_parcelada && plano.caucao_parcelas > 1 ? textoDaCaucaoParcelada(plano.caucao_parcelada) : "Devolvida no encerramento sem pendências"} />
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
          )}

          {!compra && (
          <Panel titulo="Adicionais">
            {extras.isPending && <p className="text-body text-ink-muted">Carregando os adicionais…</p>}
            {extras.isError && <p role="alert" className="text-body">{mensagemDoErro(extras.error)}</p>}
            <div className="flex flex-col">
              {extras.data?.resultados.map((x) => (
                <label key={x.id} className="flex min-h-[44px] items-center gap-3 border-b border-line py-2 text-body last:border-b-0">
                  <input type="checkbox" className="wl-marcar" checked={v.extras.includes(x.id)} onChange={() => alternarExtra(x.id)} />
                  <span className="flex-1">{x.nome}</span>
                  <span className="text-ink-muted">
                    {dinheiro(x.valor_centavos)} / {x.cobranca === "unica" ? "único" : un.por}
                  </span>
                </label>
              ))}
            </div>
          </Panel>
          )}
        </div>

        <aside className="flex min-w-0 flex-col gap-6 md:sticky md:top-6">
          <Panel titulo="Resumo">
            {(avisoDeFilial ?? erroSemCampo) && <p role="alert" className="text-body">{avisoDeFilial ?? erroSemCampo}</p>}
            {!sim && !simulacao.isError && !avisoDeFilial && <p className="text-body text-ink-muted">{corpo ? "Calculando…" : v.cliente_id && v.veiculo_id && !compra ? "Escolha o plano para ver os valores." : "Escolha o cliente e o veículo para ver os valores."}</p>}
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
                      <div className="text-caption text-ink-muted">{compra ? "Próximas parcelas" : `Próximas ${un.plural}`}</div>
                      <div className="text-body font-semibold">{dinheiro(sim.proximos_periodos_centavos)}</div>
                    </div>
                  )}
                  <div className={`rounded-md bg-solid px-4 py-3 text-on-solid ${periodicidade === "diaria" ? "col-span-2" : ""}`}>
                    <div className="text-caption opacity-80">Hoje, na retirada</div>
                    <div className="text-body font-semibold">{dinheiro(sim.hoje_na_retirada_centavos)}</div>
                  </div>
                </div>
                <p className="mt-3 text-caption text-ink-muted">
                  {sim.texto_retirada}
                  {compra && " Ao quitar a última parcela, o veículo passa ao cliente sem valor extra."}
                </p>
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

          {salvar.isError && (
            <section className="wl-panel">
              <p role="alert" className="text-body text-critical">
                {mensagemDoErro(salvar.error)}{" "}
                {linkDoErro && (
                  <Link href={linkDoErro} className="underline">
                    {semModeloDeCompra ? "Publicar o modelo de contrato" : "Abrir os modelos de contrato"}
                  </Link>
                )}
              </p>
            </section>
          )}
        </aside>
      </div>

      <BarraDeAcoes
        aEsquerda={
          <Button variante="quieto" disabled={!pronto} onClick={() => enviar("reserva")}>
            Salvar como reserva
          </Button>
        }
        cancelar={{ href: "/locacoes" }}
        principal={{ rotulo: "Continuar para vistoria", disabled: !pronto, ocupado: salvar.isPending, aoClicar: () => enviar("vistoria") }}
      />

      {escolhendo === "cliente" && <EscolherCliente aoFechar={() => setEscolhendo(null)} aoEscolher={(c) => escolherCliente(c.id)} />}
      {escolhendo === "veiculo" && <EscolherVeiculo aoFechar={() => setEscolhendo(null)} aoEscolher={(x) => escolherVeiculo(x.id)} />}
    </div>
  );
}

