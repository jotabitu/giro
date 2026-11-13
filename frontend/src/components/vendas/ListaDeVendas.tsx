"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { CelulaDupla, DataTable, StatusBadge, type ColunaTabela } from "@/design-system";
import { Paginacao } from "@/components/lista/Paginacao";
import { vendas, type Venda } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCompleta, dataCurta, dinheiro, placa } from "@/lib/formatos";

// Referência: docs/telas/html/Vendas-Desktop.dc.html e Vendas-Mobile.dc.html (T-420).
// Só a parte que a API já entrega (docs/api/vendas.md): as transferências pendentes e a lista de vendas, com o rótulo da origem.
// Funil, propostas, meta e comissão chegam com o módulo de vendas (T-418).

const situacaoDaVenda = (v: Venda) => (v.vendida_em ? `Vendida ${dataCurta(v.vendida_em)}` : "Vendida");

function SituacaoDaVenda({ v }: { v: Venda }) {
  return (
    <CelulaDupla
      principal={situacaoDaVenda(v)}
      secundaria={
        v.transferencia.pendente ? (
          <StatusBadge tom="alerta" compacto>
            {situacaoDaTransferencia(v)}
          </StatusBadge>
        ) : null
      }
    />
  );
}

const situacaoDaTransferencia = (v: Venda) => (v.transferencia.pendente ? "Falta a transferência no Detran" : `Transferência feita em ${v.transferencia.feita_em ? dataCompleta(v.transferencia.feita_em) : "—"}`);

function Origem({ v }: { v: Venda }) {
  return <span>{v.origem_rotulo}</span>;
}

function AbrirLocacao({ v }: { v: Venda }) {
  if (!v.locacao) return null;
  return (
    <Link href={`/locacoes/${v.locacao.id}`} className="wl-btn wl-btn--sm">
      Abrir locação
    </Link>
  );
}

const celulaCliente = (v: Venda) => <CelulaDupla principal={v.cliente.nome} secundaria={<span className="wl-mono">{v.locacao ? `${v.codigo} · ${v.locacao.codigo}` : v.codigo}</span>} />;
const celulaVeiculo = (v: Venda) => <CelulaDupla principal={<span className="font-normal">{v.veiculo.modelo}</span>} secundaria={placa(v.veiculo.placa)} />;

const COLUNAS_PENDENTES: ColunaTabela<Venda>[] = [
  { chave: "cliente", titulo: "Cliente", celula: celulaCliente },
  { chave: "veiculo", titulo: "Veículo", celula: celulaVeiculo },
  { chave: "origem", titulo: "Origem", celula: (v) => <Origem v={v} /> },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (v) => (
      <StatusBadge tom="alerta" compacto>
        {situacaoDaTransferencia(v)}
      </StatusBadge>
    ),
  },
  { chave: "abrir", titulo: "", celula: (v) => <AbrirLocacao v={v} /> },
];

const COLUNAS_VENDAS: ColunaTabela<Venda>[] = [
  { chave: "cliente", titulo: "Cliente", celula: celulaCliente },
  { chave: "veiculo", titulo: "Veículo", celula: celulaVeiculo },
  { chave: "origem", titulo: "Origem", celula: (v) => <Origem v={v} /> },
  { chave: "valor", titulo: "Valor", mono: true, celula: (v) => dinheiro(v.preco_final_centavos) },
  { chave: "situacao", titulo: "Situação", celula: (v) => <SituacaoDaVenda v={v} /> },
  { chave: "abrir", titulo: "", celula: (v) => <AbrirLocacao v={v} /> },
];

function CartaoDaVenda({ v }: { v: Venda }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg bg-surface-sunken p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-body font-medium">{v.cliente.nome}</div>
          <div className="wl-mono text-caption text-ink-muted">{v.locacao ? `${v.codigo} · ${v.locacao.codigo}` : v.codigo}</div>
        </div>
        <span className="text-body font-medium">{dinheiro(v.preco_final_centavos)}</span>
      </div>
      <div className="text-caption text-ink-muted">
        {v.veiculo.modelo} · <span className="wl-mono">{placa(v.veiculo.placa)}</span>
      </div>
      <div className="text-caption text-ink-muted">{v.origem_rotulo}</div>
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col items-start gap-1 text-caption text-ink-muted">
          {situacaoDaVenda(v)}
          {v.transferencia.pendente && (
            <StatusBadge tom="alerta" compacto>
              {situacaoDaTransferencia(v)}
            </StatusBadge>
          )}
        </div>
        <AbrirLocacao v={v} />
      </div>
    </div>
  );
}

/** Vendas: as transferências pendentes no Detran e a lista de vendas (VEN-11). A venda da quitação traz "Quitação de locação". */
export function ListaDeVendas() {
  const [cursor, setCursor] = useState<string | null>(null);
  const pendentes = useQuery({ queryKey: ["vendas", "pendentes"], queryFn: () => vendas.listar({ transferencia_pendente: true }) });
  const lista = useQuery({ queryKey: ["vendas", "lista", cursor], queryFn: () => vendas.listar({ cursor: cursor ?? undefined }), placeholderData: (anterior) => anterior });
  const pend = pendentes.data?.resultados ?? [];
  const d = lista.data;

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-title md:text-display">Vendas</h1>
        <p className="m-0 mt-1.5 text-body text-ink-muted">Transferências no Detran e vendas da empresa.</p>
      </header>

      {pendentes.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(pendentes.error)}
        </p>
      )}

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
              <CartaoDaVenda key={v.id} v={v} />
            ))}
          </div>
        </section>
      )}

      <section className="wl-panel" aria-label="Vendas">
        <div className="wl-panel__head">
          <h2 className="wl-panel__title">Vendas</h2>
        </div>
        {lista.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando as vendas…
          </p>
        )}
        {lista.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(lista.error)}
          </p>
        )}
        {d && d.resultados.length === 0 && <p className="py-6 text-center text-body text-ink-muted">Nenhuma venda ainda.</p>}
        {d && d.resultados.length > 0 && (
          <>
            <div className="hidden overflow-x-auto md:block">
              <DataTable colunas={COLUNAS_VENDAS} linhas={d.resultados} chaveDaLinha={(v) => String(v.id)} legenda="Vendas" />
            </div>
            <div className="flex flex-col gap-3 md:hidden">
              {d.resultados.map((v) => (
                <CartaoDaVenda key={v.id} v={v} />
              ))}
            </div>
            <Paginacao texto={`Mostrando ${d.resultados.length}`} anterior={d.anterior} proximo={d.proximo} aoIr={setCursor} />
          </>
        )}
      </section>
    </div>
  );
}
