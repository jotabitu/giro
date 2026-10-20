"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, Info, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Dialogo, Gaveta, Icone, SegmentedControl, StatusBadge } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { Paginacao } from "@/components/lista/Paginacao";
import { auditoria, type CategoriaDeAuditoria, type EventoDeAuditoria, type PeriodoDaAuditoria } from "@/lib/api";
import { CATEGORIAS_DA_AUDITORIA, filtroDaPessoa, PERIODOS_DA_AUDITORIA, tomDoEvento, valorDaPessoa } from "@/lib/auditoria";
import { mensagemDoErro } from "@/lib/erros";
import { useFiltrosNaUrl } from "@/lib/filtros-url";
import { dataHoraCurta } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { DetalheDoEvento } from "./DetalheDoEvento";

// Referência: docs/telas/html/Admin-Auditoria-Desktop.dc.html e Admin-Auditoria-Mobile.dc.html.
// Quem fez, o resumo e o detalhe são textos prontos da API (AUD-01, AUD-02); a tela não monta frase.

type Aba = "tudo" | CategoriaDeAuditoria;

const ABAS = [{ valor: "tudo", rotulo: "Tudo" }, ...CATEGORIAS_DA_AUDITORIA.map((c) => ({ valor: c.valor, rotulo: c.rotulo }))] as const;
const ABAS_CELULAR = ABAS.filter((a) => ["tudo", "financeiro", "seguranca", "suporte"].includes(a.valor));

function Resumo({ e }: { e: EventoDeAuditoria }) {
  const tom = tomDoEvento(e);
  return tom ? (
    <StatusBadge tom={tom} compacto>
      {e.resumo}
    </StatusBadge>
  ) : (
    <span>{e.resumo}</span>
  );
}

function Quem({ e }: { e: EventoDeAuditoria }) {
  return (
    <span className="flex items-center gap-3">
      <span aria-hidden="true" className="grid size-9 shrink-0 place-items-center rounded-full bg-surface-sunken text-caption font-semibold">
        {e.ator.iniciais}
      </span>
      <span>{e.ator.nome}</span>
    </span>
  );
}

/** Auditoria da empresa: o que cada pessoa fez, filtrado por categoria, pessoa e período. Só leitura; nada se edita nem se apaga. */
export function ListaAuditoria() {
  const { eu } = useSessao();
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("categoria") ?? "tudo") as Aba;
  const periodo = (valor("periodo") ?? "7d") as PeriodoDaAuditoria;
  const pessoa = valor("pessoa");
  const cursor = valor("cursor") ?? undefined;
  const [aberto, setAberto] = useState<number | null>(null);
  const [filtrando, setFiltrando] = useState(false);

  const podeVer = eu.pode.administracao;
  const consulta = useQuery({
    queryKey: ["auditoria", "eventos", { aba, periodo, pessoa, cursor }],
    queryFn: () => auditoria.eventos({ categoria: aba === "tudo" ? undefined : aba, periodo, ...filtroDaPessoa(pessoa), cursor }),
    placeholderData: (anterior) => anterior,
    enabled: podeVer,
  });
  const pessoas = useQuery({ queryKey: ["auditoria", "pessoas", periodo], queryFn: () => auditoria.pessoas(periodo), enabled: podeVer });
  const d = podeVer ? consulta.data : undefined;
  const eventos = d?.resultados ?? [];

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa a Auditoria.
      </p>
    );

  const opcoesDePessoa = (pessoas.data ?? []).map((p) => ({ valor: valorDaPessoa(p), rotulo: p.nome }));
  const mudarAba = (v: string) => definir({ categoria: v === "tudo" ? null : v });
  const filtrado = aba !== "tudo" || pessoa !== null || periodo !== "7d";

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3 md:items-end">
        <Link href="/mais" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Auditoria</h1>
          <p className="mt-1.5 mb-0 hidden text-body text-ink-muted md:block">Tudo que cada pessoa fez no sistema · guardado por 5 anos · ninguém consegue apagar</p>
        </div>
        <button type="button" aria-label="Filtrar" onClick={() => setFiltrando(true)} className="wl-icon-btn wl-icon-btn--sm size-11 md:hidden">
          <Icone de={SlidersHorizontal} />
        </button>
        <Link href="/admin/exportar" className="wl-btn hidden md:inline-flex">
          <Icone de={Download} />
          Exportar
        </Link>
      </header>

      <div className="flex items-start gap-3 rounded-lg bg-surface-sunken px-4 py-3 text-caption text-ink-muted">
        <Icone de={Info} />
        <span>A equipe do Giro só entra na sua conta com um chamado aberto, por tempo limitado, e cada entrada aparece aqui. Você pode bloquear o acesso do suporte nas configurações.</span>
      </div>

      <section className="md:wl-panel flex flex-col gap-4" aria-label="Eventos">
        <div className="hidden flex-wrap items-center gap-3 md:flex">
          <SegmentedControl rotulo="Filtro" opcoes={ABAS} valor={aba} aoMudar={mudarAba} />
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <select aria-label="Pessoa" value={pessoa ?? ""} onChange={(e) => definir({ pessoa: e.target.value })} className="wl-btn wl-btn--sm">
              <option value="">Pessoa: todas</option>
              {opcoesDePessoa.map((o) => (
                <option key={o.valor} value={o.valor}>
                  Pessoa: {o.rotulo}
                </option>
              ))}
            </select>
            <select aria-label="Período" value={periodo} onChange={(e) => definir({ periodo: e.target.value === "7d" ? null : e.target.value })} className="wl-btn wl-btn--sm">
              {PERIODOS_DA_AUDITORIA.map((p) => (
                <option key={p.valor} value={p.valor}>
                  {p.rotulo}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="md:hidden">
          <div role="group" aria-label="Categoria" className="flex gap-2 overflow-x-auto pb-1">
            {ABAS_CELULAR.map((a) => (
              <button
                key={a.valor}
                type="button"
                aria-pressed={a.valor === aba}
                onClick={() => mudarAba(a.valor)}
                className={`inline-flex h-[44px] shrink-0 items-center rounded-pill px-4 text-body whitespace-nowrap ${a.valor === aba ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
              >
                {a.rotulo}
              </button>
            ))}
          </div>
        </div>

        {consulta.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {consulta.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando os eventos…
          </p>
        )}
        {d && eventos.length === 0 && <p className="py-6 text-center text-body text-ink-muted">{filtrado ? "Nenhum evento com esses filtros. Tire um filtro ou aumente o período." : "Nenhum evento no período."}</p>}

        {d && eventos.length > 0 && (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="wl-table" aria-label="Eventos da auditoria">
                <thead>
                  <tr>
                    <th scope="col">Quando</th>
                    <th scope="col">Quem</th>
                    <th scope="col">O que</th>
                    <th scope="col">Detalhe</th>
                  </tr>
                </thead>
                <tbody>
                  {eventos.map((e) => (
                    <tr
                      key={e.id}
                      data-clicavel=""
                      tabIndex={0}
                      onClick={() => setAberto(e.id)}
                      onKeyDown={(k) => {
                        if (k.key === "Enter" || k.key === " ") {
                          k.preventDefault();
                          setAberto(e.id);
                        }
                      }}
                      className={e.tom === "alerta" ? "[&>td]:!bg-warning-soft" : undefined}
                    >
                      <td>
                        <span className="wl-mono whitespace-nowrap">{dataHoraCurta(e.ocorrido_em)}</span>
                      </td>
                      <td>
                        <Quem e={e} />
                      </td>
                      <td>
                        <Resumo e={e} />
                      </td>
                      <td>
                        <span className="wl-cell-sub">{e.detalhe}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="rounded-lg bg-surface px-4 py-2 md:hidden">
              {eventos.map((e) => (
                <button key={e.id} type="button" onClick={() => setAberto(e.id)} className={`flex min-h-[44px] w-full flex-col gap-1 border-b border-line py-[14px] text-left text-ink last:border-b-0 ${e.tom === "alerta" ? "bg-warning-soft px-3" : ""}`}>
                  <span>
                    <Resumo e={e} />
                  </span>
                  <span className="text-caption text-ink-muted">{e.detalhe}</span>
                  <span className="wl-mono text-caption text-ink-muted">
                    {e.ator.nome} · {dataHoraCurta(e.ocorrido_em)}
                  </span>
                </button>
              ))}
            </div>
            <Paginacao texto={`Mostrando ${eventos.length}`} anterior={d.anterior} proximo={d.proximo} aoIr={(cur) => definir({ cursor: cur })} />
          </>
        )}
      </section>

      {aberto !== null && (
        <Dialogo aberto aoFechar={() => setAberto(null)} titulo="Detalhe do evento" acoes={<Button variante="quieto" onClick={() => setAberto(null)}>Fechar</Button>}>
          <DetalheDoEvento id={aberto} />
        </Dialogo>
      )}

      {filtrando && (
        <Gaveta aberto aoFechar={() => setFiltrando(false)} titulo="Filtros" lado="baixo" acoes={<Button variante="solido" onClick={() => setFiltrando(false)}>Ver os eventos</Button>}>
          <div className="flex flex-col gap-4">
            <CampoSelecao rotulo="Categoria" value={aba} onChange={(e) => mudarAba(e.target.value)} opcoes={ABAS.map((a) => ({ valor: a.valor, rotulo: a.rotulo }))} />
            <CampoSelecao rotulo="Pessoa" value={pessoa ?? ""} onChange={(e) => definir({ pessoa: e.target.value })} vazio="Todas" opcoes={opcoesDePessoa} />
            <CampoSelecao rotulo="Período" value={periodo} onChange={(e) => definir({ periodo: e.target.value === "7d" ? null : e.target.value })} opcoes={PERIODOS_DA_AUDITORIA.map((p) => ({ valor: p.valor, rotulo: p.rotulo }))} />
            <Link href="/admin/exportar" className="wl-btn justify-center">
              <Icone de={Download} />
              Exportar a auditoria
            </Link>
          </div>
        </Gaveta>
      )}
    </div>
  );
}
