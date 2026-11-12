"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Button, Dialogo } from "@/design-system";

// VEI-10, "Sair da tela com fotos enviando" (T-462, CA-437-11). Enquanto há foto na fila, o navegador pergunta antes de
// sair, fechar ou recarregar (texto dele, não do Giro) e os links de dentro do sistema pedem "Sair" ou "Ficar".
// As fotos que já subiram ficam no veículo; as que faltavam se enviam depois pelo editar.

const plural = (n: number, um: string, varios: string) => (n === 1 ? um : varios);

/** "Faltam 3 fotos. Não feche esta tela." / "Falta 1 foto." */
export const textoDeFaltam = (n: number) => (n === 1 ? "Falta 1 foto." : `Faltam ${n} fotos. Não feche esta tela.`);

/** "Ainda faltam 3 fotos. Se sair, elas não serão enviadas." */
export const textoDoAviso = (n: number) => `Ainda ${plural(n, "falta 1 foto", `faltam ${n} fotos`)}. Se sair, ${plural(n, "ela não será enviada", "elas não serão enviadas")}.`;

/** O link que leva a outra página do sistema; null para âncora, nova aba, download, outra origem ou a mesma página. */
export function destinoInterno(ev: Pick<MouseEvent, "defaultPrevented" | "button" | "metaKey" | "ctrlKey" | "shiftKey" | "altKey" | "target">, base: Pick<Location, "href" | "origin" | "pathname" | "search"> = window.location): string | null {
  if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return null;
  const dentro = ev.target as Partial<Element> | null;
  const alvo = typeof dentro?.closest === "function" ? (dentro.closest("a[href]") as HTMLAnchorElement | null) : null;
  if (!alvo) return null;
  if ((alvo.target && alvo.target !== "_self") || alvo.hasAttribute("download")) return null;
  const url = new URL(alvo.href, base.href);
  if (url.origin !== base.origin) return null;
  if (url.pathname === base.pathname && url.search === base.search) return null;
  return url.pathname + url.search + url.hash;
}

/**
 * Liga o aviso enquanto `faltam` for maior que zero. Devolve o diálogo para pôr na tela.
 * Voltar do navegador não passa por aqui; só sair, fechar, recarregar e os links do sistema.
 */
export function useAvisoDeSaida(faltam: number): ReactNode {
  const router = useRouter();
  const [destino, setDestino] = useState<string | null>(null);

  useEffect(() => {
    if (faltam <= 0) {
      setDestino(null);
      return;
    }
    const aoSair = (ev: BeforeUnloadEvent) => {
      ev.preventDefault();
      ev.returnValue = "";
    };
    const aoClicar = (ev: MouseEvent) => {
      const para = destinoInterno(ev);
      if (para === null) return;
      ev.preventDefault();
      ev.stopPropagation();
      setDestino(para);
    };
    window.addEventListener("beforeunload", aoSair);
    document.addEventListener("click", aoClicar, true);
    return () => {
      window.removeEventListener("beforeunload", aoSair);
      document.removeEventListener("click", aoClicar, true);
    };
  }, [faltam]);

  return (
    <Dialogo
      aberto={destino !== null && faltam > 0}
      aoFechar={() => setDestino(null)}
      titulo="Sair desta tela?"
      descricao={textoDoAviso(faltam)}
      tamanho="pequeno"
      acoes={
        <>
          <Button
            variante="quieto"
            onClick={() => {
              const para = destino;
              setDestino(null);
              if (para) router.push(para);
            }}
          >
            Sair
          </Button>
          <Button variante="solido" data-autofocus onClick={() => setDestino(null)}>
            Ficar
          </Button>
        </>
      }
    />
  );
}

/** Linha com quantas faltam, junto do andamento. */
export function FaltamFotos({ faltam }: { faltam: number }) {
  if (faltam <= 0) return null;
  return (
    <span role="status" className="text-caption font-medium text-warning-ink">
      {textoDeFaltam(faltam)}
    </span>
  );
}
