"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { precos as api, ErroApi, type CategoriaDePreco, type TipoDaCategoria } from "@/lib/api";
import { useAmbiente } from "@/lib/ambiente";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCurta, dinheiro } from "@/lib/formatos";
import { avisoDePrecoGravado, CAMPOS_DE_PRECO, precoDosTextos, precoIgual, textosDoPreco, type ChaveDePreco, type TextosDePreco } from "@/lib/precos";
import { CampoDeDinheiro } from "./CampoDeDinheiro";

export type DialogoDaCategoriaProps = {
  /** `null` cria uma categoria; com categoria, edita nome, tipo e preço. */
  categoria: CategoriaDePreco | null;
  /** Filial a que a categoria nova pertence; `null` é da empresa toda (FIL-04). */
  filialId?: number | null;
  aoFechar: () => void;
  /** Depois de gravar, com o texto do aviso (LOC-15). */
  aoConcluir: (aviso: string) => void;
};

const TIPOS: { valor: TipoDaCategoria; rotulo: string }[] = [
  { valor: "moto", rotulo: "Moto" },
  { valor: "carro", rotulo: "Carro" },
];

const ERRO_LOCAL = "validacao_local";

function Historico({ id }: { id: number }) {
  const consulta = useQuery({ queryKey: ["precos", "categoria", id], queryFn: () => api.historicoDaCategoria(id) });
  if (consulta.isPending) return <p className="m-0 text-caption text-ink-muted">Carregando o histórico…</p>;
  if (consulta.isError) return <p className="m-0 text-caption text-ink-muted">{mensagemDoErro(consulta.error)}</p>;
  return (
    <ol className="m-0 flex list-none flex-col gap-1.5 p-0" aria-label="Histórico de preços da categoria">
      {consulta.data.map((p) => (
        <li key={p.vigente_desde} className="flex flex-wrap justify-between gap-x-3 text-caption">
          <span>
            <b className="font-medium">A partir de {dataCurta(p.vigente_desde)}</b>
            <span className="text-ink-muted"> · {p.alterado_por ?? "Sistema"}</span>
          </span>
          <span className="wl-mono text-ink-muted">
            {dinheiro(p.diaria_centavos)} · {dinheiro(p.semanal_centavos)} · {dinheiro(p.mensal_centavos)} · caução {dinheiro(p.caucao_centavos)}
          </span>
        </li>
      ))}
    </ol>
  );
}

/** Nova categoria ou edição de nome, tipo e preço. O preço novo só vale para contratos novos (LOC-15). */
export function DialogoDaCategoria({ categoria, filialId = null, aoFechar, aoConcluir }: DialogoDaCategoriaProps) {
  const cliente = useQueryClient();
  const hoje = useAmbiente()?.hoje ?? new Date().toISOString().slice(0, 10);
  const vigente = categoria?.preco_vigente ?? null;
  const [nome, setNome] = useState(categoria?.nome ?? "");
  const [tipo, setTipo] = useState<TipoDaCategoria>(categoria?.tipo_veiculo ?? "moto");
  const [textos, setTextos] = useState<TextosDePreco>(textosDoPreco(categoria?.proximo_preco ?? vigente));
  const [desde, setDesde] = useState(categoria?.proximo_preco?.vigente_desde ?? hoje);
  const [errosLocais, setErrosLocais] = useState<Partial<Record<ChaveDePreco, string>>>({});

  const salvar = useMutation({
    mutationFn: async (): Promise<string> => {
      const lidos = precoDosTextos(textos);
      if ("erros" in lidos) {
        setErrosLocais(lidos.erros);
        throw new ErroApi(0, ERRO_LOCAL, "Confira os valores.");
      }
      setErrosLocais({});
      const preco = lidos.preco;
      if (!categoria) {
        await api.criarCategoria({ nome, tipo_veiculo: tipo, filial_id: filialId, preco });
        return "Categoria criada com o primeiro preço.";
      }
      let aviso = "Categoria salva.";
      if (nome.trim() !== categoria.nome || tipo !== categoria.tipo_veiculo) {
        await api.alterarCategoria(categoria.id, { nome, tipo_veiculo: tipo });
      }
      const atual = categoria.proximo_preco ?? vigente;
      const mudouPreco = !atual || !precoIgual(preco, atual) || desde !== (categoria.proximo_preco?.vigente_desde ?? hoje);
      if (mudouPreco) {
        // Preço já agendado para esta data se troca por PUT; os outros casos são preço novo (POST).
        const gravado =
          categoria.proximo_preco && categoria.proximo_preco.vigente_desde === desde
            ? await api.trocarPrecoAgendado(categoria.id, desde, { ...preco, vigente_desde: desde })
            : await api.definirPreco(categoria.id, { ...preco, vigente_desde: desde });
        aviso = avisoDePrecoGravado(gravado.locacoes_em_andamento_mantidas);
      }
      return aviso;
    },
    onSuccess: async (aviso) => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["precos"] }), cliente.invalidateQueries({ queryKey: ["categorias"] })]);
      aoConcluir(aviso);
    },
  });

  const alternar = useMutation({
    mutationFn: () => (categoria!.ativo ? api.desativarCategoria(categoria!.id) : api.reativarCategoria(categoria!.id)),
    onSuccess: async (c) => {
      await cliente.invalidateQueries({ queryKey: ["precos"] });
      aoConcluir(c.ativo ? "Categoria reativada." : "Categoria desativada. Ela sai da escolha em cadastros novos.");
    },
  });

  const erro = salvar.error instanceof ErroApi && salvar.error.codigo === ERRO_LOCAL ? null : salvar.error;
  const trabalhando = salvar.isPending || alternar.isPending;
  const comVeiculos = (categoria?.veiculos ?? 0) > 0;
  const erroDoCampo = (k: ChaveDePreco) => errosLocais[k] ?? campoDoErro(erro, k);
  const erroGeral = erro && !(erro instanceof ErroApi && erro.campos);

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={categoria ? `Editar ${categoria.nome}` : "Nova categoria"}
      descricao="Mudanças de preço valem só para contratos novos. Quem já assinou mantém o preço da assinatura."
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
        <TextField cheio rotulo="Nome da categoria" value={nome} onChange={(e) => setNome(e.target.value)} erro={campoDoErro(erro, "nome")} autoFocus />
        <div className="wl-field">
          <span className="wl-field__label" id="tipo-da-categoria">
            Tipo de veículo
          </span>
          <div role="radiogroup" aria-labelledby="tipo-da-categoria" className="grid grid-cols-2 gap-2">
            {TIPOS.map((t) => (
              <button
                key={t.valor}
                type="button"
                role="radio"
                aria-checked={tipo === t.valor}
                disabled={comVeiculos}
                onClick={() => setTipo(t.valor)}
                className={`rounded-md px-3 py-2.5 text-body font-medium ${tipo === t.valor ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
              >
                {t.rotulo}
              </button>
            ))}
          </div>
          {comVeiculos && <span className="wl-field__hint">O tipo não muda enquanto há veículos na categoria. Ele define a CNH exigida.</span>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          {CAMPOS_DE_PRECO.map(({ chave, rotulo }) => (
            <CampoDeDinheiro key={chave} rotulo={rotulo} valor={textos[chave]} aoMudar={(v) => setTextos((t) => ({ ...t, [chave]: v }))} erro={erroDoCampo(chave)} />
          ))}
        </div>
        {categoria && (
          <label className="wl-field wl-field--cheio">
            <span className="wl-field__label">Vale a partir de</span>
            <input className="wl-input" type="date" min={hoje} value={desde} onChange={(e) => setDesde(e.target.value)} />
            {campoDoErro(erro, "vigente_desde") && <span className="wl-field__hint">{campoDoErro(erro, "vigente_desde")}</span>}
          </label>
        )}
        {erroGeral && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(erro)}
          </p>
        )}
        {categoria && (
          <section aria-label="Histórico" className="flex flex-col gap-2 border-t border-line pt-3">
            <h3 className="m-0 text-body font-semibold">Histórico de preços</h3>
            <Historico id={categoria.id} />
          </section>
        )}
        {categoria && (
          <div className="flex flex-col gap-2 border-t border-line pt-3">
            <Button compacto variante="quieto" disabled={trabalhando} onClick={() => alternar.mutate()}>
              {categoria.ativo ? "Desativar categoria" : "Reativar categoria"}
            </Button>
            {alternar.isError && (
              <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
                {mensagemDoErro(alternar.error)}
              </p>
            )}
          </div>
        )}
      </form>
    </Dialogo>
  );
}
