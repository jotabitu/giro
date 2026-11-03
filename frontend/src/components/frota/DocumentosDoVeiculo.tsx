"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Panel, TextField } from "@/design-system";
import { ErroApi, veiculos, type DocumentoVeiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta } from "@/lib/formatos";
import { AbrirDocumento } from "./FichaVeiculo";

// VEI-03, AUD-05. Contrato: docs/api/veiculos.md, "Documentos". Renovar cria um documento novo e o anterior fica no histórico.

const TIPOS: { tipo: string; rotulo: string }[] = [
  { tipo: "crlv", rotulo: "CRLV" },
  { tipo: "ipva", rotulo: "IPVA" },
  { tipo: "seguro", rotulo: "Seguro" },
  { tipo: "rastreador", rotulo: "Rastreador" },
];
const LIMITE_MB = 10;
const ACEITOS = "application/pdf,image/jpeg,image/png";

function Linha({ id, tipo, rotulo, atual }: { id: number; tipo: string; rotulo: string; atual?: DocumentoVeiculo }) {
  const cliente = useQueryClient();
  const arquivo = useRef<HTMLInputElement>(null);
  const [validade, setValidade] = useState("");
  const [exercicio, setExercicio] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [erroValidade, setErroValidade] = useState<string | undefined>();
  const [feito, setFeito] = useState(false);

  const enviar = useMutation({
    mutationFn: () => {
      const f = arquivo.current?.files?.[0];
      return veiculos.enviarDocumento(id, { tipo, validade, exercicio: tipo === "crlv" ? exercicio : undefined, arquivo: f });
    },
    onSuccess: async () => {
      setFeito(true);
      setValidade("");
      setExercicio("");
      if (arquivo.current) arquivo.current.value = "";
      await Promise.all([cliente.invalidateQueries({ queryKey: ["veiculo", id, "documentos"] }), cliente.invalidateQueries({ queryKey: ["veiculo", id] }), cliente.invalidateQueries({ queryKey: ["veiculos"] })]);
    },
  });

  function substituir() {
    setErro(null);
    setErroValidade(undefined);
    setFeito(false);
    const f = arquivo.current?.files?.[0];
    if (!validade) return setErroValidade("Informe a validade");
    if (f && f.size > LIMITE_MB * 1024 * 1024) return setErro(`O arquivo passa de ${LIMITE_MB} MB.`);
    enviar.mutate(undefined, {
      onError: (e) => {
        if (e instanceof ErroApi && e.campos?.validade) setErroValidade(e.campos.validade);
        else setErro(mensagemDoErro(e));
      },
    });
  }

  return (
    <li className="flex flex-col gap-3 border-b border-line py-4 last:border-b-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="font-semibold">{rotulo}</div>
          <div className="text-caption text-ink-muted">{atual ? (atual.validade ? `Vale até ${dataCurta(atual.validade)}` : "Em uso, sem validade") : "Nenhum cadastrado"}</div>
        </div>
        {atual && <AbrirDocumento d={atual} />}
      </div>
      <div className="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)_auto] md:items-end">
        <TextField cheio mono type="date" rotulo="Nova validade" value={validade} onChange={(e) => setValidade(e.target.value)} erro={erroValidade} />
        <label className="flex flex-col gap-1 text-body">
          <span className="text-caption text-ink-muted">Arquivo (PDF, JPG ou PNG, até {LIMITE_MB} MB)</span>
          <input ref={arquivo} type="file" accept={ACEITOS} className="min-h-[44px] text-body" />
        </label>
        <button type="button" disabled={enviar.isPending} onClick={substituir} className="wl-btn wl-btn--solid min-h-[44px]">
          {enviar.isPending ? "Enviando…" : atual ? "Substituir" : "Enviar"}
        </button>
      </div>
      {tipo === "crlv" && <TextField mono rotulo="Ano do licenciamento" inputMode="numeric" maxLength={4} dica="Opcional" value={exercicio} onChange={(e) => setExercicio(e.target.value)} />}
      {erro && (
        <p role="alert" className="m-0 text-body text-critical-ink">
          {erro}
        </p>
      )}
      {feito && (
        <p role="status" className="m-0 text-body text-success-ink">
          {rotulo} atualizado. O anterior ficou no histórico.
        </p>
      )}
    </li>
  );
}

/** Seção do Editar veículo: sobe e substitui CRLV, IPVA, seguro e rastreador. Fica fora do formulário de edição (Enter não pode salvar a edição). */
export function DocumentosDoVeiculo({ id }: { id: number }) {
  const docs = useQuery({ queryKey: ["veiculo", id, "documentos"], queryFn: () => veiculos.documentos(id) });
  return (
    <Panel titulo="Documentos">
      {docs.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(docs.error)}
        </p>
      )}
      {docs.isPending && <p className="text-body text-ink-muted">Carregando os documentos…</p>}
      {docs.data && (
        <ul className="m-0 list-none p-0">
          {TIPOS.map((t) => (
            <Linha key={t.tipo} id={id} tipo={t.tipo} rotulo={t.rotulo} atual={docs.data.find((d) => d.tipo === t.tipo)} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
