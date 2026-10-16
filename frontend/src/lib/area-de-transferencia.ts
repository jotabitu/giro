/**
 * Copia um texto que ainda vai chegar da API (USR-01, T-252).
 *
 * O Safari só grava na área de transferência durante o toque: `writeText` depois do `await` da
 * requisição é recusado. Por isso a gravação começa na hora do clique, com um `ClipboardItem` cujo
 * conteúdo é a promessa do texto. Sem `ClipboardItem` (navegador antigo), espera o texto e usa
 * `writeText`, que o Chrome e o Firefox aceitam logo depois do clique.
 *
 * Chame direto no `onClick`, antes de qualquer `await`. O texto não é guardado em lugar nenhum.
 */
export function copiarQuandoChegar(texto: Promise<string>): Promise<void> {
  const area = typeof navigator === "undefined" ? undefined : navigator.clipboard;
  if (!area) return texto.then(() => Promise.reject(new Error("Sem área de transferência.")));
  if (typeof ClipboardItem !== "undefined" && typeof area.write === "function") {
    const conteudo = texto.then((t) => new Blob([t], { type: "text/plain" }));
    return area.write([new ClipboardItem({ "text/plain": conteudo })]);
  }
  return texto.then((t) => area.writeText(t));
}
