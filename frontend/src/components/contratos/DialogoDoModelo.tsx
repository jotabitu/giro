"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { modelosContrato as api, type ModeloDeContrato } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { inserirMarcador } from "@/lib/contratos";

export type DialogoDoModeloProps = {
  modelo: ModeloDeContrato;
  aoFechar: () => void;
  aoConcluir: (aviso: string) => void;
};

/** Edita nome e texto de um modelo, com os campos automáticos da lista fechada (S-09). Editar um publicado cria o rascunho da versão seguinte (LOC-15). */
export function DialogoDoModelo({ modelo, aoFechar, aoConcluir }: DialogoDoModeloProps) {
  const cliente = useQueryClient();
  const area = useRef<HTMLTextAreaElement>(null);
  const [nome, setNome] = useState(modelo.nome);
  const [texto, setTexto] = useState(modelo.texto);
  const marcadores = useQuery({ queryKey: ["contratos", "marcadores"], queryFn: () => api.marcadores(), staleTime: 10 * 60_000 });

  const salvar = useMutation({
    mutationFn: () => api.alterar(modelo.id, { nome, texto }),
    onSuccess: async (m) => {
      await cliente.invalidateQueries({ queryKey: ["contratos"] });
      aoConcluir(modelo.status === "publicado" && !modelo.tem_rascunho ? `Rascunho da versão ${(m.versao_publicada ?? 0) + 1} salvo. A versão em uso não mudou.` : "Rascunho salvo.");
    },
  });

  function inserir(chave: string) {
    const a = area.current;
    const r = inserirMarcador(texto, chave, a?.selectionStart ?? texto.length, a?.selectionEnd ?? texto.length);
    setTexto(r.texto);
    // O cursor volta para depois do marcador inserido, no próximo quadro.
    requestAnimationFrame(() => {
      a?.focus();
      a?.setSelectionRange(r.cursor, r.cursor);
    });
  }

  const erroDoTexto = campoDoErro(salvar.error, "texto");
  const erroGeral = salvar.isError && !erroDoTexto && !campoDoErro(salvar.error, "nome");

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={`Editar ${modelo.nome}`}
      descricao="Contratos já assinados continuam com o texto da versão em que foram assinados."
      fecharAoClicarFora={false}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={salvar.isPending || !nome.trim() || !texto.trim()} onClick={() => salvar.mutate()}>
            {salvar.isPending ? "Salvando…" : "Salvar rascunho"}
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
        <TextField cheio rotulo="Nome do modelo" value={nome} onChange={(e) => setNome(e.target.value)} erro={campoDoErro(salvar.error, "nome")} />
        <div className={`wl-field wl-field--cheio ${erroDoTexto ? "wl-field--error" : ""}`}>
          <label className="wl-field__label" htmlFor="texto-do-modelo">
            Texto do contrato
          </label>
          <textarea
            id="texto-do-modelo"
            ref={area}
            className="wl-input wl-mono h-auto min-h-[220px] w-full resize-y py-3"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            aria-invalid={erroDoTexto ? true : undefined}
            spellCheck={false}
          />
          <span className="wl-field__hint">{erroDoTexto ?? "Use os campos automáticos no formato {{grupo.campo}}. Só títulos, parágrafos, listas, tabelas e destaques são mantidos."}</span>
        </div>
        <section aria-label="Campos automáticos" className="flex flex-col gap-2">
          <h3 className="m-0 text-body font-semibold">Campos automáticos</h3>
          {marcadores.isPending && <p className="m-0 text-caption text-ink-muted">Carregando…</p>}
          {marcadores.isError && <p className="m-0 text-caption text-ink-muted">{mensagemDoErro(marcadores.error)}</p>}
          {marcadores.data && (
            <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
              {marcadores.data.map((m) => (
                <button
                  key={m.chave}
                  type="button"
                  title={`${m.rotulo} · ${m.exemplo}`}
                  aria-label={`Inserir ${m.rotulo}`}
                  className="wl-mono rounded-full bg-surface-sunken px-2.5 py-1 text-caption"
                  onClick={() => inserir(m.chave)}
                >
                  {m.chave}
                </button>
              ))}
            </div>
          )}
        </section>
        {erroGeral && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(salvar.error)}
          </p>
        )}
      </form>
    </Dialogo>
  );
}
