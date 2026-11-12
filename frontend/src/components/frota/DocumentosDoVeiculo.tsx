"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Panel, StatusBadge, TextField } from "@/design-system";
import { ErroApi, veiculos, type DocumentoVeiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta } from "@/lib/formatos";
import { situacaoDoDocumento } from "@/lib/frota";
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

function SituacaoDoDocumento({ d }: { d: DocumentoVeiculo }) {
  const s = situacaoDoDocumento(d.situacao, d.dias_para_vencer, d.situacao_rotulo);
  return (
    <StatusBadge tom={s.tom} compacto>
      {s.rotulo}
    </StatusBadge>
  );
}

function Linha({ id, tipo, rotulo, atual }: { id: number; tipo: string; rotulo: string; atual?: DocumentoVeiculo }) {
  const cliente = useQueryClient();
  const seletor = useRef<HTMLInputElement>(null);
  // O seletor nativo do navegador fica escondido atrás do botão (o texto dele sai no idioma do navegador).
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [validade, setValidade] = useState("");
  const [exercicio, setExercicio] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [erroValidade, setErroValidade] = useState<string | undefined>();
  const [feito, setFeito] = useState(false);

  const enviar = useMutation({
    mutationFn: () => veiculos.enviarDocumento(id, { tipo, validade, exercicio: tipo === "crlv" ? exercicio : undefined, arquivo: arquivo ?? undefined }),
    onSuccess: async () => {
      setFeito(true);
      limpar();
      await Promise.all([cliente.invalidateQueries({ queryKey: ["veiculo", id, "documentos"] }), cliente.invalidateQueries({ queryKey: ["veiculo", id] }), cliente.invalidateQueries({ queryKey: ["veiculos"] })]);
    },
  });

  function limpar() {
    setArquivo(null);
    setValidade("");
    setExercicio("");
    setErro(null);
    setErroValidade(undefined);
    if (seletor.current) seletor.current.value = "";
  }

  function escolheu(f: File | undefined) {
    setFeito(false);
    setErro(null);
    if (!f) return;
    if (f.size > LIMITE_MB * 1024 * 1024) {
      if (seletor.current) seletor.current.value = "";
      return setErro(`O arquivo passa de ${LIMITE_MB} MB.`);
    }
    setArquivo(f);
  }

  function confirmar() {
    setErro(null);
    setErroValidade(undefined);
    if (!validade) return setErroValidade("Informe a validade");
    enviar.mutate(undefined, {
      onError: (e) => {
        if (e instanceof ErroApi && e.campos?.validade) setErroValidade(e.campos.validade);
        else setErro(mensagemDoErro(e));
      },
    });
  }

  return (
    <li className="flex min-w-0 flex-col gap-3 rounded-lg border border-line p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="font-semibold">{rotulo}</div>
          <div className="text-caption text-ink-muted">{atual ? (atual.validade ? `Vale até ${dataCurta(atual.validade)}` : "Em uso, sem validade") : "Nenhum cadastrado"}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {atual && <SituacaoDoDocumento d={atual} />}
          {atual && <AbrirDocumento d={atual} />}
        </div>
      </div>
      <input ref={seletor} type="file" accept={ACEITOS} className="hidden" aria-label={`Escolher o arquivo de ${rotulo}`} onChange={(e) => escolheu(e.target.files?.[0])} />
      {!arquivo ? (
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => seletor.current?.click()} className="wl-btn wl-btn--quiet wl-btn--sm">
            {atual ? "Substituir" : "Enviar"}
          </button>
          <span className="text-caption text-ink-muted">PDF, JPG ou PNG, até {LIMITE_MB} MB</span>
        </div>
      ) : (
        <div className="flex min-w-0 flex-col gap-3">
          <span className="wl-mono min-w-0 break-all text-caption">{arquivo.name}</span>
          <TextField cheio mono type="date" rotulo="Nova validade" value={validade} onChange={(e) => setValidade(e.target.value)} erro={erroValidade} />
          {tipo === "crlv" && <TextField cheio mono rotulo="Ano do licenciamento" inputMode="numeric" maxLength={4} dica="Opcional" value={exercicio} onChange={(e) => setExercicio(e.target.value)} />}
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={enviar.isPending} onClick={confirmar} className="wl-btn wl-btn--solid wl-btn--sm">
              {enviar.isPending ? "Enviando…" : atual ? "Substituir documento" : "Enviar documento"}
            </button>
            <button type="button" disabled={enviar.isPending} onClick={limpar} className="wl-btn wl-btn--quiet wl-btn--sm">
              Cancelar
            </button>
          </div>
        </div>
      )}
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
    <Panel titulo="Documentos" subtitulo="Substitua arquivos ou atualize validades.">
      {docs.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(docs.error)}
        </p>
      )}
      {docs.isPending && <p className="text-body text-ink-muted">Carregando os documentos…</p>}
      {docs.data && (
        <ul className="m-0 grid list-none gap-4 p-0 md:grid-cols-2">
          {TIPOS.map((t) => (
            <Linha key={t.tipo} id={id} tipo={t.tipo} rotulo={t.rotulo} atual={docs.data.find((d) => d.tipo === t.tipo)} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
