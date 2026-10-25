"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, SegmentedControl, StatusBadge } from "@/design-system";
import { precos as api, type CategoriaDePreco } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, dinheiroSemZeros } from "@/lib/formatos";
import { DialogoDaCategoria } from "./DialogoDaCategoria";

export type CategoriasDePrecoProps = {
  /** Filial do filtro "Filial X"; sem ela, só "Todas as filiais". */
  filial?: { id: number; nome: string } | null;
  /** Abre o diálogo de categoria nova (o botão fica no cabeçalho da tela ou do passo do assistente). */
  criando: boolean;
  aoFecharCriacao: () => void;
  aoAvisar: (aviso: string) => void;
};

function Resumo({ c }: { c: CategoriaDePreco }) {
  return (
    <>
      <span className="wl-cell-main">{c.nome}</span>
      {!c.ativo && (
        <StatusBadge tom="neutro" compacto>
          Desativada
        </StatusBadge>
      )}
      <small className="block text-caption text-ink-muted">
        {[c.modelos_resumo, `${c.veiculos} ${c.veiculos === 1 ? "veículo" : "veículos"}`].filter(Boolean).join(" · ")}
        {c.filial ? ` · ${c.filial.nome}` : ""}
      </small>
      {c.proximo_preco && <small className="block text-caption text-ink-muted">Novo preço a partir de {dataCurta(c.proximo_preco.vigente_desde)}</small>}
    </>
  );
}

/** Painel "Por categoria": preço vigente por categoria, da empresa ou da filial (LOC-01, FIL-04). Reaproveitado pelo passo Tabela de preços do assistente. */
export function CategoriasDePreco({ filial, criando, aoFecharCriacao, aoAvisar }: CategoriasDePrecoProps) {
  const [escopo, setEscopo] = useState<"filial" | "todas">(filial ? "filial" : "todas");
  const [editando, setEditando] = useState<CategoriaDePreco | null>(null);
  const [verDesativadas, setVerDesativadas] = useState(false);
  const filialId = escopo === "filial" ? filial?.id : undefined;
  const consulta = useQuery({ queryKey: ["precos", "categorias", filialId ?? "todas"], queryFn: () => api.categorias({ filial: filialId }) });

  const todas = consulta.data ?? [];
  const lista = verDesativadas ? todas : todas.filter((c) => c.ativo);
  const temDesativada = todas.some((c) => !c.ativo);

  return (
    <section className="wl-panel" aria-label="Por categoria">
      <div className="wl-panel__head">
        <h2 className="wl-panel__title">Por categoria</h2>
        {filial && (
          <SegmentedControl
            rotulo="Filial"
            valor={escopo}
            aoMudar={setEscopo}
            opcoes={[
              { valor: "filial", rotulo: filial.nome },
              { valor: "todas", rotulo: "Todas as filiais" },
            ]}
          />
        )}
      </div>
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando…
        </p>
      )}
      {consulta.isError && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isSuccess && lista.length === 0 && <p className="m-0 text-body text-ink-muted">Nenhuma categoria ainda. Use o botão Nova categoria para criar a primeira.</p>}
      {lista.length > 0 && (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="wl-table min-w-[820px]" aria-label="Preços por categoria">
              <thead>
                <tr>
                  <th>Categoria</th>
                  <th>Diária</th>
                  <th>Semanal</th>
                  <th>Mensal</th>
                  <th>Caução</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lista.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <Resumo c={c} />
                    </td>
                    <td className="wl-mono">{c.preco_vigente ? dinheiroSemZeros(c.preco_vigente.diaria_centavos) : "—"}</td>
                    <td className="wl-mono">{c.preco_vigente ? dinheiroSemZeros(c.preco_vigente.semanal_centavos) : "—"}</td>
                    <td className="wl-mono">{c.preco_vigente ? dinheiroSemZeros(c.preco_vigente.mensal_centavos) : "—"}</td>
                    <td className="wl-mono">{c.preco_vigente ? dinheiroSemZeros(c.preco_vigente.caucao_centavos) : "—"}</td>
                    <td>
                      <Button compacto variante="quieto" aria-label={`Editar ${c.nome}`} onClick={() => setEditando(c)}>
                        Editar
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="m-0 flex list-none flex-col gap-3 p-0 md:hidden" aria-label="Preços por categoria">
            {lista.map((c) => (
              <li key={c.id} className="rounded-[20px] bg-surface-sunken p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Resumo c={c} />
                  </div>
                  <Button compacto variante="quieto" aria-label={`Editar ${c.nome}`} onClick={() => setEditando(c)}>
                    Editar
                  </Button>
                </div>
                {c.preco_vigente && (
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {(
                      [
                        ["Diária", c.preco_vigente.diaria_centavos],
                        ["Semanal", c.preco_vigente.semanal_centavos],
                        ["Mensal", c.preco_vigente.mensal_centavos],
                      ] as const
                    ).map(([rotulo, valor]) => (
                      <div key={rotulo}>
                        <div className="text-caption text-ink-muted">{rotulo}</div>
                        <div className="wl-mono font-medium">{dinheiroSemZeros(valor)}</div>
                      </div>
                    ))}
                  </div>
                )}
                {c.preco_vigente && <div className="mt-2 text-caption text-ink-muted">Caução {dinheiroSemZeros(c.preco_vigente.caucao_centavos)}</div>}
              </li>
            ))}
          </ul>
        </>
      )}
      {(temDesativada || verDesativadas) && (
        <button type="button" className="mt-3 self-start text-caption underline" onClick={() => setVerDesativadas((v) => !v)}>
          {verDesativadas ? "Esconder categorias desativadas" : "Mostrar categorias desativadas"}
        </button>
      )}
      {criando && (
        <DialogoDaCategoria
          categoria={null}
          filialId={filialId ?? null}
          aoFechar={aoFecharCriacao}
          aoConcluir={(aviso) => {
            aoFecharCriacao();
            aoAvisar(aviso);
          }}
        />
      )}
      {editando && (
        <DialogoDaCategoria
          categoria={editando}
          aoFechar={() => setEditando(null)}
          aoConcluir={(aviso) => {
            setEditando(null);
            aoAvisar(aviso);
          }}
        />
      )}
    </section>
  );
}
