"use client";

import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, Dialogo, Icone } from "@/design-system";
import type { FotoDoVeiculo } from "@/lib/api";
import { placaSemQuebra } from "@/lib/formatos";

// VEI-10, AUD-05, CA-414-10 a 14. Referência: Veiculo-Visualizador-Desktop|Mobile.
// O visualizador passa só pelas fotos da origem que abriu (galeria ou vistoria). Os links são da API:
// valem 15 minutos e o nome do arquivo baixado (`nome_arquivo`) também; a tela não monta nenhum dos dois.

/** Seta para a esquerda ou para a direita: devolve o índice novo, sem sair da origem. Outras teclas não mudam nada. */
export function indiceAposTecla(tecla: string, indice: number, total: number): number {
  if (tecla === "ArrowLeft") return Math.max(0, indice - 1);
  if (tecla === "ArrowRight") return Math.min(total - 1, indice + 1);
  return indice;
}

export type VisualizadorProps = {
  aberto: boolean;
  aoFechar: () => void;
  /** "Galeria do veículo" ou "Vistoria de saída · LOC-2841 · 23 set". */
  origem: string;
  /** "Foto 2 de 3" na galeria; na vistoria, o rótulo da posição. */
  legenda: (foto: FotoDoVeiculo, indice: number, total: number) => string;
  fotos: FotoDoVeiculo[];
  inicial: number;
  /** Recarrega a ficha para trazer links novos depois de `url_expira_em`. */
  aoAtualizarLinks?: () => void;
};

function Seta({ lado, desabilitada, aoClicar }: { lado: "esquerda" | "direita"; desabilitada: boolean; aoClicar: () => void }) {
  return (
    <button
      type="button"
      disabled={desabilitada}
      onClick={aoClicar}
      aria-label={lado === "esquerda" ? "Foto anterior" : "Próxima foto"}
      className={`absolute top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full bg-surface text-ink shadow-pop disabled:opacity-40 ${lado === "esquerda" ? "left-2" : "right-2"}`}
    >
      <Icone de={lado === "esquerda" ? ChevronLeft : ChevronRight} />
    </button>
  );
}

export function VisualizadorDeFotos({ aberto, aoFechar, origem, legenda, fotos, inicial, aoAtualizarLinks }: VisualizadorProps) {
  const [indice, setIndice] = useState(inicial);
  const [agora, setAgora] = useState(() => Date.now());
  const total = fotos.length;

  useEffect(() => {
    if (aberto) setIndice(inicial);
  }, [aberto, inicial]);
  useEffect(() => {
    if (!aberto) return;
    const t = setInterval(() => setAgora(Date.now()), 15_000);
    return () => clearInterval(t);
  }, [aberto]);
  // As setas valem com o foco em qualquer lugar do diálogo (no botão Fechar, no painel ou numa miniatura): o <dialog> é modal,
  // então o documento só recebe teclas de dentro dele.
  useEffect(() => {
    if (!aberto) return;
    const aoTeclar = (e: KeyboardEvent) => setIndice((i) => indiceAposTecla(e.key, i, total));
    // Na captura da janela: chega antes de qualquer elemento do diálogo e não depende de onde está o foco.
    window.addEventListener("keydown", aoTeclar, true);
    return () => window.removeEventListener("keydown", aoTeclar, true);
  }, [aberto, total]);

  const foto = fotos[Math.min(indice, total - 1)];
  if (!aberto || !foto) return null;
  const i = fotos.indexOf(foto);
  const venceu = foto.url_expira_em !== null && Date.parse(foto.url_expira_em) <= agora;
  const semLink = foto.url === null;

  // Tamanho amplo do Dialogo (T-446): até 1100 × 820 px e tela cheia no celular, como a Veiculo-Visualizador.
  return (
    <Dialogo aberto={aberto} aoFechar={aoFechar} titulo={placaSemQuebra(origem)} descricao={placaSemQuebra(legenda(foto, i, total))} tamanho="amplo">
      {/* data-autofocus: o Dialogo põe o foco aqui ao abrir, dentro do conteúdo do visualizador. */}
      <div data-autofocus tabIndex={-1} className="flex h-full min-h-0 flex-1 flex-col gap-3 outline-none">
        <div className="relative grid min-h-[240px] min-w-0 flex-1 place-items-center overflow-hidden rounded-md bg-surface-sunken">
          {semLink ? (
            <p className="p-6 text-center text-body text-ink-muted">Sem link para esta foto neste acesso.</p>
          ) : venceu ? (
            <div className="flex flex-col items-center gap-3 p-6 text-center">
              <p className="text-body text-ink-muted">O link desta foto venceu. Peça links novos para ver e baixar.</p>
              {aoAtualizarLinks && (
                <Button compacto onClick={aoAtualizarLinks}>
                  Atualizar os links
                </Button>
              )}
            </div>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={foto.url ?? undefined} alt={legenda(foto, i, total)} className="size-full object-contain" />
          )}
          {total > 1 && (
            <>
              <Seta lado="esquerda" desabilitada={i === 0} aoClicar={() => setIndice(i - 1)} />
              <Seta lado="direita" desabilitada={i === total - 1} aoClicar={() => setIndice(i + 1)} />
            </>
          )}
        </div>
        <p role="status" className="m-0 text-caption text-ink-muted">
          {placaSemQuebra(`${legenda(foto, i, total)} · Origem: ${origem}`)} ({total} {total === 1 ? "foto" : "fotos"}). As setas passam só por esta origem.
        </p>
        {total > 1 && (
          <ul className="m-0 flex list-none gap-2 overflow-x-auto p-0 pb-1" aria-label="Fotos desta origem">
            {fotos.map((f, n) => (
              <li key={f.id} className="shrink-0">
                <button
                  type="button"
                  onClick={() => setIndice(n)}
                  aria-label={`Ver ${legenda(f, n, total)}`}
                  aria-current={n === i ? "true" : undefined}
                  className={`block h-[52px] w-[72px] overflow-hidden rounded-md bg-surface-sunken ${n === i ? "border-2 border-solid" : "border-2 border-transparent"}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  {f.url ? <img src={f.url} alt="" className="size-full object-cover" /> : null}
                </button>
              </li>
            ))}
          </ul>
        )}
        {foto.url_download && !venceu && (
          <div className="flex flex-col gap-1">
            <a href={foto.url_download} download={foto.nome_arquivo} rel="noopener" className="wl-btn wl-btn--solid inline-flex min-h-[44px] items-center justify-center gap-2 no-underline">
              <Icone de={Download} />
              Baixar ({placaSemQuebra(foto.nome_arquivo)})
            </a>
            <span className="text-caption text-ink-muted">Link válido por 15 minutos.</span>
          </div>
        )}
      </div>
    </Dialogo>
  );
}
