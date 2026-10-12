"use client";

// O "hoje" da tela vem da API (ADR 0021), nunca só do relógio do navegador: com a data simulada ligada, o dia é o
// de referência e a hora é a real, como no backend (comum.relogio). Sem resposta da API, vale o relógio do navegador.
import { useSyncExternalStore } from "react";
import type { Ambiente, EscopoDoAmbiente } from "@/lib/api";

let atual: Ambiente | null = null;
const ouvintes = new Set<() => void>();

export function definirAmbiente(a: Ambiente | null) {
  if (a?.hoje === atual?.hoje && a?.data_simulada === atual?.data_simulada) return;
  atual = a;
  ouvintes.forEach((o) => o());
}

export function ambienteAtual(): Ambiente | null {
  return atual;
}

const assinar = (o: () => void) => {
  ouvintes.add(o);
  return () => ouvintes.delete(o);
};

export function useAmbiente(): Ambiente | null {
  return useSyncExternalStore(assinar, ambienteAtual, () => null);
}

/** Rotas do painel da plataforma leem o ambiente do urlconf público; as demais, o da empresa. */
export function escopoDaRota(caminho: string): EscopoDoAmbiente {
  return caminho === "/plataforma" || caminho.startsWith("/plataforma/") ? "plataforma" : "empresa";
}

/** O instante `real` com o dia trocado por `hoje` (AAAA-MM-DD), mantendo a hora de Brasília (UTC-3, sem horário de verão). */
export function agoraNoDia(hoje: string, real: Date = new Date()): Date {
  const p = new Intl.DateTimeFormat("en-GB", { timeZone: "America/Sao_Paulo", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).format(real);
  const dia = new Date(`${hoje}T${p}-03:00`);
  return Number.isNaN(dia.getTime()) ? real : dia;
}

/** "Agora" para as telas: a data da API com a hora do navegador. */
export function agoraDaTela(real: Date = new Date()): Date {
  return atual ? agoraNoDia(atual.hoje, real) : real;
}

/** Hook do "agora" da tela; renderiza de novo quando o ambiente chega. */
export function useAgora(): Date {
  const a = useAmbiente();
  return a ? agoraNoDia(a.hoje) : new Date();
}
