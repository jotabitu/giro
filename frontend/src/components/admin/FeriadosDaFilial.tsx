"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";
import { Button, Icone, TextField } from "@/design-system";
import { filiais, type FeriadoNovo } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { anoDe } from "@/lib/filiais";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, diaDe } from "@/lib/formatos";

/**
 * Feriados da filial (FIL-03): a filial nasce sem nenhum; o sistema sugere os nacionais do ano e a pessoa confirma ou
 * acrescenta os locais. Nada vale antes da confirmação.
 */
export function FeriadosDaFilial({ filialId, anoSeguintePendente }: { filialId: number; anoSeguintePendente: boolean }) {
  const cliente = useQueryClient();
  const hoje = diaDe(useAgora().toISOString());
  const [ano, setAno] = useState(anoDe(hoje) + (anoSeguintePendente ? 1 : 0));
  const [sugerindo, setSugerindo] = useState(false);
  const [adicionando, setAdicionando] = useState(false);
  const [data, setData] = useState("");
  const [nome, setNome] = useState("");
  const [marcados, setMarcados] = useState<string[]>([]);

  const feriados = useQuery({ queryKey: ["filiais-admin", "feriados", filialId, ano], queryFn: () => filiais.feriados(filialId, ano) });
  const sugestoes = useQuery({ queryKey: ["filiais-admin", "sugestoes", filialId, ano], queryFn: () => filiais.sugestoesDeFeriados(filialId, ano), enabled: sugerindo });

  const atualizar = () => cliente.invalidateQueries({ queryKey: ["filiais-admin"] });
  const confirmar = useMutation({
    mutationFn: (novos: FeriadoNovo[]) => filiais.confirmarFeriados(filialId, novos),
    onSuccess: async () => {
      setSugerindo(false);
      setAdicionando(false);
      setMarcados([]);
      setData("");
      setNome("");
      await atualizar();
    },
  });
  const remover = useMutation({ mutationFn: (id: number) => filiais.removerFeriado(filialId, id), onSuccess: atualizar });

  const novas = (sugestoes.data ?? []).filter((s) => !s.ja_cadastrado);

  return (
    <div className="flex flex-col gap-2 border-t border-line pt-4">
      <div className="text-body font-medium">Feriados da filial</div>
      <p className="m-0 text-caption leading-[18px] text-ink-muted">Datas em que a filial fica fechada. A cada ano o sistema sugere os nacionais; você confirma ou acrescenta os locais.</p>

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Feriados de ${ano}`}>
        {feriados.isPending && <span className="text-caption text-ink-muted">Carregando os feriados…</span>}
        {feriados.data?.length === 0 && <span className="text-caption text-ink-muted">Nenhum feriado confirmado em {ano}.</span>}
        {feriados.data?.map((f) => (
          <span key={f.id} className="wl-badge wl-badge--sm inline-flex items-center gap-1">
            {dataCurta(f.data)} · {f.nome}
            <button type="button" aria-label={`Remover ${f.nome}`} disabled={remover.isPending} onClick={() => remover.mutate(f.id)} className="grid size-6 place-items-center rounded-full">
              <Icone de={X} />
            </button>
          </span>
        ))}
        <Button compacto variante="quieto" onClick={() => (setAdicionando((a) => !a), setSugerindo(false))}>
          Adicionar feriado
        </Button>
        <Button compacto variante="quieto" onClick={() => (setSugerindo((s) => !s), setAdicionando(false))}>
          Sugestões de {ano}
        </Button>
        <Button compacto variante="quieto" onClick={() => setAno(ano === anoDe(hoje) ? ano + 1 : anoDe(hoje))}>
          Ver {ano === anoDe(hoje) ? ano + 1 : anoDe(hoje)}
        </Button>
      </div>

      {sugerindo && (
        <div className="flex flex-col gap-1 rounded-md bg-surface-sunken p-4" aria-label="Sugestões de feriados">
          {sugestoes.isPending && <span className="text-caption text-ink-muted">Carregando as sugestões…</span>}
          {sugestoes.data && novas.length === 0 && <span className="text-caption text-ink-muted">Todos os feriados nacionais de {ano} já estão confirmados.</span>}
          {novas.map((s) => (
            <label key={s.data} className="flex min-h-[44px] items-center gap-3 text-body">
              <input type="checkbox" checked={marcados.includes(s.data)} onChange={(e) => setMarcados(e.target.checked ? [...marcados, s.data] : marcados.filter((x) => x !== s.data))} className="size-[22px] accent-[var(--solid)]" />
              {dataCurta(s.data)} · {s.nome}
            </label>
          ))}
          {novas.length > 0 && (
            <div>
              <Button
                compacto
                variante="solido"
                disabled={marcados.length === 0 || confirmar.isPending}
                onClick={() => confirmar.mutate(novas.filter((s) => marcados.includes(s.data)).map((s) => ({ data: s.data, nome: s.nome, origem: "nacional" as const })))}
              >
                Confirmar os marcados
              </Button>
            </div>
          )}
        </div>
      )}

      {adicionando && (
        <div className="flex flex-col gap-3 rounded-md bg-surface-sunken p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <TextField cheio rotulo="Data" type="date" value={data} onChange={(e) => setData(e.target.value)} />
            <TextField cheio rotulo="Nome" placeholder="Ex.: São José" value={nome} onChange={(e) => setNome(e.target.value)} />
          </div>
          <div>
            <Button compacto variante="solido" disabled={!data || nome.trim() === "" || confirmar.isPending} onClick={() => confirmar.mutate([{ data, nome: nome.trim(), origem: "local" }])}>
              Adicionar
            </Button>
          </div>
        </div>
      )}

      {(confirmar.isError || remover.isError) && (
        <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
          {mensagemDoErro(confirmar.error ?? remover.error)}
        </p>
      )}
    </div>
  );
}
