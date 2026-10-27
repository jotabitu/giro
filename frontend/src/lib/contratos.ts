import type { ModeloDeContrato, ModeloDeContratoDaLista } from "@/lib/api";

// Modelos de contrato (IMP-04, S-09, LOC-15). A tela só monta o texto do marcador; quem valida a lista fechada e sanitiza o HTML é a API.

/** Coloca `{{chave}}` onde está o cursor (ou no lugar da seleção) e diz onde o cursor fica depois. */
export function inserirMarcador(texto: string, chave: string, inicio: number, fim: number): { texto: string; cursor: number } {
  const marcador = `{{${chave}}}`;
  const de = Math.max(0, Math.min(inicio, texto.length));
  const ate = Math.max(de, Math.min(fim, texto.length));
  return { texto: texto.slice(0, de) + marcador + texto.slice(ate), cursor: de + marcador.length };
}

type ComStatus = Pick<ModeloDeContratoDaLista | ModeloDeContrato, "status" | "versao_publicada" | "tem_rascunho" | "arquivado">;

/** "Publicado · v3", "Rascunho" ou "Arquivado", como o selo da lista mostra. */
export function rotuloDoModelo(m: ComStatus): string {
  if (m.arquivado) return "Arquivado";
  if (m.status === "publicado") return `Publicado · v${m.versao_publicada ?? 1}`;
  return "Rascunho";
}

/** O texto do botão de publicar: a versão que sai ("Publicar versão 4"), ou a primeira. */
export function rotuloDePublicar(m: Pick<ComStatus, "versao_publicada">): string {
  return `Publicar versão ${(m.versao_publicada ?? 0) + 1}`;
}

/** Tem o que publicar: nunca foi publicado, ou há rascunho de uma versão nova. */
export const podePublicar = (m: ComStatus): boolean => !m.arquivado && (m.status === "rascunho" || m.tem_rascunho);

export const rotuloDeUso = (m: Pick<ModeloDeContratoDaLista, "finalidade" | "contratos_gerados">): string => {
  const n = m.contratos_gerados;
  const coisa = m.finalidade === "venda" ? (n === 1 ? "venda" : "vendas") : n === 1 ? "locação" : "locações";
  return n === 0 ? "ainda sem uso" : `usado em ${n} ${coisa}`;
};
