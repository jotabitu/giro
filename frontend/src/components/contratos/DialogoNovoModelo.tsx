"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { modelosContrato as api, type ModeloDeContrato } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";

const EM_BRANCO = "em_branco";

/** Novo modelo a partir de um dos prontos ou em branco. Nasce como rascunho; publicar é um passo à parte. */
export function DialogoNovoModelo({ aoFechar, aoCriar }: { aoFechar: () => void; aoCriar: (modelo: ModeloDeContrato) => void }) {
  const cliente = useQueryClient();
  const prontos = useQuery({ queryKey: ["contratos", "prontos"], queryFn: () => api.prontos(), staleTime: 10 * 60_000 });
  const [escolhido, setEscolhido] = useState<string>(EM_BRANCO);
  const [nome, setNome] = useState("");

  const criar = useMutation({
    mutationFn: () => {
      const pronto = prontos.data?.find((p) => p.chave === escolhido);
      const nomeFinal = nome.trim() || pronto?.nome || "";
      return escolhido === EM_BRANCO ? api.criar({ nome: nomeFinal, finalidade: "locacao", texto: "<p></p>" }) : api.criar({ nome: nomeFinal, finalidade: "locacao", a_partir_de: escolhido });
    },
    onSuccess: async (m) => {
      await cliente.invalidateQueries({ queryKey: ["contratos"] });
      aoCriar(m);
    },
  });

  const opcoes = [{ chave: EM_BRANCO, nome: "Em branco" }, ...(prontos.data ?? [])];
  const pronto = prontos.data?.find((p) => p.chave === escolhido);

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo="Novo modelo"
      descricao="Comece por um modelo pronto ou em branco. Ele fica como rascunho até você publicar."
      fecharAoClicarFora={false}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={criar.isPending || (escolhido === EM_BRANCO && !nome.trim())} onClick={() => criar.mutate()}>
            {criar.isPending ? "Criando…" : "Criar modelo"}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
        }}
      >
        <div className="wl-field">
          <span className="wl-field__label" id="modelo-pronto">
            Ponto de partida
          </span>
          <div role="radiogroup" aria-labelledby="modelo-pronto" className="flex flex-col gap-2">
            {opcoes.map((o) => (
              <button
                key={o.chave}
                type="button"
                role="radio"
                aria-checked={escolhido === o.chave}
                onClick={() => setEscolhido(o.chave)}
                className={`rounded-[16px] bg-surface px-3.5 py-3 text-left text-body ${escolhido === o.chave ? "ring-2 ring-ink ring-inset" : "ring-1 ring-line ring-inset"}`}
              >
                {o.nome}
              </button>
            ))}
          </div>
          {prontos.isPending && <span className="wl-field__hint">Carregando os modelos prontos…</span>}
          {prontos.isError && <span className="wl-field__hint">{mensagemDoErro(prontos.error)}</span>}
        </div>
        <TextField cheio rotulo="Nome do modelo" dica={pronto ? `Se deixar vazio, usa "${pronto.nome}".` : undefined} value={nome} onChange={(e) => setNome(e.target.value)} erro={campoDoErro(criar.error, "nome")} />
        {criar.isError && !campoDoErro(criar.error, "nome") && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(criar.error)}
          </p>
        )}
      </form>
    </Dialogo>
  );
}
