"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Icone, SegmentedControl, StatusBadge, TextField } from "@/design-system";
import { Confirmacao } from "@/components/financeiro/Comuns";
import { auditoria, type ExportacaoRecente, type PeriodoDaExportacao } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { arquivoDaExportacao, esteAno, ROTULO_DA_EXPORTACAO } from "@/lib/auditoria";
import { mensagemDoErro } from "@/lib/erros";
import { dataHoraCurta, diaDe } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";

// Referência: docs/telas/html/Admin-Exportar-Desktop.dc.html e Admin-Exportar-Mobile.dc.html.
// No MVP a tela é fixa: só a auditoria em CSV, por período (docs/api/auditoria.md, "O que existe no MVP", opção A de 12 out 2026).
// Clientes, veículos, contratos, financeiro, fotos, planilha, backup completo e backup automático entram na fase 2.

type Recorte = "tudo" | "ano" | "escolher";
const RECORTES = [
  { valor: "tudo", rotulo: "Tudo" },
  { valor: "ano", rotulo: "Este ano" },
  { valor: "escolher", rotulo: "Escolher" },
] as const;

/** Baixa o arquivo com o login da pessoa e entrega ao navegador. A rota da API exige autenticação, então não é um link simples. */
function useBaixar() {
  return useMutation({
    mutationFn: async (e: ExportacaoRecente) => {
      const arquivo = await auditoria.baixar(e.id);
      const url = URL.createObjectURL(arquivo);
      const a = document.createElement("a");
      a.href = url;
      a.download = `auditoria-${e.id}.csv`;
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    },
  });
}

function Recentes({ itens, aoBaixar, baixando }: { itens: ExportacaoRecente[]; aoBaixar: (e: ExportacaoRecente) => void; baixando: boolean }) {
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="wl-table" aria-label="Exportações recentes">
          <thead>
            <tr>
              <th scope="col">Quando</th>
              <th scope="col">Quem</th>
              <th scope="col">Conteúdo</th>
              <th scope="col">Arquivo</th>
              <th scope="col">Situação</th>
              <th scope="col" />
            </tr>
          </thead>
          <tbody>
            {itens.map((e) => {
              const s = ROTULO_DA_EXPORTACAO[e.status];
              return (
                <tr key={e.id}>
                  <td className="wl-mono whitespace-nowrap">{dataHoraCurta(e.solicitada_em)}</td>
                  <td>{e.solicitada_por}</td>
                  <td>{e.conteudo}</td>
                  <td>{arquivoDaExportacao(e.formato, e.tamanho_bytes)}</td>
                  <td>
                    <StatusBadge tom={s.tom} compacto>
                      {s.rotulo}
                    </StatusBadge>
                  </td>
                  <td>
                    {e.status === "pronta" && (
                      <Button compacto variante="quieto" disabled={baixando} onClick={() => aoBaixar(e)}>
                        Baixar
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="md:hidden">
        {itens.map((e) => {
          const s = ROTULO_DA_EXPORTACAO[e.status];
          return (
            <div key={e.id} className="flex flex-col gap-2 border-b border-line py-[11px] text-body last:border-b-0">
              <div className="flex items-center justify-between gap-3">
                <span className="text-ink-muted">
                  {dataHoraCurta(e.solicitada_em)} · {e.conteudo}
                </span>
                <StatusBadge tom={s.tom} compacto>
                  {s.rotulo}
                </StatusBadge>
              </div>
              {e.status === "pronta" && (
                <div>
                  <Button compacto variante="quieto" disabled={baixando} onClick={() => aoBaixar(e)}>
                    Baixar
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

/** Exportar dados da empresa (AUD-07): pede a auditoria em CSV e lista as exportações recentes, com download pelo sistema. */
export function ExportarDados() {
  const { eu } = useSessao();
  const cliente = useQueryClient();
  const hoje = diaDe(useAgora().toISOString());
  const [recorte, setRecorte] = useState<Recorte>("tudo");
  const [de, setDe] = useState("");
  const [ate, setAte] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);

  const podeVer = eu.pode.administracao;
  const recentes = useQuery({
    queryKey: ["auditoria", "exportacoes"],
    queryFn: () => auditoria.exportacoes(),
    enabled: podeVer,
    refetchInterval: (q) => (q.state.data?.some((e) => e.status === "na_fila") ? 8_000 : false),
  });

  const periodo: PeriodoDaExportacao | null = recorte === "tudo" ? null : recorte === "ano" ? esteAno(hoje) : de && ate ? { de, ate } : null;
  const periodoCompleto = recorte !== "escolher" || (de !== "" && ate !== "" && de <= ate);

  const gerar = useMutation({
    mutationFn: () => auditoria.exportar({ itens: ["auditoria"], formato: "csv", periodo }),
    onSuccess: async () => {
      setAviso("Pedido recebido. Avisamos por e-mail quando o arquivo ficar pronto, com um link válido por 7 dias.");
      await cliente.invalidateQueries({ queryKey: ["auditoria", "exportacoes"] });
    },
  });
  const baixar = useBaixar();

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador exporta dados.
      </p>
    );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-4">
        <Link href="/admin/auditoria" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Exportar dados</h1>
          <p className="mt-1.5 mb-0 hidden text-body text-ink-muted md:block">Os dados são da sua empresa. Baixe quando quiser, inclusive se for cancelar.</p>
        </div>
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}

      <section className="wl-panel flex flex-col gap-4" aria-label="O que exportar">
        <h2 className="text-heading">O que exportar</h2>
        <div className="flex items-start gap-3 rounded-md bg-surface-sunken px-4 py-3">
          <div>
            <div className="text-body font-medium">Auditoria</div>
            <small className="text-caption text-ink-muted">registro completo de quem fez o quê, em CSV</small>
          </div>
        </div>
        <div className="wl-field">
          <span className="wl-field__label">Período</span>
          <SegmentedControl rotulo="Período" opcoes={RECORTES} valor={recorte} aoMudar={setRecorte} />
        </div>
        {recorte === "escolher" && (
          <div className="grid gap-3 md:grid-cols-2">
            <TextField cheio rotulo="De" type="date" max={hoje} value={de} onChange={(e) => setDe(e.target.value)} />
            <TextField cheio rotulo="Até" type="date" max={hoje} value={ate} onChange={(e) => setAte(e.target.value)} erro={de && ate && de > ate ? "A data final precisa ser depois da inicial." : undefined} />
          </div>
        )}
        {gerar.isError && (
          <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
            {mensagemDoErro(gerar.error)}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Button variante="solido" disabled={!periodoCompleto || gerar.isPending} onClick={() => gerar.mutate()}>
            {gerar.isPending ? "Pedindo…" : "Gerar arquivo"}
          </Button>
          <span className="text-caption text-ink-muted">Fica pronto em alguns minutos. Avisamos por e-mail com um link válido por 7 dias.</span>
        </div>
      </section>

      <section className="wl-panel" aria-label="Exportações recentes">
        <h2 className="mb-2 text-heading">
          <span className="hidden md:inline">Exportações recentes</span>
          <span className="md:hidden">Recentes</span>
        </h2>
        {recentes.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(recentes.error)}
          </p>
        )}
        {recentes.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando as exportações…
          </p>
        )}
        {recentes.data?.length === 0 && <p className="py-4 text-body text-ink-muted">Nenhuma exportação ainda.</p>}
        {baixar.isError && (
          <p role="alert" className="mb-2 rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
            {mensagemDoErro(baixar.error)}
          </p>
        )}
        {recentes.data && recentes.data.length > 0 && <Recentes itens={recentes.data} aoBaixar={(e) => baixar.mutate(e)} baixando={baixar.isPending} />}
      </section>
    </div>
  );
}
