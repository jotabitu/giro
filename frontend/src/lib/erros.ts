import { ErroApi } from "@/lib/api";

const BLOQUEIOS = new Set(["PLT-08", "USR-06"]);

/** "14:32" em America/Sao_Paulo, ou `undefined` se a data não for válida. */
function horaDoBloqueio(iso: unknown): string | undefined {
  if (typeof iso !== "string") return undefined;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return undefined;
  return new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" }).format(d);
}

/** "42 segundos", "1 minuto", "2 minutos": o tempo de espera do 429 `muitas_requisicoes`, arredondado para cima. */
export function tempoDeEspera(segundos: number): string {
  if (segundos < 60) return `${Math.max(1, Math.ceil(segundos))} ${segundos <= 1 ? "segundo" : "segundos"}`;
  const minutos = Math.ceil(segundos / 60);
  return `${minutos} ${minutos === 1 ? "minuto" : "minutos"}`;
}

/**
 * Texto para o usuário a partir de um erro da API; a mensagem já vem pronta em português.
 * 429 de bloqueio (`PLT-08`, `USR-06`) diz até que horas; 429 `muitas_requisicoes` diz quanto esperar.
 */
export function mensagemDoErro(erro: unknown): string {
  if (!(erro instanceof ErroApi)) return "Não foi possível concluir agora. Tente de novo.";
  if (erro.status === 429 && BLOQUEIOS.has(erro.codigo)) {
    const hora = horaDoBloqueio(erro.detalhes?.tentar_de_novo_em);
    return hora ? `${erro.message}. Você pode tentar de novo às ${hora}.` : `${erro.message}.`;
  }
  if (erro.status === 429 && erro.codigo === "muitas_requisicoes") {
    const s = Number(erro.detalhes?.tentar_de_novo_em_segundos);
    return Number.isFinite(s) && s > 0 ? `Muitas tentativas seguidas. Espere ${tempoDeEspera(s)} e tente de novo.` : erro.message;
  }
  return erro.message;
}

export function campoDoErro(erro: unknown, campo: string): string | undefined {
  return erro instanceof ErroApi ? erro.campos?.[campo] : undefined;
}

export function aparelhoAtual(): "desktop" | "celular" {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 720px)").matches ? "celular" : "desktop";
}
