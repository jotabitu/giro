import type { Eu } from "@/lib/api";

export const ROTA_DA_ENTRADA_DO_SUPORTE = "/suporte/entrar";
/** Destino depois de "Sair do suporte": a página de entrada, avisando que a saída foi pedida. */
export const ROTA_DEPOIS_DE_SAIR = `${ROTA_DA_ENTRADA_DO_SUPORTE}?saiu=1`;

export const TEXTO_SUPORTE_TERMINOU = "O acesso de suporte terminou";
export const TEXTO_SAIU_DO_SUPORTE = "Você saiu do modo suporte";

const ROTULO_DA_PERMISSAO = { ver: "Só ver", ver_editar: "Ver e editar" } as const;

type Suporte = NonNullable<Eu["suporte"]>;

/** Rótulos da faixa. Vêm da API (`permissao_rotulo`, `fim_rotulo`); sem eles, o rótulo fixo da permissão e nenhum horário. */
export function rotulosDaFaixa(s: Suporte): { permissao: string; fim: string | null } {
  return { permissao: s.permissao_rotulo ?? ROTULO_DA_PERMISSAO[s.permissao], fim: s.fim_rotulo ?? null };
}
