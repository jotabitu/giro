"use client";

import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Button } from "@/design-system";
import { copiarQuandoChegar } from "@/lib/area-de-transferencia";
import { mensagemDoErro } from "@/lib/erros";
import { dataHoraCurta } from "@/lib/formatos";

type RespostaDoLink = { link: string; expira_em: string; aviso: string };

/**
 * Copiar link do contrato e do recibo (T-411, S-15). O link só existe na resposta da mutação: fica neste
 * estado local, some ao fechar o painel e nunca vai para cache, URL nem armazenamento do navegador.
 * A cópia começa no clique, antes da resposta (Safari, T-252); cada clique gera um link novo.
 */
export function useCopiarLink(pedir: () => Promise<RespostaDoLink>, aoCopiar?: () => void) {
  const falhouACopia = useRef(false);
  const mutacao = useMutation({
    mutationFn: async ({ pedido, copia }: { pedido: Promise<RespostaDoLink>; copia: Promise<void> }) => {
      const r = await pedido;
      falhouACopia.current = false;
      await copia.catch(() => {
        falhouACopia.current = true;
      });
      return r;
    },
    onSuccess: () => aoCopiar?.(),
  });
  const copiar = () => {
    const pedido = pedir();
    const copia = copiarQuandoChegar(pedido.then((r) => r.link));
    copia.catch(() => undefined); // se a API falhar, o erro que vale é o dela, lido em `pedido`
    mutacao.mutate({ pedido, copia });
  };
  return { copiar, pendente: mutacao.isPending, erro: mutacao.isError ? mensagemDoErro(mutacao.error) : null, resultado: mutacao.data ?? null, falhouACopia: falhouACopia.current, limpar: mutacao.reset };
}

/** O link recém-gerado, num campo só de leitura, com a validade e o aviso da API. */
export function LinkCopiado({ resultado, copiado, aviso, aoFechar }: { resultado: RespostaDoLink; copiado: boolean; aviso?: string; aoFechar: () => void }) {
  const campo = useRef<HTMLInputElement>(null);
  const [selecionado, setSelecionado] = useState(false);
  return (
    <div role="status" className="flex flex-col gap-2 rounded-md bg-surface-sunken p-4">
      <span className="text-caption text-ink-muted">
        {copiado ? "Link copiado." : "Não deu para copiar sozinho. Selecione o link abaixo e copie."} Vale até {dataHoraCurta(resultado.expira_em)}.
      </span>
      <input
        ref={(el) => {
          campo.current = el;
          if (el && !copiado && !selecionado) {
            el.select();
            setSelecionado(true);
          }
        }}
        readOnly
        aria-label="Link gerado"
        value={resultado.link}
        onFocus={(e) => e.currentTarget.select()}
        className="wl-mono min-h-[44px] w-full rounded-md border border-line bg-surface px-3 text-caption"
      />
      {aviso && <p className="text-caption text-ink">{aviso}</p>}
      <p className="text-caption text-ink-muted">{resultado.aviso}</p>
      <Button compacto variante="quieto" onClick={aoFechar}>
        Fechar o link
      </Button>
    </div>
  );
}
