// Regras do campo de código, sem DOM, para testar sem navegador.
// O valor é uma string só de dígitos e sem buracos: a caixa i mostra valor[i].

export const TAMANHO_PADRAO = 6;

export function soDigitos(texto: string): string {
  return texto.replace(/\D/g, "");
}

export type Resultado = { valor: string; foco: number };

function limitar(foco: number, tamanho: number): number {
  return Math.max(0, Math.min(foco, tamanho - 1));
}

/**
 * Entrada de texto na caixa `indice`. Um dígito sobrescreve a posição (sempre colada ao fim do valor);
 * vários dígitos (colar, preenchimento automático do celular) substituem dali em diante.
 * Texto sem dígito é ignorado.
 */
export function aplicarEntrada(valor: string, indice: number, texto: string, tamanho = TAMANHO_PADRAO): Resultado {
  const digitos = soDigitos(texto);
  if (!digitos) return { valor, foco: limitar(indice, tamanho) };
  const posicao = Math.min(indice, valor.length);
  const novo =
    digitos.length === 1
      ? valor.slice(0, posicao) + digitos + valor.slice(posicao + 1)
      : valor.slice(0, posicao) + digitos;
  const cortado = novo.slice(0, tamanho);
  return { valor: cortado, foco: limitar(posicao + Math.min(digitos.length, tamanho - posicao), tamanho) };
}

/** Backspace na caixa `indice`: apaga o dígito dela; se estiver vazia, apaga o último e volta. */
export function aplicarApagar(valor: string, indice: number, tamanho = TAMANHO_PADRAO): Resultado {
  if (indice < valor.length) return { valor: valor.slice(0, indice) + valor.slice(indice + 1), foco: indice };
  const restante = valor.slice(0, -1);
  return { valor: restante, foco: limitar(restante.length, tamanho) };
}

/** Delete na caixa `indice`: apaga o dígito dela e fica no lugar. */
export function aplicarExcluir(valor: string, indice: number): Resultado {
  if (indice >= valor.length) return { valor, foco: indice };
  return { valor: valor.slice(0, indice) + valor.slice(indice + 1), foco: indice };
}

/** Caixa de destino das setas e de Home e End; null quando a tecla não navega. */
export function destinoDaTecla(tecla: string, indice: number, tamanho = TAMANHO_PADRAO): number | null {
  switch (tecla) {
    case "ArrowLeft":
      return limitar(indice - 1, tamanho);
    case "ArrowRight":
      return limitar(indice + 1, tamanho);
    case "Home":
      return 0;
    case "End":
      return tamanho - 1;
    default:
      return null;
  }
}

export function completo(valor: string, tamanho = TAMANHO_PADRAO): boolean {
  return valor.length === tamanho;
}
