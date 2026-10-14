"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bike, Car, Check } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, Icone, Panel, StatusBadge } from "@/design-system";
import { TelaDeErro } from "@/components/locacoes/Comuns";
import { vistorias, type Vistoria } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { celular, dataCurta, dinheiro, placa } from "@/lib/formatos";
import { ROTULO_PERIODICIDADE } from "@/lib/clientes";
import { linkDaPendencia, pendenciasDoErro, textoDaPendencia } from "@/lib/vistorias";
import { PainelDeFotos, PainelDeItens, PainelDeKmECombustivel } from "./PartesDaVistoria";
import { useVistoriaEmEdicao } from "./useVistoriaEmEdicao";

// Referência: docs/telas/html/Vistoria-Desktop.dc.html e Vistoria-Mobile.dc.html (etapa 2 · Vistoria, check-out).
// A lista de itens, as pendências e a hora das fotos vêm da API; a tela só mostra e envia.

function Etapas() {
  return (
    <ol className="flex flex-wrap gap-2" aria-label="Etapas">
      <li className="wl-badge wl-badge--surface">
        <Icone de={Check} />1 · Dados
      </li>
      <li aria-current="step" className="wl-badge wl-badge--solid">
        2 · Vistoria
      </li>
      <li className="wl-badge wl-badge--surface">3 · Assinatura</li>
    </ol>
  );
}

function Linha({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

function ResumoDaLocacao({ v }: { v: Vistoria }) {
  const r = v.resumo_locacao;
  const carro = /kwid|mobi|argo|onix|hb20|uno|gol|polo|sandero/i.test(v.veiculo.modelo);
  return (
    <section className="wl-panel">
      <div className="mb-3 flex items-center gap-3">
        <span aria-hidden="true" className="grid h-[52px] w-[52px] shrink-0 place-items-center rounded-md bg-surface-sunken text-ink-muted">
          <Icone de={carro ? Car : Bike} />
        </span>
        <div>
          <div className="text-body font-medium">{v.veiculo.modelo}</div>
          <div className="wl-mono text-caption text-ink-muted">
            {placa(v.veiculo.placa)}
            {v.veiculo.ano ? ` · ${v.veiculo.ano}` : ""}
          </div>
        </div>
      </div>
      <dl>
        <Linha rotulo="Cliente">{v.cliente.nome}</Linha>
        <Linha rotulo="Celular">{celular(v.cliente.celular)}</Linha>
        {v.cliente.cnh && (
          <Linha rotulo="CNH">
            <StatusBadge tom="sucesso" compacto>
              {v.cliente.cnh}
            </StatusBadge>
          </Linha>
        )}
        {v.cliente.retirada_liberada !== null && (
          <Linha rotulo="Retirada">
            <StatusBadge tom={v.cliente.retirada_liberada ? "sucesso" : "alerta"} compacto>
              {v.cliente.retirada_liberada ? "Liberada" : "Não liberada"}
            </StatusBadge>
          </Linha>
        )}
        <Linha rotulo="Período">
          {dataCurta(r.inicio)} a {dataCurta(r.fim_previsto)} · {ROTULO_PERIODICIDADE[r.periodicidade as keyof typeof ROTULO_PERIODICIDADE]?.toLowerCase() ?? r.periodicidade}
        </Linha>
        {r.diaria_centavos !== undefined && <Linha rotulo="Diária">{dinheiro(r.diaria_centavos)}</Linha>}
        <Linha rotulo="Franquia">{r.km_livre ? "Km livre" : "Km limitado"}</Linha>
        {r.caucao_centavos !== undefined && (
          <Linha rotulo="Caução">
            <StatusBadge tom={r.caucao_paga ? "sucesso" : "alerta"} compacto>
              {dinheiro(r.caucao_centavos)} {r.caucao_paga ? "pago" : "a receber"}
            </StatusBadge>
          </Linha>
        )}
      </dl>
    </section>
  );
}

/** Vistoria de saída (check-out): painel, fotos e itens, com o resumo da locação ao lado. */
export function VistoriaDeSaida({ locacaoId }: { locacaoId: number }) {
  const router = useRouter();
  const cache = useQueryClient();
  const inicio = useQuery({ queryKey: ["vistoria-saida", locacaoId], queryFn: () => vistorias.iniciarSaida(locacaoId), staleTime: Infinity, refetchOnWindowFocus: false, retry: false });
  const edicao = useVistoriaEmEdicao(inicio.data?.id);
  const v = edicao.vistoria ?? inicio.data;

  const concluir = useMutation({
    mutationFn: () => vistorias.concluir(v?.id ?? 0),
    onSuccess: async (nova) => {
      cache.setQueryData(["vistoria", nova.id], nova);
      await Promise.all([cache.invalidateQueries({ queryKey: ["locacao", locacaoId] }), cache.invalidateQueries({ queryKey: ["locacoes"] })]);
      router.push(`/locacoes/${locacaoId}`);
    },
  });

  if (inicio.isPending) {
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Abrindo a vistoria…
      </p>
    );
  }
  if (inicio.isError) return <TelaDeErro erro={inicio.error} voltar={{ href: `/locacoes/${locacaoId}`, rotulo: "Voltar para a locação" }} />;
  if (!v) return null;

  const falta = v.pendencias[0] === "km" && edicao.avisoDoKm ? edicao.avisoDoKm.mensagem : textoDaPendencia(v);
  const pendencias = pendenciasDoErro(concluir.error);
  const concluida = v.status === "concluida";

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <nav aria-label="Caminho" className="text-caption text-ink-muted">
            <Link href="/locacoes" className="text-ink-muted">
              Locações
            </Link>{" "}
            / <Link href={`/locacoes/${locacaoId}`} className="wl-mono text-ink-muted">{v.locacao.codigo}</Link>
          </nav>
          <h1 className="text-title md:text-display">Check-out da {v.veiculo.modelo}</h1>
        </div>
        <div className="md:ml-auto">
          <Etapas />
        </div>
      </header>

      <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex min-w-0 flex-col gap-6">
          <div className="md:hidden">
            <ResumoDaLocacao v={v} />
          </div>
          <PainelDeKmECombustivel v={v} edicao={edicao} titulo="Painel" rotuloKm="Quilometragem na saída" rotuloCombustivel="Combustível" desativado={concluida} />
          <PainelDeFotos v={v} edicao={edicao} desativado={concluida} />
          <PainelDeItens v={v} edicao={edicao} desativado={concluida} />
        </div>

        <aside className="flex min-w-0 flex-col gap-6 md:sticky md:top-6">
          <div className="hidden md:block">
            <ResumoDaLocacao v={v} />
          </div>
          <Panel>
            <div className="flex flex-col gap-3">
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
                  Voltar para a locação
                </Link>
              ) : (
                <>
                  <Button variante="solido" disabled={!v.pode_concluir || concluir.isPending || edicao.editar.isPending} onClick={() => concluir.mutate()}>
                    {concluir.isPending ? "Concluindo…" : "Continuar para assinatura"}
                  </Button>
                  {falta && <div className="text-center text-caption text-ink-muted">{falta}</div>}
                  <Button variante="quieto" disabled={edicao.editar.isPending} onClick={() => router.push(`/locacoes/${locacaoId}`)}>
                    Salvar e continuar depois
                  </Button>
                  {concluir.isError && pendencias.length === 0 && (
                    <p role="alert" className="text-body text-critical">
                      {mensagemDoErro(concluir.error)}
                    </p>
                  )}
                </>
              )}
            </div>
          </Panel>
        </aside>
      </div>
    </div>
  );
}
