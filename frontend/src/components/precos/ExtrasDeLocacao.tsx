"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button, Dialogo, Icone, StatusBadge, TextField } from "@/design-system";
import { precos as api, type CobrancaDoExtra, type ExtraDePreco } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";
import { reaisDoCentavos, ROTULO_DA_COBRANCA } from "@/lib/precos";

const COBRANCAS: CobrancaDoExtra[] = ["por_periodo", "unica"];

function DialogoDoExtra({ extra, aoFechar, aoConcluir }: { extra: ExtraDePreco | null; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cliente = useQueryClient();
  const [nome, setNome] = useState(extra?.nome ?? "");
  const [valor, setValor] = useState(extra ? reaisDoCentavos(extra.valor_centavos) : "");
  const [cobranca, setCobranca] = useState<CobrancaDoExtra>(extra?.cobranca ?? "por_periodo");
  const [erroLocal, setErroLocal] = useState<string | null>(null);

  const salvar = useMutation({
    mutationFn: async () => {
      const centavos = centavosDoTexto(valor);
      if (centavos === null) {
        setErroLocal("Informe um valor em reais, como 15,00.");
        throw new Error("valor");
      }
      setErroLocal(null);
      const corpo = { nome, valor_centavos: centavos, cobranca };
      return extra ? api.alterarExtra(extra.id, corpo) : api.criarExtra(corpo);
    },
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["precos", "extras"] });
      aoConcluir(extra ? "Extra salvo. O novo valor vale para locações novas." : "Extra criado.");
    },
  });
  const desativar = useMutation({
    mutationFn: () => api.desativarExtra(extra!.id),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["precos", "extras"] });
      aoConcluir("Extra desativado. Ele sai da escolha em locações novas.");
    },
  });
  const trabalhando = salvar.isPending || desativar.isPending;
  const erro = erroLocal ? null : salvar.error;

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={extra ? `Editar ${extra.nome}` : "Novo extra"}
      descricao="Mudar o valor vale para locações novas. Quem já assinou mantém o valor da assinatura."
      fecharAoClicarFora={false}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={trabalhando || !nome.trim()} onClick={() => salvar.mutate()}>
            {salvar.isPending ? "Salvando…" : "Salvar"}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!trabalhando && nome.trim()) salvar.mutate();
        }}
      >
        <TextField cheio rotulo="Nome do extra" value={nome} onChange={(e) => setNome(e.target.value)} erro={campoDoErro(erro, "nome")} autoFocus />
        <TextField cheio rotulo="Valor" mono inputMode="decimal" autoComplete="off" value={valor} onChange={(e) => setValor(e.target.value)} erro={erroLocal ?? campoDoErro(erro, "valor_centavos")} />
        <div className="wl-field">
          <span className="wl-field__label" id="cobranca-do-extra">
            Cobrança
          </span>
          <div role="radiogroup" aria-labelledby="cobranca-do-extra" className="grid grid-cols-2 gap-2">
            {COBRANCAS.map((c) => (
              <button
                key={c}
                type="button"
                role="radio"
                aria-checked={cobranca === c}
                onClick={() => setCobranca(c)}
                className={`rounded-md px-3 py-2.5 text-body font-medium ${cobranca === c ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
              >
                {ROTULO_DA_COBRANCA[c]}
              </button>
            ))}
          </div>
        </div>
        {erro && !(erro as { campos?: unknown }).campos && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(erro)}
          </p>
        )}
        {extra?.ativo && (
          <div className="border-t border-line pt-3">
            <Button compacto variante="quieto" disabled={trabalhando} onClick={() => desativar.mutate()}>
              Desativar extra
            </Button>
            {desativar.isError && (
              <p role="alert" className="m-0 mt-2 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
                {mensagemDoErro(desativar.error)}
              </p>
            )}
          </div>
        )}
      </form>
    </Dialogo>
  );
}

/** Painel "Extras" (LOC-02): capacete, cadeado e o que mais a locadora cobra à parte. */
export function ExtrasDeLocacao({ aoAvisar }: { aoAvisar: (aviso: string) => void }) {
  const [verDesativados, setVerDesativados] = useState(false);
  const [dialogo, setDialogo] = useState<{ extra: ExtraDePreco | null } | null>(null);
  const consulta = useQuery({ queryKey: ["precos", "extras", verDesativados], queryFn: () => api.extras(verDesativados ? {} : { ativo: true }) });
  const lista = consulta.data ?? [];

  return (
    <section className="wl-panel" aria-label="Extras">
      <div className="wl-panel__head">
        <h2 className="wl-panel__title">Extras</h2>
        <Button compacto icone={<Icone de={Plus} />} onClick={() => setDialogo({ extra: null })}>
          Extra
        </Button>
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
      {consulta.isSuccess && lista.length === 0 && <p className="m-0 text-body text-ink-muted">Nenhum extra cadastrado.</p>}
      {lista.map((e) => (
        <div key={e.id} className="flex items-center gap-3 border-b border-line py-3.5 last:border-b-0">
          <div className="min-w-0 flex-1">
            <div className="font-medium">{e.nome}</div>
            <small className="block text-caption text-ink-muted">{ROTULO_DA_COBRANCA[e.cobranca]}</small>
          </div>
          {!e.ativo && (
            <StatusBadge tom="neutro" compacto>
              Desativado
            </StatusBadge>
          )}
          <span className="wl-mono">{dinheiro(e.valor_centavos)}</span>
          {e.ativo && (
            <Button compacto variante="quieto" aria-label={`Editar ${e.nome}`} onClick={() => setDialogo({ extra: e })}>
              Editar
            </Button>
          )}
        </div>
      ))}
      <button type="button" className="mt-3 self-start text-caption underline" onClick={() => setVerDesativados((v) => !v)}>
        {verDesativados ? "Esconder extras desativados" : "Mostrar extras desativados"}
      </button>
      {dialogo && (
        <DialogoDoExtra
          extra={dialogo.extra}
          aoFechar={() => setDialogo(null)}
          aoConcluir={(aviso) => {
            setDialogo(null);
            aoAvisar(aviso);
          }}
        />
      )}
    </section>
  );
}
