"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Icone, Panel, SegmentedControl } from "@/design-system";
import { TelaDeErro } from "@/components/locacoes/Comuns";
import { vistorias, type Combustivel, type DevolucaoCompleta } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, dataHoraCurta, placa } from "@/lib/formatos";
import { linkDaPendencia, pendenciasDoErro, rotuloDaPosicao, textoDaPendencia, textoDoNivelNaSaida } from "@/lib/vistorias";
import { AvisosDoAcerto, EtapaDoAcerto, ResumoDoAcerto } from "./AcertoDaDevolucao";
import { GradeDeFotos } from "./Campos";
import { PainelDeItens, PainelDeKmECombustivel } from "./PartesDaVistoria";
import { useVistoriaEmEdicao } from "./useVistoriaEmEdicao";

// Referência: docs/telas/html/Devolucao-Desktop.dc.html e Devolucao-Mobile.dc.html (1 · Vistoria, 2 · Acerto, 3 · Recibo).
// O acerto, o saldo, o texto e o botão vêm da API (DEV-01 a DEV-07); a tela não calcula nada.

type Etapa = "vistoria" | "acerto" | "recibo";

function ComparacaoDeFotos({ d, edicao }: { d: DevolucaoCompleta; edicao: ReturnType<typeof useVistoriaEmEdicao> }) {
  const [tirando, setTirando] = useState(false);
  const v = edicao.vistoria ?? d.vistoria;
  const concluida = v.status === "concluida";
  // Sem chegada ainda (troca cancelada com a chegada descartada, LOC-09), não há comparação.
  const comparacao = d.comparacao;
  if (comparacao === null) return null;
  return (
    <Panel
      titulo="Fotos · saída × agora"
      acao={
        !concluida && (
          <Button compacto icone={<Icone de={Camera} />} onClick={() => setTirando((x) => !x)}>
            Tirar mais fotos
          </Button>
        )
      }
    >
      <div className="flex flex-col gap-4">
        {comparacao.fotos.length === 0 && <p className="text-body text-ink-muted">Nenhuma foto de chegada ainda. Tire as fotos para comparar com a saída.</p>}
        <div className="grid grid-cols-2 gap-3">
          {comparacao.fotos.map((f) => (
            <FotoPar key={f.posicao} f={f} />
          ))}
        </div>
        {tirando && !concluida && (
          <div>
            <p className="mb-3 text-caption text-ink-muted">{`${v.fotos_obrigatorias.feitas} de ${v.fotos_obrigatorias.total} fotos obrigatórias feitas na chegada.`}</p>
            <GradeDeFotos fotos={v.fotos} enviando={edicao.fotoEnviando} aoEnviar={(posicao, arquivo) => edicao.foto.mutate({ posicao, arquivo })} />
          </div>
        )}
      </div>
    </Panel>
  );
}

function FotoPar({ f }: { f: NonNullable<DevolucaoCompleta["comparacao"]>["fotos"][number] }) {
  const rotulo = rotuloDaPosicao(f.posicao);
  return (
    <>
      <figure className="m-0 overflow-hidden rounded-md bg-surface-sunken">
        {f.saida ? (
          // eslint-disable-next-line @next/next/no-img-element -- URL assinada de 15 minutos da API, sem otimização do Next
          <img src={f.saida.url} alt={`Saída · ${rotulo}`} className="h-[110px] w-full object-cover" />
        ) : (
          <div className="grid h-[110px] place-items-center text-caption text-ink-muted">Sem foto</div>
        )}
        <figcaption className="px-3 py-2 text-caption">
          <b>Saída{f.saida ? ` · ${dataCurta(f.saida.tirada_em)}` : ""}</b>
          <br />
          {rotulo}
        </figcaption>
      </figure>
      <figure className="m-0 overflow-hidden rounded-md bg-surface-sunken">
        {f.agora ? (
          // eslint-disable-next-line @next/next/no-img-element -- URL assinada de 15 minutos da API, sem otimização do Next
          <img src={f.agora.url} alt={`Agora · ${rotulo}`} className="h-[110px] w-full object-cover" />
        ) : (
          <div className="grid h-[110px] place-items-center text-caption text-ink-muted">Tire a foto</div>
        )}
        <figcaption className="px-3 py-2 text-caption">
          <b>Agora</b>
          <br />
          {rotulo}
        </figcaption>
      </figure>
    </>
  );
}

function EtapaDoRecibo({ d, aoMudar }: { d: DevolucaoCompleta; aoMudar: () => void }) {
  const cache = useQueryClient();
  const baixar = useMutation({ mutationFn: () => vistorias.recibo(d.id), onSuccess: (r) => window.open(r.url, "_blank", "noopener") });
  const reenviar = useMutation({
    mutationFn: () => vistorias.reenviarRecibo(d.id),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["devolucao", d.id] });
      aoMudar();
    },
  });
  const concluida = d.status === "concluida";
  return (
    <Panel titulo="Recibo" subtitulo={concluida ? `Devolução encerrada${d.concluida_em ? ` em ${dataHoraCurta(d.concluida_em)}` : ""}` : "O recibo sai quando a devolução for encerrada"}>
      {concluida ? (
        <div className="flex flex-col gap-4">
          <p className="text-body">
            {d.recibo_enviado_em ? `Recibo enviado por WhatsApp em ${dataHoraCurta(d.recibo_enviado_em)}.` : "O recibo com as fotos é enviado por WhatsApp em instantes."} A locação {d.locacao.codigo} está {d.locacao.status === "cancelada" ? "cancelada" : "encerrada"}.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variante="solido" disabled={baixar.isPending} onClick={() => baixar.mutate()}>
              Baixar recibo (PDF)
            </Button>
            <Button disabled={reenviar.isPending} onClick={() => reenviar.mutate()}>
              {reenviar.isPending ? "Reenviando…" : "Reenviar por WhatsApp"}
            </Button>
            <Link href={`/locacoes/${d.locacao.id}`} className="wl-btn wl-btn--quiet">
              Ver a locação
            </Link>
          </div>
          {(baixar.isError || reenviar.isError) && (
            <p role="alert" className="text-body text-critical">
              {mensagemDoErro(baixar.error ?? reenviar.error)}
            </p>
          )}
        </div>
      ) : (
        <p className="text-body text-ink-muted">Conclua a vistoria e o acerto para encerrar a devolução.</p>
      )}
    </Panel>
  );
}

/** Devolução: vistoria de chegada, acerto e recibo, numa tela com três etapas. */
export function Devolucao({ locacaoId }: { locacaoId: number }) {
  const router = useRouter();
  const cache = useQueryClient();
  const [etapaEscolhida, setEtapa] = useState<Etapa | null>(null);

  const abrir = useQuery({ queryKey: ["devolucao-da-locacao", locacaoId], queryFn: () => vistorias.abrirDevolucao(locacaoId), staleTime: Infinity, refetchOnWindowFocus: false, retry: false });
  const id = abrir.data?.id;
  const consulta = useQuery({ queryKey: ["devolucao", id], queryFn: () => vistorias.obterDevolucao(id ?? 0), enabled: id !== undefined, initialData: abrir.data, retry: false });
  const recarregar = () => cache.invalidateQueries({ queryKey: ["devolucao", id] });
  const d = consulta.data;
  const edicao = useVistoriaEmEdicao(d?.vistoria.id, recarregar);

  const concluirVistoria = useMutation({
    mutationFn: () => vistorias.concluir(d?.vistoria.id ?? 0),
    onSuccess: async (v) => {
      cache.setQueryData(["vistoria", v.id], v);
      await recarregar();
      setEtapa("acerto");
    },
  });
  const encerrar = useMutation({
    mutationFn: () => vistorias.encerrar(id ?? 0),
    onSuccess: async (nova) => {
      cache.setQueryData(["devolucao", nova.id], nova);
      await Promise.all([cache.invalidateQueries({ queryKey: ["locacao", locacaoId] }), cache.invalidateQueries({ queryKey: ["locacoes"] })]);
      setEtapa("recibo");
    },
  });

  if (abrir.isPending) {
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Abrindo a devolução…
      </p>
    );
  }
  if (abrir.isError) return <TelaDeErro erro={abrir.error} voltar={{ href: `/locacoes/${locacaoId}`, rotulo: "Voltar para a locação" }} />;
  if (!d) return null;

  const v = edicao.vistoria ?? d.vistoria;
  const acerto = d.acerto;
  const concluida = d.status === "concluida";
  const etapa: Etapa = etapaEscolhida ?? (concluida ? "recibo" : "vistoria");
  const pendencias = pendenciasDoErro(concluirVistoria.error);
  const falta = textoDaPendencia(v);
  const vistoriaConcluida = v.status === "concluida";

  const opcoes = [
    { valor: "vistoria", rotulo: "1 · Vistoria" },
    ...(acerto ? [{ valor: "acerto", rotulo: "2 · Acerto" }, ...(concluida ? [{ valor: "recibo", rotulo: "3 · Recibo" }] : [])] : []),
  ];
  const curtas = opcoes.map((o) => ({ valor: o.valor, rotulo: o.rotulo.replace(/^\d · /, "") }));

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <nav aria-label="Caminho" className="hidden text-caption text-ink-muted md:block">
            <Link href="/locacoes" className="text-ink-muted">
              Locações
            </Link>{" "}
            / <Link href={`/locacoes/${locacaoId}`} className="text-ink-muted">{d.locacao.codigo}</Link> / <span className="text-ink">Devolução</span>
          </nav>
          <h1 className="text-title md:text-display">Devolução</h1>
          <p className="mt-1 text-body text-ink-muted">
            {d.locacao.cliente} · {d.locacao.veiculo.replace(/ · ([A-Z0-9]{7})$/, (_, p: string) => ` · ${placa(p)}`)} · {d.locacao.no_horario ? "no horário" : "fora do horário"}
          </p>
        </div>
        {acerto && (
          <div className="md:ml-auto">
            <div className="hidden md:block">
              <SegmentedControl rotulo="Etapa" valor={etapa} aoMudar={(x) => setEtapa(x as Etapa)} opcoes={opcoes} />
            </div>
            <div className="md:hidden">
              <SegmentedControl rotulo="Etapa" valor={etapa} aoMudar={(x) => setEtapa(x as Etapa)} opcoes={curtas} />
            </div>
          </div>
        )}
      </header>

      <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex min-w-0 flex-col gap-6">
          {etapa === "vistoria" && (
            <>
              <PainelDeKmECombustivel
                v={v}
                edicao={edicao}
                titulo="Quilometragem e combustível"
                rotuloKm="Km agora"
                rotuloCombustivel={`Combustível agora · ${textoDoNivelNaSaida((d.comparacao?.combustivel.saida ?? null) as Combustivel | null)}`}
                kmNaSaida={d.comparacao?.km.saida}
                dicaDoKm={d.comparacao?.km.texto}
                desativado={vistoriaConcluida}
              />
              <ComparacaoDeFotos d={d} edicao={edicao} />
              <PainelDeItens v={v} edicao={edicao} desativado={vistoriaConcluida} />
            </>
          )}
          {etapa === "acerto" && <EtapaDoAcerto d={d} semNivel={d.vistoria.combustivel == null} aoMudar={() => void recarregar()} />}
          {etapa === "recibo" && <EtapaDoRecibo d={d} aoMudar={() => void recarregar()} />}
        </div>

        <aside className="flex min-w-0 flex-col gap-6 md:sticky md:top-6">
          {acerto && (
            <Panel titulo="Acerto">
              <div className="flex flex-col gap-4">
                <ResumoDoAcerto acerto={acerto} semNivel={d.vistoria.combustivel == null} />
                <AvisosDoAcerto acerto={acerto} />
                {edicao.erro && (
                  <p role="alert" className="text-body text-critical">
                    {edicao.erro}
                  </p>
                )}
                {pendencias.length > 0 && (
                  <ul role="alert" className="flex flex-col gap-2 rounded-md bg-critical-soft px-4 py-3 text-caption text-critical-ink">
                    {pendencias.map((p) => {
                      const link = linkDaPendencia(p, v);
                      return (
                        <li key={`${p.codigo}-${p.mensagem}`}>
                          {p.mensagem}
                          {link && (
                            <>
                              {" "}
                              <Link href={link.href} className="underline">
                                {link.rotulo}
                              </Link>
                            </>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
                {concluida ? (
                  <Link href={`/locacoes/${locacaoId}`} className="wl-btn wl-btn--solid">
                    Ver a locação
                  </Link>
                ) : !vistoriaConcluida ? (
                  <>
                    <Button variante="solido" disabled={!v.pode_concluir || concluirVistoria.isPending || edicao.editar.isPending} onClick={() => concluirVistoria.mutate()}>
                      {concluirVistoria.isPending ? "Concluindo…" : "Concluir vistoria"}
                    </Button>
                    {falta && <div className="text-center text-caption text-ink-muted">{falta}</div>}
                    <Button onClick={() => router.push(`/locacoes/${locacaoId}`)}>Salvar e continuar depois</Button>
                  </>
                ) : (
                  <>
                    <Button variante="solido" disabled={encerrar.isPending || (acerto.resultado.tipo === "devolver" && !acerto.forma_devolucao && etapa !== "acerto")} onClick={() => (acerto.resultado.tipo === "devolver" && !acerto.forma_devolucao ? setEtapa("acerto") : encerrar.mutate())}>
                      {encerrar.isPending ? "Encerrando…" : acerto.resultado.botao}
                    </Button>
                    {acerto.resultado.tipo === "devolver" && !acerto.forma_devolucao && <div className="text-center text-caption text-ink-muted">Escolha a forma de devolução na etapa Acerto.</div>}
                    <Button onClick={() => router.push(`/locacoes/${locacaoId}`)}>Salvar e continuar depois</Button>
                  </>
                )}
                {encerrar.isError && (
                  <p role="alert" className="text-body text-critical">
                    {mensagemDoErro(encerrar.error)}
                  </p>
                )}
                {concluirVistoria.isError && pendencias.length === 0 && (
                  <p role="alert" className="text-body text-critical">
                    {mensagemDoErro(concluirVistoria.error)}
                  </p>
                )}
              </div>
            </Panel>
          )}
          {!acerto && (
            <Panel>
              <div className="flex flex-col gap-3">
                {vistoriaConcluida ? (
                  <Link href="/vistorias" className="wl-btn wl-btn--solid">
                    Voltar para as vistorias
                  </Link>
                ) : (
                  <>
                    <Button variante="solido" disabled={!v.pode_concluir || concluirVistoria.isPending} onClick={() => concluirVistoria.mutate()}>
                      {concluirVistoria.isPending ? "Concluindo…" : "Concluir vistoria"}
                    </Button>
                    {falta && <div className="text-center text-caption text-ink-muted">{falta}</div>}
                  </>
                )}
                {concluirVistoria.isError && <p role="alert" className="text-body text-critical">{mensagemDoErro(concluirVistoria.error)}</p>}
              </div>
            </Panel>
          )}
          <p className="text-caption text-ink-muted">O cliente recebe o recibo com as fotos por WhatsApp. O veículo volta para “Disponível” ou vai para a oficina se você marcar avaria.</p>
        </aside>
      </div>
    </div>
  );
}
