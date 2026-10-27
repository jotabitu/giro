"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button, Dialogo, Icone, StatusBadge, TextField } from "@/design-system";
import { precos as api, type PeriodicidadeDoPlano, type PlanoEspecialDePreco, type RegraDoPlano } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { centavosDoTexto } from "@/lib/veiculos";
import { contratos, reaisDoCentavos, ROTULO_DA_PERIODICIDADE, valorDoPlano } from "@/lib/precos";

const PERIODICIDADES: PeriodicidadeDoPlano[] = ["diaria", "semanal", "mensal"];
const REGRAS: { valor: RegraDoPlano; rotulo: string }[] = [
  { valor: "preco_fixo", rotulo: "Preço fixo" },
  { valor: "desconto", rotulo: "Desconto" },
];

function Opcoes<V extends string>({ rotulo, opcoes, valor, aoMudar }: { rotulo: string; opcoes: { valor: V; rotulo: string }[]; valor: V; aoMudar: (v: V) => void }) {
  const id = `plano-${rotulo.replace(/\s/g, "-").toLowerCase()}`;
  return (
    <div className="wl-field">
      <span className="wl-field__label" id={id}>
        {rotulo}
      </span>
      <div role="radiogroup" aria-labelledby={id} className="grid grid-flow-col auto-cols-fr gap-2">
        {opcoes.map((o) => (
          <button
            key={o.valor}
            type="button"
            role="radio"
            aria-checked={valor === o.valor}
            onClick={() => aoMudar(o.valor)}
            className={`rounded-md px-3 py-2.5 text-body font-medium ${valor === o.valor ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
          >
            {o.rotulo}
          </button>
        ))}
      </div>
    </div>
  );
}

function DialogoDoPlano({ plano, aoFechar, aoConcluir }: { plano: PlanoEspecialDePreco | null; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cliente = useQueryClient();
  const [nome, setNome] = useState(plano?.nome ?? "");
  const [periodicidade, setPeriodicidade] = useState<PeriodicidadeDoPlano>((plano?.periodicidade as PeriodicidadeDoPlano) ?? "semanal");
  const [regra, setRegra] = useState<RegraDoPlano>((plano?.regra as RegraDoPlano) ?? "preco_fixo");
  const [preco, setPreco] = useState(plano?.preco_centavos != null ? reaisDoCentavos(plano.preco_centavos) : "");
  const [desconto, setDesconto] = useState(plano?.desconto_pct ?? "");
  const [apartir, setApartir] = useState(plano?.a_partir_do_periodo != null ? String(plano.a_partir_do_periodo) : "");
  const [condicoes, setCondicoes] = useState(plano?.condicoes ?? "");
  const [erroLocal, setErroLocal] = useState<string | null>(null);

  const salvar = useMutation({
    mutationFn: async () => {
      const base = { nome, periodicidade, regra, condicoes };
      let corpo;
      if (regra === "preco_fixo") {
        const c = centavosDoTexto(preco);
        if (c === null) {
          setErroLocal("Informe um valor em reais, como 279,00.");
          throw new Error("valor");
        }
        corpo = { ...base, preco_centavos: c, desconto_pct: null, a_partir_do_periodo: null };
      } else {
        corpo = { ...base, preco_centavos: null, desconto_pct: desconto.replace(",", "."), a_partir_do_periodo: apartir ? Number(apartir) : null };
      }
      setErroLocal(null);
      return plano ? api.alterarPlanoEspecial(plano.id, corpo) : api.criarPlanoEspecial(corpo);
    },
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["precos", "planos"] });
      aoConcluir(plano ? "Plano salvo. A mudança vale para locações novas." : "Plano criado.");
    },
  });
  const desativar = useMutation({
    mutationFn: () => api.desativarPlanoEspecial(plano!.id),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["precos", "planos"] });
      aoConcluir("Plano desativado. Quem já assinou mantém o plano.");
    },
  });
  const trabalhando = salvar.isPending || desativar.isPending;
  const erro = erroLocal ? null : salvar.error;

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={plano ? `Editar ${plano.nome}` : "Novo plano especial"}
      descricao="A mudança vale para locações novas. Quem já assinou mantém o plano da assinatura."
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
        <TextField cheio rotulo="Nome do plano" value={nome} onChange={(e) => setNome(e.target.value)} erro={campoDoErro(erro, "nome")} autoFocus />
        <Opcoes rotulo="Modalidade" valor={periodicidade} aoMudar={setPeriodicidade} opcoes={PERIODICIDADES.map((p) => ({ valor: p, rotulo: ROTULO_DA_PERIODICIDADE[p] }))} />
        <Opcoes rotulo="Regra" valor={regra} aoMudar={setRegra} opcoes={REGRAS} />
        {regra === "preco_fixo" ? (
          <TextField cheio rotulo="Preço por período" mono inputMode="decimal" autoComplete="off" value={preco} onChange={(e) => setPreco(e.target.value)} erro={erroLocal ?? campoDoErro(erro, "preco_centavos")} />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <TextField cheio rotulo="Desconto (%)" mono inputMode="decimal" autoComplete="off" value={desconto} onChange={(e) => setDesconto(e.target.value)} erro={campoDoErro(erro, "desconto_pct")} />
            <TextField cheio rotulo="A partir do período" mono inputMode="numeric" autoComplete="off" value={apartir} onChange={(e) => setApartir(e.target.value.replace(/\D/g, ""))} erro={campoDoErro(erro, "a_partir_do_periodo")} />
          </div>
        )}
        <TextField cheio rotulo="Condições" value={condicoes} onChange={(e) => setCondicoes(e.target.value)} erro={campoDoErro(erro, "condicoes")} />
        {erro && !(erro as { campos?: unknown }).campos && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(erro)}
          </p>
        )}
        {plano?.ativo && (
          <div className="border-t border-line pt-3">
            <Button compacto variante="quieto" disabled={trabalhando} onClick={() => desativar.mutate()}>
              Desativar plano
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

/** Painel "Planos especiais" (LOC-01, LOC-15): Entregador, Mensal fidelidade e os que a locadora criar. */
export function PlanosEspeciais({ aoAvisar }: { aoAvisar: (aviso: string) => void }) {
  const [verDesativados, setVerDesativados] = useState(false);
  const [dialogo, setDialogo] = useState<{ plano: PlanoEspecialDePreco | null } | null>(null);
  const consulta = useQuery({ queryKey: ["precos", "planos", verDesativados], queryFn: () => api.planosEspeciais({ ativo: verDesativados ? "todos" : true }) });
  const lista = consulta.data ?? [];

  return (
    <section className="wl-panel" aria-label="Planos especiais">
      <div className="wl-panel__head">
        <h2 className="wl-panel__title">Planos especiais</h2>
        <Button compacto icone={<Icone de={Plus} />} onClick={() => setDialogo({ plano: null })}>
          Plano
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
      {consulta.isSuccess && lista.length === 0 && <p className="m-0 text-body text-ink-muted">Nenhum plano especial.</p>}
      {lista.map((p) => (
        <div key={p.id} className="flex flex-wrap items-center gap-3 border-b border-line py-3.5 last:border-b-0">
          <div className="min-w-0 flex-1">
            <div className="font-medium">{p.nome}</div>
            <small className="block text-caption text-ink-muted">{p.condicoes}</small>
          </div>
          {!p.ativo && (
            <StatusBadge tom="neutro" compacto>
              Desativado
            </StatusBadge>
          )}
          <span className="wl-mono">{valorDoPlano(p)}</span>
          <span className="text-caption text-ink-muted">{contratos(p.locacoes_ativas)}</span>
          {p.ativo && (
            <Button compacto variante="quieto" aria-label={`Editar ${p.nome}`} onClick={() => setDialogo({ plano: p })}>
              Editar
            </Button>
          )}
        </div>
      ))}
      <button type="button" className="mt-3 self-start text-caption underline" onClick={() => setVerDesativados((v) => !v)}>
        {verDesativados ? "Esconder planos desativados" : "Mostrar planos desativados"}
      </button>
      {dialogo && (
        <DialogoDoPlano
          plano={dialogo.plano}
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
