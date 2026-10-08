"use client";

import { useEffect, useState } from "react";

/** Token de um link `/pagina#<token>`: o texto depois do `#`, sem espaços. Vazio vira `null`. */
export function tokenDoFragmento(hash: string): string | null {
  const token = hash.replace(/^#/, "").trim();
  return token === "" ? null : token;
}

/** Lê o token do fragmento e, se havia, apaga o fragmento da barra e do histórico (`history.replaceState`). */
export function consumirFragmento(
  local: Pick<Location, "hash" | "pathname" | "search">,
  historico: Pick<History, "replaceState">,
): string | null {
  const token = tokenDoFragmento(local.hash);
  if (token) historico.replaceState(null, "", local.pathname + local.search);
  return token;
}

export type TokenDoLink = { pronto: boolean; token: string | null };

/**
 * Lê o token do fragmento da URL, apaga o fragmento da barra e do histórico (`history.replaceState`) e guarda o token só em memória.
 * O fragmento não vai ao servidor nem ao proxy, então o token não cai em log nem no Sentry (P-09, T-072).
 * `pronto` é falso até a leitura no navegador; depois, `token` é `null` se o link veio sem ele.
 */
export function useTokenDoFragmento(): TokenDoLink {
  const [estado, setEstado] = useState<TokenDoLink>({ pronto: false, token: null });
  useEffect(() => {
    const lido = consumirFragmento(window.location, window.history);
    // No modo estrito o efeito roda duas vezes: a segunda já não vê o fragmento e não pode apagar o token.
    setEstado((atual) => (atual.token ? atual : { pronto: true, token: lido }));
  }, []);
  return estado;
}
