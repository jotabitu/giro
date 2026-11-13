"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { Button, Dialogo, Icone, StatusBadge, TextField } from "@/design-system";
import { precos as api, type PlanoDeCompra } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { reaisDoCentavos, ROTULO_DA_PERIODICIDADE } from "@/lib/precos";
import { centavosDoTexto } from "@/lib/veiculos";

// Referência: "Planos de compra" em docs/telas/html/Precos-Desktop.dc.html e Precos-Mobile.dc.html (LOC-16, T-420).
// A última parcela (com a caução abatida) e a caução vêm da API; a tela não calcula.

const PERIODICIDADES = [
  { valor: "mensal", rotulo: "Mensal" },
  { valor: "semanal", rotulo: "Semanal" },
] as const;

const locacoes = (n: number) => `${n} ${n === 1 ? "ativa" : "ativas"}`;

function DialogoDoPlanoDeCompra({ plano, aoFechar, aoConcluir }: { plano: PlanoDeCompra | null; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cliente = useQueryClient();
  const categorias = useQuery({ queryKey: ["precos", "categorias", "todas"], queryFn: () => api.categorias() });
  const [nome, setNome] = useState(plano?.nome ?? "");
  const [categoria, setCategoria] = useState(plano ? String(plano.categoria.id) : "");
  const [periodicidade, setPeriodicidade] = useState<"mensal" | "semanal">(plano?.periodicidade ?? "mensal");
  const [parcelas, setParcelas] = useState(plano ? String(plano.parcelas) : "");
  const [valor, setValor] = useState(plano ? reaisDoCentavos(plano.valor_parcela_centavos) : "");
  const [condicoes, setCondicoes] = useState(plano?.condicoes ?? "");
  const [erroLocal, setErroLocal] = useState<string | null>(null);

  const salvar = useMutation({
    mutationFn: async () => {
      const centavos = centavosDoTexto(valor);
      if (centavos === null) {
        setErroLocal("Informe um valor em reais, como 1.190,00.");
        throw new Error("valor");
      }
      setErroLocal(null);
      const corpo = { nome, categoria_id: Number(categoria), periodicidade, parcelas: Number(parcelas), valor_parcela_centavos: centavos, condicoes };
      return plano ? api.alterarPlanoDeCompra(plano.id, corpo) : api.criarPlanoDeCompra(corpo);
    },
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["precos", "planos-compra"] }), cliente.invalidateQueries({ queryKey: ["planos-compra"] })]);
      aoConcluir(plano ? "Plano de compra salvo. A mudança vale para locações novas." : "Plano de compra criado.");
    },
  });
  const desativar = useMutation({
    mutationFn: () => api.desativarPlanoDeCompra(plano!.id),
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["precos", "planos-compra"] }), cliente.invalidateQueries({ queryKey: ["planos-compra"] })]);
      aoConcluir("Plano de compra desativado. Quem já confirmou mantém o plano.");
    },
  });
  const trabalhando = salvar.isPending || desativar.isPending;
  const erro = erroLocal ? null : salvar.error;
  const completo = !!nome.trim() && !!categoria && !!parcelas && !!valor.trim();

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={plano ? `Editar ${plano.nome}` : "Novo plano de compra"}
      descricao="A mudança vale para locações novas. Quem já confirmou mantém o plano."
      fecharAoClicarFora={false}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={trabalhando || !completo} onClick={() => salvar.mutate()}>
            {salvar.isPending ? "Salvando…" : "Salvar"}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!trabalhando && completo) salvar.mutate();
        }}
      >
        <TextField cheio rotulo="Nome do plano" value={nome} onChange={(e) => setNome(e.target.value)} erro={campoDoErro(erro, "nome")} autoFocus />
        <CampoSelecao
          rotulo="Categoria"
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          vazio={categorias.isPending ? "Carregando…" : "Escolha a categoria"}
          opcoes={(categorias.data ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome }))}
          erro={categorias.isError ? mensagemDoErro(categorias.error) : campoDoErro(erro, "categoria_id")}
        />
        <CampoSelecao rotulo="Periodicidade" value={periodicidade} onChange={(e) => setPeriodicidade(e.target.value as "mensal" | "semanal")} opcoes={PERIODICIDADES.map((p) => ({ valor: p.valor, rotulo: p.rotulo }))} erro={campoDoErro(erro, "periodicidade")} />
        <div className="grid grid-cols-2 gap-3">
          <TextField cheio rotulo="Parcelas" mono inputMode="numeric" autoComplete="off" value={parcelas} onChange={(e) => setParcelas(e.target.value.replace(/\D/g, ""))} erro={campoDoErro(erro, "parcelas")} />
          <TextField cheio rotulo="Valor da parcela" mono inputMode="decimal" autoComplete="off" value={valor} onChange={(e) => setValor(e.target.value)} erro={erroLocal ?? campoDoErro(erro, "valor_parcela_centavos")} />
        </div>
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

/** Painel "Planos de compra" (LOC-16): o administrador cria, edita e desativa; a locação com intenção de compra escolhe um deles. */
export function PlanosDeCompra({ aoAvisar }: { aoAvisar: (aviso: string) => void }) {
  const [verDesativados, setVerDesativados] = useState(false);
  const [dialogo, setDialogo] = useState<{ plano: PlanoDeCompra | null } | null>(null);
  const consulta = useQuery({ queryKey: ["precos", "planos-compra", verDesativados], queryFn: () => api.planosDeCompra({ ativo: verDesativados ? "todos" : true }) });
  const lista = consulta.data ?? [];

  return (
    <section className="wl-panel" aria-label="Planos de compra">
      <div className="wl-panel__head">
        <h2 className="wl-panel__title">Planos de compra</h2>
        <Button compacto icone={<Icone de={Plus} />} onClick={() => setDialogo({ plano: null })}>
          Plano de compra
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
      {consulta.isSuccess && lista.length === 0 && <p className="m-0 text-body text-ink-muted">Nenhum plano de compra.</p>}
      {lista.map((p) => (
        <div key={p.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line py-3.5 last:border-b-0">
          <div className="min-w-0 flex-[1_1_220px]">
            <div className="font-medium">{p.nome}</div>
            <small className="block text-caption text-ink-muted">{p.categoria.nome}</small>
          </div>
          {!p.ativo && (
            <StatusBadge tom="neutro" compacto>
              Desativado
            </StatusBadge>
          )}
          <div className="text-caption text-ink-muted">
            {ROTULO_DA_PERIODICIDADE[p.periodicidade]} · {p.parcelas} parcelas
          </div>
          <div className="wl-mono">{dinheiro(p.valor_parcela_centavos)}</div>
          <div className="text-caption text-ink-muted">
            Última {dinheiro(p.ultima_parcela_centavos)} com a caução de {dinheiro(p.caucao_centavos)} abatida
          </div>
          <div className="text-caption text-ink-muted">{locacoes(p.locacoes_ativas)}</div>
          {p.ativo && (
            <Button compacto variante="quieto" aria-label={`Editar ${p.nome}`} onClick={() => setDialogo({ plano: p })}>
              Editar
            </Button>
          )}
        </div>
      ))}
      <p className="m-0 mt-3 text-caption text-ink-muted">Mudar ou desativar um plano vale só para locações novas. Quem já confirmou mantém o plano.</p>
      <button type="button" className="mt-3 self-start text-caption underline" onClick={() => setVerDesativados((v) => !v)}>
        {verDesativados ? "Esconder planos desativados" : "Mostrar planos desativados"}
      </button>
      {dialogo && (
        <DialogoDoPlanoDeCompra
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
