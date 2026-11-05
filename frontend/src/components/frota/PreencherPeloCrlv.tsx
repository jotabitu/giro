"use client";

import { useMutation } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { useRef, useState } from "react";
import { Icone } from "@/design-system";
import { ErroApi, veiculos, type LeituraCrlv, type LeituraCrlvNoEditar, type ModeloDoCatalogo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";

export type CrlvLido = { arquivo: File; leitura: LeituraCrlv | LeituraCrlvNoEditar };

/** A recusa 400 diz o problema no campo `arquivo`; 422, 429 e 503 trazem a mensagem pronta (VEI-08). */
export function mensagemDaLeitura(e: unknown): string {
  if (e instanceof ErroApi && e.status === 400 && e.campos?.arquivo) return e.campos.arquivo;
  return mensagemDoErro(e);
}

/**
 * "Preencher pelo documento" (Veiculo-Novo-Desktop|Mobile): envia o PDF do CRLV-e para `POST /api/veiculos/leitura-crlv/`
 * e devolve o que a API leu. A leitura não grava nada: a pessoa confere os campos e salva (VEI-08).
 */
export function PreencherPeloCrlv({
  lido,
  aoLer,
  aoRemover,
  aoEscolherVersao,
  veiculoId,
}: {
  lido: CrlvLido | null;
  aoLer: (l: CrlvLido) => void;
  aoRemover: () => void;
  /** T-415: a pessoa escolheu uma das versões que a API achou no catálogo; quem usa preenche marca e modelo. */
  aoEscolherVersao?: (versao: ModeloDoCatalogo) => void;
  /** T-421 (padrão A): no editar, lê pelo veículo. A placa e o chassi são conferidos e não mudam; a 422 `crlv_outro_veiculo` sobe como vem. */
  veiculoId?: number;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [versao, setVersao] = useState<string | null>(null);
  const ler = useMutation({ mutationFn: (arquivo: File) => (veiculoId != null ? veiculos.lerCrlvDoVeiculo(veiculoId, arquivo) : veiculos.lerCrlv(arquivo)).then((leitura) => ({ arquivo, leitura })) });

  function escolher(arquivo: File | undefined) {
    if (!arquivo || ler.isPending) return;
    setVersao(null);
    ler.mutate(arquivo, { onSuccess: aoLer });
  }

  return (
    <section className="wl-panel flex flex-wrap items-center gap-4" aria-busy={ler.isPending}>
      <div className="grid h-[52px] w-[52px] flex-none place-items-center rounded-lg bg-surface-sunken text-ink-muted">
        <Icone de={FileText} />
      </div>
      <div className="min-w-0 flex-1 basis-64">
        <div className="text-body font-semibold">Preencher pelo documento</div>
        <p className="text-body text-ink-muted">
          {veiculoId != null
            ? "Envie o PDF do CRLV-e e preenchemos renavam, ano, cor, modelo e os dados do documento. Placa e chassi não mudam. Confira antes de salvar."
            : "Envie o PDF do CRLV-e e preenchemos placa, chassi, renavam, ano, cor, modelo e os dados do documento. Confira antes de salvar."}
        </p>
        {lido?.leitura.dicas.marca_modelo && (
          <p className="mt-1 text-body text-ink-muted">
            No documento: <span className="wl-mono">{lido.leitura.dicas.marca_modelo}</span>.{" "}
            {lido.leitura.dicas.candidatos.length > 0 ? "Escolha a versão:" : "Escolha a marca e o modelo da lista abaixo."}
          </p>
        )}
        {lido && lido.leitura.dicas.candidatos.length > 0 && (
          <ul aria-label="Versões que batem com o documento" className="m-0 mt-2 flex list-none flex-col gap-2 p-0">
            {lido.leitura.dicas.candidatos.map((c) => {
              const chave = `${c.marca}|${c.modelo}`;
              const escolhida = versao === chave;
              return (
                <li key={chave}>
                  <button
                    type="button"
                    aria-pressed={escolhida}
                    onClick={() => {
                      setVersao(chave);
                      aoEscolherVersao?.(c);
                    }}
                    className={`wl-btn min-h-[44px] w-full justify-start text-left ${escolhida ? "wl-btn--solid" : "wl-btn--quiet"}`}
                  >
                    {c.modelo}
                  </button>
                </li>
              );
            })}
          </ul>
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
              setVersao(null);
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
