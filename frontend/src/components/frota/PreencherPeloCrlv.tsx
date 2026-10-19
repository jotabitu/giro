"use client";

import { useMutation } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { useRef } from "react";
import { Icone } from "@/design-system";
import { ErroApi, veiculos, type LeituraCrlv } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";

export type CrlvLido = { arquivo: File; leitura: LeituraCrlv };

/** A recusa 400 diz o problema no campo `arquivo`; 422, 429 e 503 trazem a mensagem pronta (VEI-08). */
export function mensagemDaLeitura(e: unknown): string {
  if (e instanceof ErroApi && e.status === 400 && e.campos?.arquivo) return e.campos.arquivo;
  return mensagemDoErro(e);
}

/**
 * "Preencher pelo documento" (Veiculo-Novo-Desktop|Mobile): envia o PDF do CRLV-e para `POST /api/veiculos/leitura-crlv/`
 * e devolve o que a API leu. A leitura não grava nada: a pessoa confere os campos e salva (VEI-08).
 */
export function PreencherPeloCrlv({ lido, aoLer, aoRemover }: { lido: CrlvLido | null; aoLer: (l: CrlvLido) => void; aoRemover: () => void }) {
  const entrada = useRef<HTMLInputElement>(null);
  const ler = useMutation({ mutationFn: (arquivo: File) => veiculos.lerCrlv(arquivo).then((leitura) => ({ arquivo, leitura })) });

  function escolher(arquivo: File | undefined) {
    if (!arquivo || ler.isPending) return;
    ler.mutate(arquivo, { onSuccess: aoLer });
  }

  return (
    <section className="wl-panel flex flex-wrap items-center gap-4" aria-busy={ler.isPending}>
      <div className="grid h-[52px] w-[52px] flex-none place-items-center rounded-lg bg-surface-sunken text-ink-muted">
        <Icone de={FileText} />
      </div>
      <div className="min-w-0 flex-1 basis-64">
        <div className="text-body font-semibold">Preencher pelo documento</div>
        <p className="text-body text-ink-muted">Envie o PDF do CRLV-e e preenchemos placa, chassi, renavam, ano, cor e modelo. Confira antes de salvar.</p>
        {lido?.leitura.dicas.marca_modelo && (
          <p className="mt-1 text-body text-ink-muted">
            No documento: <span className="wl-mono">{lido.leitura.dicas.marca_modelo}</span>. Escolha a marca e o modelo da lista abaixo.
          </p>
        )}
        {ler.isError && (
          <p role="alert" className="mt-2 text-body text-critical-ink">
            {mensagemDaLeitura(ler.error)}
          </p>
        )}
      </div>
      <input
        ref={entrada}
        type="file"
        accept=".pdf,application/pdf"
        className="sr-only"
        tabIndex={-1}
        aria-label="Arquivo do CRLV-e"
        onChange={(e) => {
          escolher(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {lido && !ler.isPending && <span className="wl-badge wl-badge--success">{lido.leitura.rotulo}</span>}
      {ler.isPending && (
        <span role="status" className="text-body text-ink-muted">
          Lendo o documento…
        </span>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" disabled={ler.isPending} onClick={() => entrada.current?.click()} className="wl-btn">
          {lido ? "Trocar o CRLV-e" : "Enviar CRLV-e"}
        </button>
        {lido && (
          <button
            type="button"
            disabled={ler.isPending}
            onClick={() => {
              ler.reset();
              aoRemover();
            }}
            className="wl-btn wl-btn--quiet"
          >
            Remover o CRLV-e
          </button>
        )}
      </div>
    </section>
  );
}
