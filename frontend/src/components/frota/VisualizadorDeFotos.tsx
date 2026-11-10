"use client";

import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import { useEffect, useState, type KeyboardEvent } from "react";
import { Button, Dialogo, Icone } from "@/design-system";
import type { FotoDoVeiculo } from "@/lib/api";

// VEI-10, AUD-05, CA-414-10 a 14. Referência: Veiculo-Visualizador-Desktop|Mobile.
// O visualizador passa só pelas fotos da origem que abriu (galeria ou vistoria). Os links são da API:
// valem 15 minutos e o nome do arquivo baixado (`nome_arquivo`) também; a tela não monta nenhum dos dois.

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

export function VisualizadorDeFotos({ aberto, aoFechar, origem, legenda, fotos, inicial, aoAtualizarLinks }: VisualizadorProps) {
  const [indice, setIndice] = useState(inicial);
  const [agora, setAgora] = useState(() => Date.now());
  useEffect(() => {
    if (aberto) setIndice(inicial);
  }, [aberto, inicial]);
  useEffect(() => {
    if (!aberto) return;
    const t = setInterval(() => setAgora(Date.now()), 15_000);
    return () => clearInterval(t);
  }, [aberto]);

  const foto = fotos[Math.min(indice, fotos.length - 1)];
  if (!aberto || !foto) return null;
  const i = fotos.indexOf(foto);
  const venceu = foto.url_expira_em !== null && Date.parse(foto.url_expira_em) <= agora;
  const semLink = foto.url === null;
  const teclas = (e: KeyboardEvent) => {
    if (e.key === "ArrowLeft" && i > 0) setIndice(i - 1);
    if (e.key === "ArrowRight" && i < fotos.length - 1) setIndice(i + 1);
  };

  return (
    <Dialogo aberto={aberto} aoFechar={aoFechar} titulo={origem} descricao={legenda(foto, i, fotos.length)} tamanho="medio">
      <div className="flex flex-col gap-3" onKeyDown={teclas}>
        <div className="grid min-h-[240px] place-items-center overflow-hidden rounded-md bg-surface-sunken">
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
            <img src={foto.url ?? undefined} alt={legenda(foto, i, fotos.length)} className="max-h-[60vh] w-full object-contain" />
          )}
        </div>
        <div className="flex items-center justify-between gap-2">
          <Button compacto variante="quieto" icone={<Icone de={ChevronLeft} />} disabled={i === 0} onClick={() => setIndice(i - 1)} aria-label="Foto anterior">
            Anterior
          </Button>
          <span role="status" className="text-caption text-ink-muted">
            {legenda(foto, i, fotos.length)}
          </span>
          <Button compacto variante="quieto" disabled={i === fotos.length - 1} onClick={() => setIndice(i + 1)} aria-label="Próxima foto">
            Próxima
            <Icone de={ChevronRight} />
          </Button>
        </div>
        {foto.url_download && !venceu && (
          <div className="flex flex-col gap-1">
            <a href={foto.url_download} download={foto.nome_arquivo} rel="noopener" className="wl-btn wl-btn--solid inline-flex min-h-[44px] items-center justify-center gap-2 no-underline">
              <Icone de={Download} />
              Baixar ({foto.nome_arquivo})
            </a>
            <span className="text-caption text-ink-muted">Link válido por 15 minutos.</span>
          </div>
        )}
      </div>
    </Dialogo>
  );
}
