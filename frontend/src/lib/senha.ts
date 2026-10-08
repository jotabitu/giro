export type RegraDeSenha = { chave: string; texto: string; ok: boolean };

/**
 * Lista de conferência enquanto a pessoa digita. É só dica visual: a validação final, inclusive a lista
 * de senhas comuns e o nome da empresa, é da API (docs/api/contas.md).
 */
export function regrasDeSenha(senha: string, email?: string): RegraDeSenha[] {
  const regras: RegraDeSenha[] = [
    { chave: "tamanho", texto: "12 caracteres ou mais", ok: senha.length >= 12 },
    { chave: "mistura", texto: "Letras e números", ok: /[A-Za-z]/.test(senha) && /\d/.test(senha) },
  ];
  if (email) {
    regras.push({ chave: "diferente", texto: "Diferente do e-mail e do nome da empresa", ok: senha.length > 0 && senha.toLowerCase() !== email.toLowerCase() });
  }
  return regras;
}
