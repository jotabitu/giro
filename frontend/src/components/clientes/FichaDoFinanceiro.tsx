"use client";

import { useMutation, useQuery, type UseQueryResult } from "@tanstack/react-query";
import { Info, MessageCircle } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Button, CelulaDupla, DataTable, Icone, KpiGrid, KpiTile, Panel, StatusBadge, type ColunaTabela } from "@/design-system";
import { clientes, financeiro, type ClienteResumo, type ContaReceber, type LocacaoDoCliente } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { origemDaConta, rotuloDaForma, rotuloDaParcela, situacaoDaConta } from "@/lib/financeiro";
import { celular, dataCurta, dinheiro, dinheiroSemZerosOuTraco, iniciais, mesAno, placa, soDigitos } from "@/lib/formatos";
import { tomDoStatus } from "@/lib/tom";

// USR-09, D-28: a ficha do cliente para o financeiro tem contato, locações e o financeiro do cliente (total pago,
// em aberto, parcelas atrasadas com os dias, pagamentos), sem documentos, endereço nem análise do cadastro, e com Cobrar como única ação.
// Valor do dia, dias de atraso e a ação vêm da API; a tela só mostra.

function Linha({ rotulo, children }: { rotulo: ReactNode; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <dt className="text-ink-muted">{rotulo}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

function Estado({ consulta, vazio, textoVazio, children }: { consulta: UseQueryResult<unknown>; vazio: boolean; textoVazio: string; children: ReactNode }) {
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  if (!consulta.data) return <p className="text-body text-ink-muted">Carregando…</p>;
  if (vazio) return <p className="text-body text-ink-muted">{textoVazio}</p>;
  return <>{children}</>;
}

const COLUNAS_LOCACOES: ColunaTabela<LocacaoDoCliente>[] = [
  { chave: "codigo", titulo: "Contrato", mono: true },
  { chave: "veiculo", titulo: "Veículo", celula: (l) => <CelulaDupla principal={l.veiculo.modelo} secundaria={<span className="wl-mono">{placa(l.veiculo.placa)}</span>} /> },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (l) => (
      <StatusBadge tom={tomDoStatus(l.situacao.tom)} compacto>
        {l.situacao.rotulo}
      </StatusBadge>
    ),
  },
  { chave: "pago", titulo: "Pago", celula: (l) => dinheiro(l.pago_centavos) },
];

function Atrasada({ c }: { c: ContaReceber }) {
  const s = situacaoDaConta(c);
  return (
    <li className="flex items-center gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <span className="min-w-0 flex-1">
        <span className="wl-mono block">{origemDaConta(c)}</span>
        <span className="block text-caption text-ink-muted">
          {rotuloDaParcela(c)} · venceu {dataCurta(c.vencimento)}
        </span>
      </span>
      <StatusBadge tom={s.tom} compacto>
        {s.rotulo}
      </StatusBadge>
      <span className="shrink-0 font-semibold">{dinheiro(c.valor_hoje.total_centavos)}</span>
    </li>
  );
}

function Pagamento({ c }: { c: ContaReceber }) {
  return (
    <li className="flex items-center gap-3 border-b border-line py-[11px] text-body last:border-b-0">
      <span className="min-w-0 flex-1">
        <span className="wl-mono block">{origemDaConta(c)}</span>
        <span className="block text-caption text-ink-muted">
          {rotuloDaParcela(c)} · {rotuloDaForma(c.forma)}
          {c.pago_em ? ` · ${dataCurta(c.pago_em)}` : ""}
        </span>
      </span>
      <span className="shrink-0 font-semibold">{dinheiro(c.valor_centavos)}</span>
    </li>
  );
}

export function FichaDoFinanceiro({ c }: { c: ClienteResumo }) {
  const [aviso, setAviso] = useState<string | null>(null);
  const locacoes = useQuery({ queryKey: ["cliente", c.id, "locacoes"], queryFn: () => clientes.locacoes(c.id) });
  const atrasadas = useQuery({ queryKey: ["cliente", c.id, "contas", "atrasadas"], queryFn: () => financeiro.listarContas({ cliente: c.id, situacao: "atrasadas" }) });
  const pagas = useQuery({ queryKey: ["cliente", c.id, "contas", "pagas"], queryFn: () => financeiro.listarContas({ cliente: c.id, situacao: "pagas" }) });

  const acao = c.acao_principal?.codigo === "cobrar" ? c.acao_principal : null;
  const cobrar = useMutation({
    mutationFn: (alvoId: number) => financeiro.cobrar(alvoId),
    onSuccess: (r) => setAviso(r.enviadas > 0 ? `Cobrança enviada a ${c.nome}.` : `Nada foi enviado a ${c.nome}: a conta já foi cobrada hoje ou o cliente não tem contato.`),
  });
  const fin = c.financeiro;
  const lista = locacoes.data;

  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Caminho" className="text-caption text-ink-muted">
        <Link href="/clientes" className="text-ink-muted no-underline">
          Clientes
        </Link>{" "}
        / {c.nome}
      </nav>

      <header className="-mt-2 flex flex-wrap items-center gap-5">
        <span aria-hidden="true" className="grid h-[72px] w-[72px] shrink-0 place-items-center rounded-lg bg-solid text-[24px] font-bold text-on-solid">
          {iniciais(c.nome)}
        </span>
        <div className="min-w-0">
          <h1 className="text-title md:text-display">{c.nome}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge tom={tomDoStatus(c.situacao.tom)} compacto>
              {c.situacao.rotulo}
            </StatusBadge>
            <span className="text-[13px] text-ink-muted">cliente desde {mesAno(c.cliente_desde)}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 md:ml-auto">
          <a href={`https://wa.me/55${soDigitos(c.celular)}`} target="_blank" rel="noreferrer" className="wl-btn justify-center no-underline" style={{ height: 44 }}>
            <Icone de={MessageCircle} />
            WhatsApp
          </a>
          {acao?.alvo && (
            <Button variante="solido" disabled={cobrar.isPending} onClick={() => cobrar.mutate(acao.alvo!.id)} style={{ height: 44 }}>
              {acao.rotulo}
            </Button>
          )}
        </div>
      </header>

      {aviso && (
        <p role="status" className="rounded-lg bg-surface-sunken p-4 text-body">
          {aviso}
        </p>
      )}
      {cobrar.isError && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {mensagemDoErro(cobrar.error)}
        </p>
      )}

      {c.bloqueio && (
        <p role="status" className="flex items-start gap-3 rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          <Icone de={Info} />
          <span>{c.bloqueio.descricao}</span>
        </p>
      )}

      <KpiGrid>
        <KpiTile destaque rotulo="Total pago" valor={dinheiroSemZerosOuTraco(fin?.total_pago_centavos)} contexto={lista ? `em ${lista.total} locações` : undefined} />
        <KpiTile rotulo="Em aberto" valor={dinheiroSemZerosOuTraco(fin?.em_aberto_centavos)} contexto={fin ? (fin.em_aberto_centavos > 0 ? "parcelas vencidas" : "nenhuma parcela vencida") : undefined} />
      </KpiGrid>

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-6">
          <Panel titulo="Parcelas atrasadas">
            <Estado consulta={atrasadas} vazio={atrasadas.data?.resultados.length === 0} textoVazio="Nenhuma parcela atrasada.">
              <ul>{atrasadas.data?.resultados.map((x) => <Atrasada key={x.id} c={x} />)}</ul>
            </Estado>
          </Panel>

          <Panel titulo="Locações">
            <Estado consulta={locacoes} vazio={lista?.resultados.length === 0} textoVazio="Nenhuma locação.">
              {lista && <DataTable colunas={COLUNAS_LOCACOES} linhas={lista.resultados} chaveDaLinha={(l) => String(l.id)} legenda="Locações do cliente" />}
            </Estado>
          </Panel>
        </div>

        <aside className="flex min-w-0 flex-[1_1_340px] flex-col gap-6">
          <Panel titulo="Contato">
            <dl>
              <Linha rotulo="Celular">{celular(c.celular)}</Linha>
              <Linha rotulo="E-mail">{c.email ?? "Não informado"}</Linha>
            </dl>
          </Panel>

          <Panel titulo="Pagamentos">
            <Estado consulta={pagas} vazio={pagas.data?.resultados.length === 0} textoVazio="Nenhum pagamento ainda.">
              <ul>{pagas.data?.resultados.map((x) => <Pagamento key={x.id} c={x} />)}</ul>
            </Estado>
          </Panel>
        </aside>
      </div>
    </div>
  );
}
