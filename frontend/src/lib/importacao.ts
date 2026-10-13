// Textos da importação por planilha. Contagens, estado, erros e avisos vêm da API (docs/api/importacao.md); a tela não conta linha.
import type { Importacao, TipoDeImportacao } from "@/lib/api";

export const TIPOS_DE_IMPORTACAO: { tipo: TipoDeImportacao; titulo: string; apoio: string; modelo: string }[] = [
  { tipo: "veiculos", titulo: "Veículos", apoio: "Placa, chassi, marca, modelo, ano, cor, km e categoria", modelo: "Baixar planilha modelo de veículos" },
  { tipo: "clientes", titulo: "Clientes", apoio: "Nome, CPF, CNH, telefone e endereço", modelo: "Baixar planilha modelo de clientes" },
];

export const TAMANHO_MAXIMO_DA_PLANILHA = 5 * 1024 * 1024;

/** A importação ainda está sendo conferida ou gravada: a tela atualiza sozinha. */
export const emAndamento = (i: Pick<Importacao, "status">): boolean => i.status === "validando" || i.status === "importando";

/** A mais recente do tipo que não foi cancelada. */
export function atualDoTipo(lista: Importacao[], tipo: TipoDeImportacao): Importacao | null {
  return [...lista].filter((i) => i.tipo === tipo && i.status !== "cancelada").sort((a, b) => b.id - a.id)[0] ?? null;
}

export const plural = (n: number, um: string, varios: string): string => `${n} ${n === 1 ? um : varios}`;

/** "frota-moto-rapida.xlsx · 86 linhas". */
export const resumoDoArquivo = (i: Pick<Importacao, "arquivo" | "contagens">): string => `${i.arquivo} · ${plural(i.contagens.linhas, "linha", "linhas")}`;

/** Campos da linha que a pessoa pode corrigir: o campo do erro. */
export const rotuloDoCampo = (campo: string): string => campo.replace(/_/g, " ");
