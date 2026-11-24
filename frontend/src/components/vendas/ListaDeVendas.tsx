"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { CelulaDupla, DataTable, Icone, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { Paginacao } from "@/components/lista/Paginacao";
import { vendas, type FiltroDeVendas, type ListaDeVendas as ListaDeVendasDaApi, type Venda } from "@/lib/api";
import { useAgora, useAmbiente } from "@/lib/ambiente";
import { mensagemDoErro } from "@/lib/erros";
import { useFilial } from "@/lib/filial-escolhida";
import { useFiltrosNaUrl } from "@/lib/filtros-url";
import { dataCompleta, dinheiro, dinheiroSemZeros, placa } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { BotaoDoContrato } from "./AssinaturaDaVenda";
import { codigoEVendedor, comMaiuscula, mesDoDia, mesPorExtenso, tomDaVenda, ultimoContato } from "@/lib/vendas";

// Referência: docs/telas/html/Vendas-Desktop.dc.html e Vendas-Mobile.dc.html (T-503, VEN-08 a VEN-19; T-420, VEN-11).
// Fases 1a e 1b da T-502: propostas abertas (com as abas), transferências pendentes (quitação e balcão) e vendidas do mês,
// com o contrato da venda de balcão. Forma e situação vêm prontas
// (`forma_texto`, `situacao_texto`). Os números do topo (vendido, em negociação, aguardando, funil, conversão e meta),
// "Definir metas" e o total das vendidas vêm do resumo da 1c (`GET /api/vendas/resumo/`) e entram quando ele existir.

type Aba = "todas" | "minhas" | "aguardando" | "perdidas";

const ABAS: { valor: Aba; rotulo: string; curto: string; filtro: FiltroDeVendas }[] = [
  { valor: "todas", rotulo: "Todas", curto: "Todas", filtro: { aba: "abertas" } },
  { valor: "minhas", rotulo: "Minhas", curto: "Minhas", filtro: { aba: "minhas" } },
  { valor: "aguardando", rotulo: "Aguardando gerente", curto: "Gerente", filtro: { aba: "aguardando" } },
  { valor: "perdidas", rotulo: "Perdidas", curto: "Perdidas", filtro: { status: "perdida" } },
];

const abaDaUrl = (v: string | null): Aba => (ABAS.some((a) => a.valor === v) ? (v as Aba) : "todas"); // "propostas" (menu) = todas

function Situacao({ v }: { v: Venda }) {
  return (
    <StatusBadge tom={tomDaVenda(v.status)} compacto>
      {v.situacao_texto}
    </StatusBadge>
  );
}

const situacaoDaTransferencia = (v: Venda) => (v.transferencia.pendente ? "Falta a transferência no Detran" : `Transferência feita em ${v.transferencia.feita_em ? dataCompleta(v.transferencia.feita_em) : "—"}`);

/** A venda da quitação abre pela locação; a de balcão, pela própria tela. Nas propostas e vendidas, o botão é quieto. */
function Abrir({ v, rotulo, quieto }: { v: Venda; rotulo: string; quieto?: boolean }) {
  const classe = `wl-btn wl-btn--sm whitespace-nowrap no-underline${quieto ? " wl-btn--quiet" : ""}`;
  if (v.locacao)
    return (
      <Link href={`/locacoes/${v.locacao.id}`} className={classe}>
        Abrir locação
      </Link>
    );
  return (
    <Link href={`/vendas/${v.id}`} className={classe} aria-label={`${rotulo} ${v.codigo}`}>
      {rotulo}
    </Link>
  );
}

// `comprador_nome`: o cliente, ou o interessado sem cadastro (VEN-14); a API escolhe.
const celulaCliente = (v: Venda) => <CelulaDupla principal={v.comprador_nome} secundaria={<span className="wl-mono">{codigoEVendedor(v)}</span>} />;
const celulaVeiculo = (v: Venda) => <CelulaDupla principal={<span className="font-normal">{v.veiculo.modelo}</span>} secundaria={placa(v.veiculo.placa)} />;
const celulaValor = (v: Venda) => <CelulaDupla principal={<span className="font-semibold">{dinheiro(v.preco_final_centavos)}</span>} secundaria={v.forma_texto || (v.locacao ? v.origem_rotulo : null)} />;

const COLUNAS_PENDENTES: ColunaTabela<Venda>[] = [
  { chave: "cliente", titulo: "Cliente", celula: celulaCliente },
  { chave: "veiculo", titulo: "Veículo", celula: celulaVeiculo },
  { chave: "origem", titulo: "Origem", celula: (v) => v.origem_rotulo },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (v) => (
      <StatusBadge tom="alerta" compacto>
        {situacaoDaTransferencia(v)}
      </StatusBadge>
    ),
  },
  { chave: "abrir", titulo: "", celula: (v) => <Abrir v={v} rotulo="Ver venda" /> },
];

const colunasAbertas = (agora: Date): ColunaTabela<Venda>[] => [
  { chave: "cliente", titulo: "Cliente", celula: celulaCliente },
  { chave: "veiculo", titulo: "Veículo", celula: celulaVeiculo },
  { chave: "valor", titulo: "Valor", celula: celulaValor },
  { chave: "situacao", titulo: "Situação", celula: (v) => <Situacao v={v} /> },
  { chave: "contato", titulo: "Último contato", celula: (v) => <span className="text-ink-muted">{ultimoContato(v.ultimo_contato_em, agora)}</span> },
  { chave: "abrir", titulo: "", celula: (v) => <Abrir v={v} rotulo="Ver proposta" quieto /> },
];

const COLUNAS_VENDIDAS: ColunaTabela<Venda>[] = [
  { chave: "cliente", titulo: "Cliente", celula: celulaCliente },
  { chave: "veiculo", titulo: "Veículo", celula: celulaVeiculo },
  { chave: "valor", titulo: "Valor", celula: celulaValor },
  { chave: "situacao", titulo: "Situação", celula: (v) => <Situacao v={v} /> },
  { chave: "comissao", titulo: "Comissão", celula: (v) => (v.comissao_centavos == null ? "—" : dinheiro(v.comissao_centavos)) },
  {
    chave: "abrir",
    titulo: "",
    // VEN-15: a venda de balcão concluída tem o contrato assinado ("Recibo" virou "Contrato").
    celula: (v) => (
      <span className="flex items-center justify-end gap-1">
        {v.origem === "balcao" && <BotaoDoContrato vendaId={v.id} />}
        <Abrir v={v} rotulo="Ver venda" quieto />
      </span>
    ),
  },
];

/** `transferencia`: no bloco das pendentes, o selo é o da transferência; nas outras listas, a situação da venda. */
function CartaoDaVenda({ v, agora, comissao, transferencia }: { v: Venda; agora: Date; comissao?: boolean; transferencia?: boolean }) {
  const href = v.locacao ? `/locacoes/${v.locacao.id}` : `/vendas/${v.id}`;
  return (
    <Link href={href} className="flex flex-col gap-2 rounded-lg bg-surface-sunken p-4 text-ink no-underline">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1.5">
          <div>
            <div className="text-body font-medium">{v.comprador_nome}</div>
            <div className="text-caption text-ink-muted">
              {v.veiculo.modelo} · <span className="wl-mono">{v.locacao ? `${v.codigo} · ${v.origem_rotulo}` : v.codigo}</span>
            </div>
          </div>
          <div>
            {transferencia && v.transferencia.pendente ? (
              <StatusBadge tom="alerta" compacto>
                {situacaoDaTransferencia(v)}
              </StatusBadge>
            ) : (
              <Situacao v={v} />
            )}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-body font-semibold">{dinheiroSemZeros(v.preco_final_centavos)}</div>
          <div className="text-caption text-ink-muted">{comissao ? (v.comissao_centavos == null ? "" : `comissão ${dinheiro(v.comissao_centavos)}`) : ultimoContato(v.ultimo_contato_em, agora)}</div>
        </div>
      </div>
    </Link>
  );
}

function Lista({ titulo, rotulo, colunas, consulta, vazio, agora, comissao, aoIr, cabeca }: { titulo: string; rotulo: string; colunas: ColunaTabela<Venda>[]; consulta: UseQueryResult<ListaDeVendasDaApi>; vazio: string; agora: Date; comissao?: boolean; aoIr?: (c: string | null) => void; cabeca?: ReactNode }) {
  const d = consulta.data;
  // O número só aparece com a lista inteira na tela (sem próxima página): é a contagem do que está listado, não um total calculado.
  const n = d && !d.proximo && !d.anterior ? d.resultados.length : null;
  return (
    <section className="wl-panel" aria-label={rotulo}>
      <div className="wl-panel__head flex-wrap gap-3">
        <h2 className="wl-panel__title">
          {titulo}
          {n !== null && n > 0 ? ` · ${n}` : ""}
        </h2>
        {cabeca}
      </div>
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando as vendas…
        </p>
      )}
      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {d && d.resultados.length === 0 && <p className="py-6 text-center text-body text-ink-muted">{vazio}</p>}
      {d && d.resultados.length > 0 && (
        <>
          <div className="hidden overflow-x-auto md:block">
            <DataTable colunas={colunas} linhas={d.resultados} chaveDaLinha={(v) => String(v.id)} legenda={rotulo} />
          </div>
          <div className="flex flex-col gap-3 md:hidden">
            {d.resultados.map((v) => (
              <CartaoDaVenda key={v.id} v={v} agora={agora} comissao={comissao} />
            ))}
          </div>
          {aoIr && (d.proximo || d.anterior) && <Paginacao texto={`Mostrando ${d.resultados.length}`} anterior={d.anterior} proximo={d.proximo} aoIr={aoIr} />}
        </>
      )}
    </section>
  );
}

/** Vendas: propostas abertas, transferências pendentes no Detran e vendidas do mês (VEN-08 a VEN-19, VEN-11). */
export function ListaDeVendas() {
  const { eu } = useSessao();
  const agora = useAgora();
  const hoje = useAmbiente()?.hoje ?? new Date().toISOString().slice(0, 10);
  const mes = mesPorExtenso(hoje);
  const filial = useFilial()?.nome ?? eu.filiais[0]?.nome;
  const { valor, definir } = useFiltrosNaUrl();
  const aba = abaDaUrl(valor("aba"));
  const filtro = ABAS.find((a) => a.valor === aba)?.filtro ?? {};
  const [cursorAbertas, setCursorAbertas] = useState<string | null>(null);
  const [cursorVendidas, setCursorVendidas] = useState<string | null>(null);

  const pendentes = useQuery({ queryKey: ["vendas", "pendentes"], queryFn: () => vendas.listar({ transferencia_pendente: true }) });
  const abertas = useQuery({ queryKey: ["vendas", "abertas", aba, cursorAbertas], queryFn: () => vendas.listar({ ...filtro, cursor: cursorAbertas ?? undefined }), placeholderData: (a) => a });
  const vendidas = useQuery({ queryKey: ["vendas", "vendidas", mesDoDia(hoje), cursorVendidas], queryFn: () => vendas.listar({ aba: "vendidas", mes: mesDoDia(hoje), cursor: cursorVendidas ?? undefined }), placeholderData: (a) => a });
  const pend = pendentes.data?.resultados ?? [];
  const irPara = (a: Aba) => {
    setCursorAbertas(null);
    definir({ aba: a === "todas" ? null : a });
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-title md:text-display">Vendas</h1>
          <p className="m-0 mt-1.5 text-body text-ink-muted">{[comMaiuscula(mes), filial].filter(Boolean).join(" · ")}</p>
        </div>
        {eu.pode.vendas_criar && (
          <Link href="/vendas/nova" className="wl-btn wl-btn--solid">
            <Icone de={Plus} />
            Nova venda
          </Link>
        )}
      </header>

      {pendentes.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(pendentes.error)}
        </p>
      )}

      <Lista
        titulo={aba === "perdidas" ? "Perdidas" : "Propostas abertas"}
        rotulo="Propostas"
        colunas={colunasAbertas(agora)}
        consulta={abertas}
        agora={agora}
        aoIr={setCursorAbertas}
        vazio={aba === "perdidas" ? "Nenhuma venda perdida." : aba === "aguardando" ? "Nenhuma proposta esperando o gerente." : "Nenhuma proposta aberta."}
        cabeca={
          <>
            <div className="hidden md:block">
              <SegmentedControl rotulo="Propostas" opcoes={ABAS.map((a) => ({ valor: a.valor, rotulo: a.rotulo }))} valor={aba} aoMudar={irPara} />
            </div>
            {/* No celular, rótulos curtos para as quatro caberem sem rolar. */}
            <div className="w-full md:hidden [&_.wl-seg]:flex [&_.wl-seg_button]:flex-1 [&_.wl-seg_button]:px-2">
              <SegmentedControl rotulo="Propostas" opcoes={ABAS.map((a) => ({ valor: a.valor, rotulo: a.curto }))} valor={aba} aoMudar={irPara} />
            </div>
          </>
        }
      />

      {pend.length > 0 && (
        <section className="wl-panel" aria-label="Transferências pendentes">
          <div className="wl-panel__head">
            <h2 className="wl-panel__title">Transferências pendentes</h2>
            <span className="text-caption text-ink-muted">{pend.length} no Detran</span>
          </div>
          <div className="hidden overflow-x-auto md:block">
            <DataTable colunas={COLUNAS_PENDENTES} linhas={pend} chaveDaLinha={(v) => String(v.id)} legenda="Transferências pendentes" />
          </div>
          <div className="flex flex-col gap-3 md:hidden">
            {pend.map((v) => (
              <CartaoDaVenda key={v.id} v={v} agora={agora} transferencia />
            ))}
          </div>
        </section>
      )}

      <Lista titulo={`Vendidas em ${mes}`} rotulo="Vendidas" colunas={COLUNAS_VENDIDAS} consulta={vendidas} agora={agora} comissao aoIr={setCursorVendidas} vazio={`Nenhuma venda concluída em ${mes}.`} />
    </div>
  );
}
