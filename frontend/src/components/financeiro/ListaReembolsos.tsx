"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button, CelulaDupla, DataTable, KpiGrid, KpiTile, SearchField, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { Paginacao } from "@/components/lista/Paginacao";
import { financeiro, type Reembolso, type StatusDoReembolso } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useFilial } from "@/lib/filial-escolhida";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { dataCurta, dataHoraCurta, dinheiro } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { Confirmacao } from "./Comuns";
import { DialogoMarcarFeito } from "./DialogoMarcarFeito";

// Referência: docs/telas/html/Reembolsos-Desktop.dc.html e Reembolsos-Mobile.dc.html.
// Textos, indicadores, contagens e quem pode marcar como feito vêm da API (DEV-02, T-380); a tela não soma nem decide nada.

type Aba = "todos" | StatusDoReembolso;
type Periodo = "hoje" | "semana" | "mes";

const PERIODOS = [
  { valor: "hoje", rotulo: "Hoje" },
  { valor: "semana", rotulo: "Semana" },
  { valor: "mes", rotulo: "Mês" },
] as const;

const origemDe = (r: Reembolso) => [r.origem.codigo, r.origem.veiculo].filter(Boolean).join(" · ");
/** "A fazer" ou "Feito · 06 out": o rótulo é da API, a data só se formata. */
const situacaoDe = (r: Reembolso) => (r.feito_em ? `${r.status_rotulo} · ${dataCurta(r.feito_em)}` : r.status_rotulo);

function Situacao({ r }: { r: Reembolso }) {
  return (
    <StatusBadge tom={r.status === "a_fazer" ? "alerta" : "sucesso"} compacto>
      {situacaoDe(r)}
    </StatusBadge>
  );
}

function Acoes({ r, aoMarcar }: { r: Reembolso; aoMarcar: (r: Reembolso) => void }) {
  return (
    <span className="flex flex-wrap items-center gap-2">
      {r.acoes.marcar_feito && (
        <Button variante="solido" compacto onClick={() => aoMarcar(r)}>
          Marcar como feito
        </Button>
      )}
      {r.origem.id !== null && (
        <Link href={`/locacoes/${r.origem.id}`} className="wl-btn wl-btn--quiet wl-btn--sm min-h-[44px] md:min-h-0">
          Ver acerto
        </Link>
      )}
      {r.comprovante && (
        <a href={r.comprovante.url} target="_blank" rel="noreferrer" aria-label={`Ver o comprovante de ${r.cliente.nome}`} className="wl-btn wl-btn--quiet wl-btn--sm min-h-[44px] md:min-h-0">
          Comprovante
        </a>
      )}
    </span>
  );
}

function CartaoDoReembolso({ r, aoMarcar }: { r: Reembolso; aoMarcar: (r: Reembolso) => void }) {
  return (
    <article className="flex flex-col gap-2 border-b border-line py-[14px] last:border-b-0">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="m-0 text-body font-medium">{r.cliente.nome}</p>
          <p className="m-0 wl-mono text-caption text-ink-muted">{origemDe(r)}</p>
        </div>
        <span className="shrink-0 text-body font-semibold">{dinheiro(r.valor_centavos)}</span>
      </div>
      <p className="m-0 text-caption text-ink-muted">
        {r.motivo} · {r.forma_rotulo}
      </p>
      <div>
        <Situacao r={r} />
      </div>
      <Acoes r={r} aoMarcar={aoMarcar} />
    </article>
  );
}

/** Reembolsos ao cliente: indicadores, lista por situação e o registro de que a transferência foi feita. */
export function ListaReembolsos() {
  const { eu } = useSessao();
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("aba") ?? "a_fazer") as Aba;
  const periodo = (valor("periodo") ?? "mes") as Periodo;
  const cursor = valor("cursor") ?? undefined;
  const buscaNaUrl = valor("busca") ?? "";
  const [busca, setBusca] = useBuscaNaUrl(definir, buscaNaUrl);
  const [marcando, setMarcando] = useState<Reembolso | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const filial = useFilial()?.nome ?? eu.filiais[0]?.nome;

  const consulta = useQuery({
    queryKey: ["reembolsos", { aba, periodo, cursor, busca: buscaNaUrl }],
    queryFn: () => financeiro.listarReembolsos({ status: aba, periodo, busca: buscaNaUrl || undefined, cursor }),
    placeholderData: (anterior) => anterior,
  });
  const d = consulta.data;
  const c = d?.contagens;
  const reembolsos = d?.resultados ?? [];
  const total = c ? (aba === "a_fazer" ? c.a_fazer : aba === "feito" ? c.feito : c.todos) : reembolsos.length;

  const colunas: ColunaTabela<Reembolso>[] = [
    { chave: "data", titulo: "Data da devolução", mono: true, celula: (x) => <span className="wl-mono">{dataHoraCurta(x.criado_em)}</span> },
    { chave: "cliente", titulo: "Cliente e locação", celula: (x) => <CelulaDupla principal={x.cliente.nome} secundaria={origemDe(x)} /> },
    { chave: "origem", titulo: "Origem do saldo", celula: (x) => <CelulaDupla principal={x.origem_rotulo} secundaria={x.motivo} /> },
    { chave: "forma", titulo: "Forma", celula: (x) => x.forma_rotulo },
    { chave: "valor", titulo: "Valor", celula: (x) => <span className="font-medium whitespace-nowrap">{dinheiro(x.valor_centavos)}</span> },
    { chave: "situacao", titulo: "Situação", celula: (x) => <Situacao r={x} /> },
    { chave: "acoes", titulo: "", celula: (x) => <Acoes r={x} aoMarcar={setMarcando} /> },
  ];
  const abas = [
    { valor: "a_fazer", rotulo: `A fazer${c ? ` ${c.a_fazer}` : ""}` },
    { valor: "feito", rotulo: `Feitos${c ? ` ${c.feito}` : ""}` },
    { valor: "todos", rotulo: `Todos${c ? ` ${c.todos}` : ""}` },
  ] as const;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-title md:text-display">Reembolsos</h1>
          <p className="mt-1 text-body text-ink-muted">
            <span className="hidden md:inline">Devoluções de caução e acertos a transferir ao cliente</span>
            <span className="md:hidden">Devoluções e cauções</span>
            {filial ? ` · ${filial}` : ""}
          </p>
        </div>
        <div className="hidden md:block">
          <SegmentedControl rotulo="Período" opcoes={PERIODOS} valor={periodo} aoMudar={(v) => definir({ periodo: v === "mes" ? null : v })} />
        </div>
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}

      {d && (
        <KpiGrid>
          <KpiTile destaque rotulo="A reembolsar" valor={dinheiro(d.indicadores.a_fazer.valor_centavos)} contexto={d.indicadores.a_fazer.texto} />
          <KpiTile rotulo="Reembolsados no período" valor={dinheiro(d.indicadores.feitos.valor_centavos)} contexto={d.indicadores.feitos.texto} />
        </KpiGrid>
      )}

      <section className="wl-panel" aria-label="Reembolsos">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <SegmentedControl rotulo="Situação" opcoes={abas} valor={aba} aoMudar={(v) => definir({ aba: v === "a_fazer" ? null : v })} />
          <div className="ml-auto w-full md:w-[240px] [&_.wl-search]:!w-full">
            <SearchField placeholder="Buscar cliente ou locação" aria-label="Buscar reembolso" value={busca} onChange={(e) => setBusca(e.target.value)} />
          </div>
        </div>

        {consulta.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {consulta.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando os reembolsos…
          </p>
        )}
        {d && reembolsos.length === 0 && (
          <p className="py-6 text-center text-body text-ink-muted">{buscaNaUrl ? "Nenhum reembolso com essa busca. Mude o termo." : aba === "a_fazer" ? "Nenhum reembolso a fazer." : "Nenhum reembolso nesta situação."}</p>
        )}
        {d && reembolsos.length > 0 && (
          <>
            <div className="hidden overflow-x-auto md:block">
              <DataTable colunas={colunas} linhas={reembolsos} chaveDaLinha={(x) => String(x.id)} legenda="Reembolsos ao cliente" />
            </div>
            <div className="flex flex-col md:hidden">
              {reembolsos.map((x) => (
                <CartaoDoReembolso key={x.id} r={x} aoMarcar={setMarcando} />
              ))}
            </div>
            <Paginacao texto={`Mostrando ${reembolsos.length} de ${total}`} anterior={d.anterior} proximo={d.proximo} aoIr={(cur) => definir({ cursor: cur })} />
          </>
        )}
      </section>

      <p className="text-caption text-ink-muted">Reembolso em dinheiro sai direto pelo caixa aberto e já nasce feito. Pix e estorno no cartão nascem a fazer: faça a transferência pelo banco da locadora e marque como feito, com o comprovante se quiser (DEV-02).</p>

      {marcando && (
        <DialogoMarcarFeito
          reembolso={marcando}
          aoFechar={() => setMarcando(null)}
          aoConcluir={(texto) => {
            setMarcando(null);
            setAviso(texto);
          }}
        />
      )}
    </div>
  );
}
