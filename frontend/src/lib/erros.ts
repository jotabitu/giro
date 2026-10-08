import { ErroApi } from "@/lib/api";

/** Texto para o usuário a partir de um erro da API; a mensagem já vem pronta em português. */
export function mensagemDoErro(erro: unknown): string {
  if (erro instanceof ErroApi) return erro.message;
  return "Não foi possível concluir agora. Tente de novo.";
}

export function campoDoErro(erro: unknown, campo: string): string | undefined {
  return erro instanceof ErroApi ? erro.campos?.[campo] : undefined;
}

export function aparelhoAtual(): "desktop" | "celular" {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 720px)").matches ? "celular" : "desktop";
}
