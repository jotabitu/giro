"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bike, Car, MapPin, Navigation, Plus, X } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Aviso } from "@/components/acesso/Aviso";
import { QuadroDeMovimentacoes } from "@/components/movimentacoes/QuadroDeMovimentacoes";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { Button, Dialogo, Icone, SearchField, SegmentedControl, StatusBadge, TextField } from "@/design-system";
import { ErroApi, filiais, movimentacoes, veiculos, type Veiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { km, placa } from "@/lib/formatos";
import { campoDoFormulario, esquemaMovimentacao, novaParada, paraCorpoMovimentacao, VALORES_INICIAIS_MOVIMENTACAO, type ValoresMovimentacao } from "@/lib/movimentacao-form";
import { ROTA_DAS_MOVIMENTACOES, ROTULO_DO_TIPO_DE_LOCAL, TIPOS_DE_LOCAL } from "@/lib/movimentacoes";
import { tomDoStatus } from "@/lib/tom";

// Referência: docs/telas/html/Movimentacao-Nova-Desktop.dc.html (gaveta sobre o quadro) e Movimentacao-Nova-Mobile.dc.html (tela inteira).
// MOV-01 a MOV-06. No MVP a parada não tem ordem de serviço (MOV-04, CA-246-07): a parada tem serviço e valor previsto.

const PIN = "absolute -left-[34px] top-4 grid size-[28px] place-items-center rounded-pill text-[12px] font-bold";

function Secao({ children }: { children: string }) {
  return <h2 className="m-0 mt-1 text-[15px] font-semibold">{children}</h2>;
}

function CartaoDoVeiculo({ v }: { v: Veiculo }) {
  return (
    <div className="flex items-center gap-3 rounded-[18px] bg-surface-sunken px-[14px] py-3">
      <span className="grid size-[44px] shrink-0 place-items-center rounded-[12px] bg-surface text-ink-muted">
        <Icone de={v.tipo_veiculo === "moto" ? Bike : Car} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="font-semibold">
          {v.marca} {v.modelo} · <span className="wl-mono font-medium">{placa(v.placa)}</span>
        </div>
        <div className="text-caption text-ink-muted">
          {v.filial.nome} · {km(v.km_atual)}
        </div>
      </div>
      <StatusBadge compacto tom={tomDoStatus(v.situacao.tom)}>
        {v.situacao.rotulo}
      </StatusBadge>
    </div>
  );
}

/** Escolha do veículo: busca por placa ou modelo; a API diz depois se ele pode ser movimentado (MOV-03). */
function EscolhaDoVeiculo({ escolhido, aoEscolher, erro }: { escolhido: Veiculo | null; aoEscolher: (v: Veiculo | null) => void; erro?: string }) {
  const [busca, setBusca] = useState("");
  const resultados = useQuery({ queryKey: ["veiculos", "busca-movimentacao", busca], queryFn: () => veiculos.listar({ busca: busca.trim() }), enabled: busca.trim().length >= 2 && !escolhido });
  if (escolhido) {
    return (
      <div className="flex flex-col gap-2">
        <CartaoDoVeiculo v={escolhido} />
        <Button compacto variante="quieto" onClick={() => aoEscolher(null)}>
          Trocar o veículo
        </Button>
      </div>
    );
  }
  const lista = resultados.data?.resultados ?? [];
  return (
    <div className="flex flex-col gap-2">
      <SearchField placeholder="Placa ou modelo" atalho={false} cheio value={busca} onChange={(e) => setBusca(e.target.value)} />
      {erro && <span className="text-caption text-critical-ink">{erro}</span>}
      {busca.trim().length >= 2 && resultados.isSuccess && lista.length === 0 && <p className="m-0 text-caption text-ink-muted">Nenhum veículo encontrado.</p>}
      {lista.slice(0, 5).map((v) => (
        <button key={v.id} type="button" onClick={() => aoEscolher(v)} className="min-h-[44px] text-left">
          <CartaoDoVeiculo v={v} />
        </button>
      ))}
    </div>
  );
}

function NovoLocal({ aberto, aoFechar, aoCriar }: { aberto: boolean; aoFechar: () => void; aoCriar: (id: number) => void }) {
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState("lava_jato");
  const criar = useMutation({
    mutationFn: () => movimentacoes.criarLocal({ nome: nome.trim(), tipo: tipo as (typeof TIPOS_DE_LOCAL)[number]["valor"] }),
    onSuccess: (local) => {
      setNome("");
      aoCriar(local.id);
    },
  });
  return (
    <Dialogo
      aberto={aberto}
      aoFechar={aoFechar}
      titulo="Novo local de apoio"
      descricao="O local vale para todas as filiais. O nome não pode repetir."
      fecharAoClicarFora={false}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={criar.isPending || nome.trim() === ""} onClick={() => criar.mutate()}>
            Salvar local
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <TextField rotulo="Nome" cheio value={nome} onChange={(e) => setNome(e.target.value)} />
        <CampoSelecao rotulo="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} opcoes={TIPOS_DE_LOCAL.map((t) => ({ valor: t.valor, rotulo: t.rotulo }))} />
        {criar.isError && <Aviso tipo="erro">{mensagemDoErro(criar.error)}</Aviso>}
      </div>
    </Dialogo>
  );
}

/** Nova movimentação. No desktop é a gaveta de 520px sobre o quadro; no celular, a tela inteira com o botão fixo embaixo. */
export function NovaMovimentacao() {
  const router = useRouter();
  const cliente = useQueryClient();
  const params = useSearchParams();
  const [veiculo, setVeiculo] = useState<Veiculo | null>(null);
  const [novoLocalPara, setNovoLocalPara] = useState<number | null>(null);
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    control,
    formState: { errors },
  } = useForm<ValoresMovimentacao>({ resolver: zodResolver(esquemaMovimentacao), defaultValues: VALORES_INICIAIS_MOVIMENTACAO });
  const paradas = useFieldArray({ control, name: "paradas" });
  const v = watch();

  // "Movimentar" e "Transferir" da ficha chegam com ?veiculo= e, na transferência, &destino=.
  const veiculoDaUrl = Number(params.get("veiculo")) || null;
  const destinoDaUrl = params.get("destino");
  const daUrl = useQuery({ queryKey: ["veiculos", "detalhe", veiculoDaUrl], queryFn: () => veiculos.obter(veiculoDaUrl ?? 0), enabled: veiculoDaUrl !== null });
  useEffect(() => {
    if (daUrl.data && !veiculo) {
      setVeiculo(daUrl.data);
      setValue("veiculo_id", String(daUrl.data.id));
      if (destinoDaUrl) setValue("destino_filial_id", destinoDaUrl);
    }
  }, [daUrl.data, veiculo, destinoDaUrl, setValue]);

  const filialDeSaida = veiculo?.filial.id;
  const locais = useQuery({ queryKey: ["movimentacoes", "locais"], queryFn: () => movimentacoes.locais() });
  const minhas = useQuery({ queryKey: ["filiais-minhas"], queryFn: () => filiais.minhas(), staleTime: 5 * 60_000 });
  const quemLeva = useQuery({ queryKey: ["movimentacoes", "levam", filialDeSaida], queryFn: async () => (await movimentacoes.pessoas(filialDeSaida ?? 0)).resultados, enabled: filialDeSaida !== undefined });
  const transferencia = veiculo !== null && v.destino_filial_id !== "" && Number(v.destino_filial_id) !== filialDeSaida;
  const categoriasDoDestino = useQuery({
    queryKey: ["categorias", { filial: v.destino_filial_id, tipo: veiculo?.tipo_veiculo }],
    queryFn: () => veiculos.categorias({ filial: Number(v.destino_filial_id), tipo_veiculo: veiculo?.tipo_veiculo }),
    enabled: transferencia,
  });

  const criar = useMutation({ mutationFn: (valores: ValoresMovimentacao) => movimentacoes.criar(paraCorpoMovimentacao(valores)) });

  async function enviar(valores: ValoresMovimentacao) {
    setErroGeral(null);
    try {
      await criar.mutateAsync(valores);
      await cliente.invalidateQueries({ queryKey: ["movimentacoes"] });
      router.push(ROTA_DAS_MOVIMENTACOES);
    } catch (e) {
      if (e instanceof ErroApi && e.campos) {
        const sobra: string[] = [];
        for (const [campo, mensagem] of Object.entries(e.campos)) {
          const nome = campoDoFormulario(campo);
          if (nome) setError(nome as keyof ValoresMovimentacao, { message: mensagem });
          else sobra.push(mensagem);
        }
        if (sobra.length) setErroGeral(sobra.join(". "));
      } else {
        setErroGeral(mensagemDoErro(e));
      }
    }
  }

  const fechar = () => router.push(ROTA_DAS_MOVIMENTACOES);
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && !document.querySelector("dialog[open]") && router.push(ROTA_DAS_MOVIMENTACOES);
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [router]);

  const agendar = v.quando === "agendar";
  const erro = (nome: string) => (nome.split(".").reduce<unknown>((acc, parte) => (acc as Record<string, unknown> | undefined)?.[parte], errors) as { message?: string } | undefined)?.message;
  const opcoesDeLocal = (locais.data?.resultados ?? []).map((l) => ({ valor: String(l.id), rotulo: `${l.nome} · ${ROTULO_DO_TIPO_DE_LOCAL[l.tipo]}` }));

  return (
    <>
      <div inert className="max-md:hidden">
        <QuadroDeMovimentacoes />
      </div>
      <div className="md:fixed md:inset-0 md:z-40">
        <div aria-hidden="true" onClick={fechar} className="max-md:hidden md:absolute md:inset-0 md:bg-solid/40" />
        <form
          aria-label="Nova movimentação"
          noValidate
          onSubmit={handleSubmit(enviar)}
          className="flex min-h-[calc(100dvh-120px)] flex-col md:absolute md:top-4 md:right-4 md:bottom-4 md:min-h-0 md:w-[520px] md:overflow-hidden md:rounded-xl md:bg-surface md:shadow-pop"
        >
          <header className="flex items-center gap-3 md:px-6 md:pt-6 md:pb-3">
            <Link href={ROTA_DAS_MOVIMENTACOES} aria-label="Fechar" className="wl-icon-btn wl-icon-btn--sm size-[44px] md:order-last">
              <Icone de={X} />
            </Link>
            <h1 className="m-0 flex-1 text-title md:text-[24px] md:font-semibold">Nova movimentação</h1>
          </header>

          <div className="flex flex-1 flex-col gap-[14px] pt-3 md:overflow-y-auto md:px-6 md:pb-4">
            <Secao>1 · Veículo</Secao>
            <EscolhaDoVeiculo
              escolhido={veiculo}
              aoEscolher={(x) => {
                setVeiculo(x);
                setValue("veiculo_id", x ? String(x.id) : "", { shouldValidate: x !== null });
                setValue("levado_por_id", "");
              }}
              erro={erro("veiculo_id")}
            />

            <Secao>2 · Para onde vai</Secao>
            <div className="relative flex flex-col gap-2 pl-[34px] before:absolute before:top-6 before:bottom-6 before:left-[13px] before:w-[2px] before:bg-line before:content-['']">
              <div className="relative flex flex-col gap-[10px] rounded-[18px] bg-surface-sunken px-[14px] py-3">
                <span className={`${PIN} bg-solid text-on-solid`}>A</span>
                <div className="font-medium">
                  Saída · {veiculo?.filial.nome ?? "filial do veículo"} <small className="text-caption font-normal text-ink-muted">onde o veículo está</small>
                </div>
              </div>

              {paradas.fields.map((campo, i) => (
                <div key={campo.id} className="relative flex flex-col gap-[10px] rounded-[18px] bg-surface-sunken px-[14px] py-3">
                  <span className={`${PIN} bg-surface text-ink shadow-[inset_0_0_0_2px_var(--ink)]`}>{i + 1}</span>
                  <div className="flex items-center gap-2 font-medium">
                    <Icone de={MapPin} />
                    Parada
                    <Button compacto variante="quieto" aria-label={`Remover a parada ${i + 1}`} onClick={() => paradas.remove(i)}>
                      Remover
                    </Button>
                  </div>
                  <CampoSelecao rotulo="Local de apoio" vazio="Escolha o local" opcoes={opcoesDeLocal} erro={erro(`paradas.${i}.local_id`)} {...register(`paradas.${i}.local_id`)} />
                  <button type="button" onClick={() => setNovoLocalPara(i)} className="min-h-[44px] self-start text-left text-caption underline">
                    Novo local
                  </button>
                  <div className="grid gap-3 md:grid-cols-2">
                    <TextField rotulo="Serviço" cheio erro={erro(`paradas.${i}.servico`)} {...register(`paradas.${i}.servico`)} />
                    <TextField rotulo="Valor previsto" cheio inputMode="decimal" placeholder="35,00" dica="Confira com o recibo na saída." erro={erro(`paradas.${i}.valor_previsto`)} {...register(`paradas.${i}.valor_previsto`)} />
                  </div>
                </div>
              ))}

              <button type="button" onClick={() => paradas.append(novaParada())} className="flex h-[44px] items-center gap-2 rounded-[14px] border-[1.5px] border-dashed border-line bg-transparent px-[14px] text-body text-ink-muted">
                <Icone de={Plus} />
                Adicionar parada
              </button>

              <div className="relative flex flex-col gap-[10px] rounded-[18px] bg-surface-sunken px-[14px] py-3">
                <span className={`${PIN} bg-brand text-on-brand`}>B</span>
                <div className="flex items-center gap-2 font-medium">
                  <Icone de={Navigation} />
                  Destino
                  {veiculo && v.destino_filial_id !== "" && (
                    <span className="ml-auto">
                      <StatusBadge compacto tom="info">
                        {transferencia ? "Transferência" : "Ida e volta"}
                      </StatusBadge>
                    </span>
                  )}
                </div>
                <CampoSelecao rotulo="Filial de destino" vazio="Escolha a filial" opcoes={(minhas.data?.resultados ?? []).map((f) => ({ valor: String(f.id), rotulo: f.nome }))} erro={erro("destino_filial_id")} {...register("destino_filial_id")} />
                {transferencia && (
                  <CampoSelecao
                    rotulo="Categoria do veículo na filial de destino"
                    vazio="Manter a categoria atual"
                    opcoes={(categoriasDoDestino.data ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome }))}
                    erro={erro("categoria_destino_id")}
                    {...register("categoria_destino_id")}
                  />
                )}
                <p className="m-0 text-caption text-ink-muted">O destino é sempre uma filial. Em outra filial, o veículo passa a ser dela na chegada.</p>
              </div>
            </div>

            <Secao>3 · Quando e quem leva</Secao>
            <SegmentedControl
              rotulo="Quando"
              opcoes={[
                { valor: "agora", rotulo: "Sair agora" },
                { valor: "agendar", rotulo: "Agendar" },
              ]}
              valor={v.quando}
              aoMudar={(q) => setValue("quando", q)}
            />
            {agendar && (
              <div className="grid grid-cols-2 gap-3">
                <TextField rotulo="Dia" cheio type="date" erro={erro("dia")} {...register("dia")} />
                <TextField rotulo="Hora" cheio type="time" erro={erro("hora")} {...register("hora")} />
              </div>
            )}
            <CampoSelecao
              rotulo="Quem leva"
              vazio="Escolha quem leva"
              dica={veiculo ? `Usuário da ${veiculo.filial.nome}.` : "Escolha o veículo primeiro."}
              opcoes={(quemLeva.data ?? []).map((p) => ({ valor: String(p.id), rotulo: p.eu ? `${p.nome} (você)` : p.nome }))}
              erro={erro("levado_por_id")}
              {...register("levado_por_id")}
            />
            <label className="flex min-h-[44px] items-center gap-[10px] text-body">
              <input type="checkbox" className="wl-marcar" disabled={transferencia} checked={transferencia || v.vistoria_rapida} {...register("vistoria_rapida")} />
              Vistoria rápida na chegada (km, combustível e 4 fotos). {transferencia ? "Obrigatória na transferência." : "Opcional na volta à mesma filial."}
            </label>
          </div>

          <footer className="flex flex-col gap-[10px] border-t border-line pt-4 md:px-6 md:pb-6">
            {erroGeral && <Aviso tipo="erro">{erroGeral}</Aviso>}
            <p className="m-0 text-body text-ink-muted">Agendada, a movimentação não muda o status do veículo. Ao sair, o veículo disponível passa a Em movimentação.</p>
            <div className="flex justify-end gap-2">
              <Link href={ROTA_DAS_MOVIMENTACOES} className="wl-btn max-md:hidden">
                Cancelar
              </Link>
              <Button type="submit" variante="solido" disabled={criar.isPending} icone={<Icone de={Plus} />}>
                {agendar ? "Agendar movimentação" : "Sair agora"}
              </Button>
            </div>
          </footer>
        </form>
      </div>

      <NovoLocal
        aberto={novoLocalPara !== null}
        aoFechar={() => setNovoLocalPara(null)}
        aoCriar={async (id) => {
          await cliente.invalidateQueries({ queryKey: ["movimentacoes", "locais"] });
          if (novoLocalPara !== null) setValue(`paradas.${novoLocalPara}.local_id`, String(id));
          setNovoLocalPara(null);
        }}
      />
    </>
  );
}
