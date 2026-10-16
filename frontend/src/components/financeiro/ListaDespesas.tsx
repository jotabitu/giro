"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, Paperclip, Plus } from "lucide-react";
import { useState } from "react";
import { Button, CelulaDupla, DataTable, Icone, KpiGrid, KpiTile, ProgressBar, SearchField, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { Paginacao } from "@/components/lista/Paginacao";
import { financeiro, type Despesa, type StatusDaDespesa } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { mesDe, nomeDoMes } from "@/lib/despesas";
import { mensagemDoErro } from "@/lib/erros";
import { origemDaDespesa, rotuloDaCategoria, TOM_DA_DESPESA } from "@/lib/financeiro";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { TODAS } from "@/lib/filial";
import { useFilial } from "@/lib/filial-escolhida";
import { dataCurta, dinheiro } from "@/lib/formatos";
import { dinheiroCurto } from "@/lib/painel";
import { useSessao } from "@/lib/sessao";
import { Confirmacao } from "./Comuns";
import { DetalheDaDespesa } from "./DetalheDaDespesa";
import { NovaDespesa } from "./NovaDespesa";

// Referência: docs/telas/html/Despesas-Desktop.dc.html e Despesas-Mobile.dc.html.
// Estado, texto da situação e indicadores vêm da API (FIN-05, APR-03); a tela não calcula valor nem estado.

type Aba = "todas" | StatusDaDespesa;

function Situacao({ d }: { d: Despesa }) {
  return (
    <StatusBadge tom={TOM_DA_DESPESA[d.status]} compacto>
      {d.rotulo_situacao}
    </StatusBadge>
  );
}

function BotaoNota({ d }: { d: Despesa }) {
  if (!d.nota) return null;
  return (
    <a href={d.nota.url} target="_blank" rel="noreferrer" aria-label={`Ver a nota de ${d.descricao}`} onClick={(e) => e.stopPropagation()} className="wl-btn wl-btn--quiet wl-btn--sm">
      <Icone de={Paperclip} />
    </a>
  );
}

/** "Últimas" no celular: um cartão por despesa, com data, origem, situação e valor. */
function CartaoDaDespesa({ d, origem, aoAbrir }: { d: Despesa; origem: string; aoAbrir: (d: Despesa) => void }) {
  return (
    <button type="button" onClick={() => aoAbrir(d)} className="flex min-h-[44px] items-center gap-3 border-b border-line py-[14px] text-left text-ink last:border-b-0">
      <span className="min-w-0 flex-1">
        <span className="block text-body font-medium">{d.descricao}</span>
        <span className="block text-caption text-ink-muted">
          {dataCurta(d.data)} · {origem}
        </span>
        <span className="mt-1.5 block">
          <Situacao d={d} />
        </span>
      </span>
      <span className="shrink-0 text-body font-semibold">{dinheiro(d.valor_centavos)}</span>
    </button>
  );
}

/** Quanto cada categoria pesa no mês: a largura acompanha o valor que a API devolveu, relativo à maior. */
function PorCategoria({ valores }: { valores: Partial<Record<Despesa["categoria"], number>> }) {
  const itens = Object.entries(valores)
    .filter((e): e is [Despesa["categoria"], number] => typeof e[1] === "number" && e[1] > 0)
    .sort((a, b) => b[1] - a[1]);
  if (itens.length === 0) return null;
  const maior = itens[0]![1];
  return (
    <section className="wl-panel hidden md:block">
      <h2 className="mb-2 text-heading">Por categoria</h2>
      {itens.map(([categoria, centavos]) => (
        <div key={categoria} className="py-2">
          <div className="flex justify-between text-caption">
            <span>{rotuloDaCategoria(categoria)}</span>
            <span className="font-medium">{dinheiro(centavos)}</span>
          </div>
          <div className="mt-1.5">
            <ProgressBar valor={(centavos / maior) * 100} rotulo={rotuloDaCategoria(categoria)} />
          </div>
        </div>
      ))}
    </section>
  );
}

/** Despesas do mês: indicadores, lista com situação, gasto por categoria e o formulário de nova despesa. */
export function ListaDespesas({ abrirId }: { abrirId?: number }) {
  const { eu } = useSessao();
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("aba") ?? "todas") as Aba;
  const cursor = valor("cursor") ?? undefined;
  const buscaNaUrl = valor("busca") ?? "";
  const [busca, setBusca] = useBuscaNaUrl(definir, buscaNaUrl);
  const mes = mesDe(useAgora());
  const [detalhe, setDetalhe] = useState<{ id: number; inicial?: Despesa } | null>(abrirId ? { id: abrirId } : null);
  const [aviso, setAviso] = useState<string | null>(null);

  // Quem só lança manutenção (vistoriador) não vê a lista; as demais telas do financeiro seguem o mesmo corte.
  const veLista = eu.pode.caixa_receber || eu.pode.despesas_aprovar || eu.pode.financeiro_pagar;
  const podeLancar = eu.pode.despesas_lancar !== "nao";

  const consulta = useQuery({
    queryKey: ["despesas", { aba, mes, cursor, busca: buscaNaUrl }],
    queryFn: () => financeiro.listarDespesas({ mes, status: aba === "todas" ? undefined : aba, busca: buscaNaUrl || undefined, cursor }),
    placeholderData: (anterior) => anterior,
    enabled: veLista,
  });
  const d = veLista ? consulta.data : undefined;
  const ind = d?.indicadores;
  const c = d?.contagens;
  const despesas = d?.resultados ?? [];
  const filial = useFilial()?.nome ?? eu.filiais[0]?.nome;
  const nomeDoMesAtual = nomeDoMes(mes);

  // Exportar (FIN-16): quem pode vem da API, não do nome do perfil. O pedido leva o mês e a filial da tela, sem a busca nem a aba.
  const podeExportar = eu.pode.despesas_exportar;
  const escolhida = useFilial()?.escolha ?? null;
  const filialDaExportacao = escolhida === null ? (eu.filiais[0]?.id ?? null) : escolhida === TODAS ? null : Number(escolhida);
  const exportar = useMutation({
    mutationFn: () => financeiro.exportarDespesas({ mes, filial_id: filialDaExportacao }),
    onSuccess: () => setAviso("Exportação pedida. O link para baixar o arquivo chega no seu e-mail."),
  });

  const origem = (x: Despesa) => origemDaDespesa(x, eu.filiais);
  const colunas: ColunaTabela<Despesa>[] = [
    { chave: "data", titulo: "Data", mono: true, celula: (x) => <span className="wl-mono">{dataCurta(x.data)}</span> },
    { chave: "despesa", titulo: "Despesa", celula: (x) => <CelulaDupla principal={x.descricao} secundaria={origem(x)} /> },
    { chave: "valor", titulo: "Valor", celula: (x) => <span className="font-medium whitespace-nowrap">{dinheiro(x.valor_centavos)}</span> },
    { chave: "situacao", titulo: "Situação", celula: (x) => <Situacao d={x} /> },
    { chave: "lancou", titulo: "Lançou", celula: (x) => <span className="wl-cell-sub !text-ink">{x.lancada_por.nome}</span> },
    { chave: "nota", titulo: "", celula: (x) => <BotaoNota d={x} /> },
  ];
  const abas = [
    { valor: "todas", rotulo: "Todas" },
    { valor: "aguardando_aprovacao", rotulo: `Aguardando${c ? ` ${c.aguardando_aprovacao}` : ""}` },
    { valor: "a_pagar", rotulo: `A pagar${c ? ` ${c.a_pagar}` : ""}` },
    { valor: "paga", rotulo: "Pagas" },
  ] as const;

  if (!veLista && !podeLancar)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Seu perfil não tem acesso a Despesas.
      </p>
    );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-x-4 gap-y-3">
        <div className="min-w-0 flex-1 md:flex-none">
          <h1 className="text-title md:text-display">Despesas</h1>
          <p className="mt-1 text-body text-ink-muted">
            {nomeDoMesAtual}
            {filial ? ` · ${filial}` : ""}
          </p>
        </div>
        {podeExportar && (
          <div className="ml-auto hidden md:block">
            <Button onClick={() => exportar.mutate()} disabled={exportar.isPending}>
              <Icone de={Download} />
              {exportar.isPending ? "Pedindo…" : "Exportar"}
            </Button>
          </div>
        )}
        {/* O `.wl-icon-btn` define `display`, e isso vence o `md:hidden` do próprio link: o wrapper é quem some no desktop (a referência do desktop só tem Exportar). */}
        {podeLancar && (
          <div className="ml-auto md:hidden">
            <a href="#nova-despesa" aria-label="Nova despesa" className="wl-icon-btn wl-icon-btn--sm size-11">
              <Icone de={Plus} />
            </a>
          </div>
        )}
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}
      {exportar.isError && (
        <p role="alert" className="text-body text-critical-ink">
          {mensagemDoErro(exportar.error)}
        </p>
      )}

      {ind && (
        <KpiGrid>
          <KpiTile destaque rotulo={`Gasto em ${nomeDoMesAtual.toLowerCase()}`} valor={dinheiroCurto(ind.gasto_mes_centavos)} contexto="até hoje" />
          <KpiTile rotulo="Aguardando aprovação" valor={String(ind.aguardando_aprovacao_quantidade)} contexto={dinheiro(ind.aguardando_aprovacao_centavos)} />
          <div className="hidden md:contents">
            <KpiTile rotulo="A pagar esta semana" valor={dinheiroCurto(ind.a_pagar_semana_centavos)} />
            {/* FIN-16: a API divide; sem veículo ela manda `null` e a tela não mostra valor nem zero. */}
            <KpiTile rotulo="Despesa por veículo" valor={ind.despesa_por_veiculo_centavos == null ? "—" : dinheiro(ind.despesa_por_veiculo_centavos)} contexto="no mês" />
          </div>
        </KpiGrid>
      )}

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <div className="order-2 flex min-w-0 flex-col gap-6 md:order-1 md:flex-[999_1_560px]">
          {veLista && (
            <section className="wl-panel" aria-label="Despesas do mês">
              <div className="mb-5 hidden flex-wrap items-center gap-3 md:flex">
                <SegmentedControl rotulo="Filtro" opcoes={abas} valor={aba} aoMudar={(v) => definir({ aba: v === "todas" ? null : v })} />
                <div className="ml-auto w-[220px] [&_.wl-search]:!w-full">
                  <SearchField placeholder="Buscar despesa" aria-label="Buscar despesa" value={busca} onChange={(e) => setBusca(e.target.value)} />
                </div>
              </div>
              <h2 className="mb-1 text-heading md:hidden">Últimas</h2>

              {consulta.isError && (
                <p role="alert" className="text-body">
                  {mensagemDoErro(consulta.error)}
                </p>
              )}
              {consulta.isPending && (
                <p className="text-body text-ink-muted" aria-busy="true">
                  Carregando as despesas…
                </p>
              )}
              {d && despesas.length === 0 && <p className="py-6 text-center text-body text-ink-muted">{buscaNaUrl ? "Nenhuma despesa com essa busca. Mude o termo." : aba === "todas" ? "Nenhuma despesa neste mês." : "Nenhuma despesa nesta situação."}</p>}
              {d && despesas.length > 0 && (
                <>
                  <div className="hidden overflow-x-auto md:block">
                    <DataTable colunas={colunas} linhas={despesas} chaveDaLinha={(x) => String(x.id)} aoAbrir={(x) => setDetalhe({ id: x.id, inicial: x })} legenda="Despesas do mês" />
                  </div>
                  <div className="flex flex-col md:hidden">
                    {despesas.map((x) => (
                      <CartaoDaDespesa key={x.id} d={x} origem={origem(x)} aoAbrir={(y) => setDetalhe({ id: y.id, inicial: y })} />
                    ))}
                  </div>
                  <Paginacao texto={`Mostrando ${despesas.length}`} anterior={d.anterior} proximo={d.proximo} aoIr={(cur) => definir({ cursor: cur })} />
                </>
              )}
            </section>
          )}
          {ind && <PorCategoria valores={ind.por_categoria} />}
        </div>

        {podeLancar && (
          <aside id="nova-despesa" className="wl-panel order-1 scroll-mt-4 md:order-2 md:flex-[1_1_340px]" aria-label="Nova despesa">
            <h2 className="mb-4 text-heading">Nova despesa</h2>
            <NovaDespesa
              eu={eu}
              aoLancar={(nova) =>
                setAviso(
                  nova.status === "aguardando_aprovacao"
                    ? `Despesa de ${dinheiro(nova.valor_centavos)} enviada ao gerente para aprovar antes de pagar.`
                    : "Despesa lançada.",
                )
              }
            />
          </aside>
        )}
      </div>

      {detalhe && <DetalheDaDespesa id={detalhe.id} inicial={detalhe.inicial} eu={eu} aoFechar={() => setDetalhe(null)} aoConcluir={setAviso} />}
    </div>
  );
}
