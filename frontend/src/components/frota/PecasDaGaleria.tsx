"use client";

import { Camera, CircleAlert, Trash2, Upload } from "lucide-react";
import { useRef, useState, type DragEvent, type ReactNode } from "react";
import { Button, Icone, StatusBadge } from "@/design-system";

// VEI-10. As três peças da galeria que o editar do veículo e o cadastro novo (T-437) montam, cada um com as próprias ações:
// a zona de envio, o cartão de foto (ações por slot) e a lista de recusas. Nenhuma chama a API nem conhece o modelo do servidor.

export const FORMATOS_ACEITOS = "image/jpeg,image/png";

/** Zona tracejada: clicar em "Selecionar fotos" ou soltar arquivos aqui. A validação é da API; esta peça só entrega os arquivos. */
export function ZonaDeEnvio({ limite, ocupado = false, progresso, aoEscolher }: { limite: number; ocupado?: boolean; progresso?: string | null; aoEscolher: (arquivos: File[]) => void }) {
  const escolher = useRef<HTMLInputElement>(null);
  const [sobre, setSobre] = useState(false);
  const soltar = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setSobre(false);
    if (ocupado) return;
    const arquivos = Array.from(e.dataTransfer.files);
    if (arquivos.length > 0) aoEscolher(arquivos);
  };
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!ocupado) setSobre(true);
      }}
      onDragLeave={() => setSobre(false)}
      onDrop={soltar}
      className={`flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center ${sobre ? "border-solid bg-surface-sunken" : "border-line"}`}
    >
      <Icone de={Upload} className="size-6 text-ink-muted" />
      <p className="m-0 text-body font-medium">Clique para enviar fotos ou arraste arquivos aqui</p>
      <Button variante="solido" compacto disabled={ocupado} onClick={() => escolher.current?.click()}>
        {ocupado ? "Enviando…" : "Selecionar fotos"}
      </Button>
      <input
        ref={escolher}
        type="file"
        multiple
        accept={FORMATOS_ACEITOS}
        className="hidden"
        aria-label="Escolher as fotos para enviar"
        onChange={(e) => {
          const arquivos = Array.from(e.target.files ?? []);
          e.target.value = "";
          if (arquivos.length > 0) aoEscolher(arquivos);
        }}
      />
      <span className="text-caption text-ink-muted">JPG ou PNG de até 10 MB · até {limite} fotos no total · a localização (GPS) é removida</span>
      {progresso && (
        <span role="status" className="text-caption">
          {progresso}
        </span>
      )}
    </div>
  );
}

/**
 * Foto com o selo de posição, o selo Capa e as ações num slot. Abaixo de 721 px é uma linha (miniatura de 64 px, texto e
 * botões ao lado); a partir daí, um cartão com a miniatura de 140 px.
 */
export function CartaoDeFoto({ url, alt, posicao, capa, legenda, acoes }: { url: string | null; alt: string; posicao: number; capa: boolean; legenda: string; acoes?: ReactNode }) {
  return (
    <li className="flex min-w-0 items-center gap-3 border-b border-line py-3 last:border-b-0 md:flex-col md:items-stretch md:border-b-0 md:py-0">
      <div className="relative size-[64px] shrink-0 overflow-hidden rounded-md bg-surface-sunken md:size-auto md:h-[140px] md:w-full">
        {url ? (
          // A URL é assinada e vale 15 minutos (AUD-05).
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={alt} className="size-full object-cover" />
        ) : (
          <span aria-hidden="true" className="absolute inset-0 grid place-items-center text-ink-muted opacity-[.55]">
            <Icone de={Camera} className="size-5" />
          </span>
        )}
        <span className="absolute right-1 top-1 md:right-2 md:top-2">
          <StatusBadge tom="superficie" compacto>
            {posicao}
          </StatusBadge>
        </span>
        {capa && (
          <span className="absolute bottom-1 left-1 hidden md:left-2 md:top-2 md:bottom-auto md:block">
            <StatusBadge tom="solido" compacto>
              Capa
            </StatusBadge>
          </span>
        )}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2 text-caption text-ink-muted">
          <span className="truncate">{legenda}</span>
          {capa && (
            <span className="md:hidden">
              <StatusBadge tom="solido" compacto>
                Capa
              </StatusBadge>
            </span>
          )}
        </div>
        {acoes && <div className="flex flex-wrap gap-2">{acoes}</div>}
      </div>
    </li>
  );
}

/** Apagar é a única ação em `critical-ink` do cartão. */
export function BotaoApagar({ disabled, aoClicar, rotulo = "Apagar" }: { disabled?: boolean; aoClicar: () => void; rotulo?: string }) {
  return (
    <button type="button" disabled={disabled} onClick={aoClicar} className="wl-btn wl-btn--quiet wl-btn--sm text-critical-ink">
      <Icone de={Trash2} />
      {rotulo}
    </button>
  );
}

export type RecusaDeFoto = { chave: string; nome: string; mensagem: string };

/** Faixa `critical-soft` com o nome do arquivo e a frase da API. */
export function ListaDeRecusas({ recusas, aoDispensar }: { recusas: RecusaDeFoto[]; aoDispensar?: () => void }) {
  if (recusas.length === 0) return null;
  return (
    <div role="alert" className="flex items-start gap-3 rounded-md bg-critical-soft p-3 text-critical-ink">
      <Icone de={CircleAlert} className="mt-[2px] size-5 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {recusas.map((r) => (
          <p key={r.chave} className="m-0 text-body">
            <span className="wl-mono break-all">{r.nome}</span>: {r.mensagem}
          </p>
        ))}
        {aoDispensar && (
          <div>
            <Button compacto variante="quieto" onClick={aoDispensar}>
              Fechar o aviso
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
