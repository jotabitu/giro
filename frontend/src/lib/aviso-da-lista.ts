// O aviso que a ficha deixa para a lista mostrar depois de voltar (VEI-22, CLI-13: "Veículo SAK-1D39 excluído.").
// A frase vem pronta da API e fica em memória, não na URL: ninguém monta um aviso pelo endereço, e recarregar a lista o apaga.

let pendente: { rota: string; texto: string } | null = null;

export function deixarAvisoParaALista(rota: string, texto: string) {
  pendente = { rota, texto };
}

/** Lê sem apagar: o render pode rodar duas vezes. Quem mostra apaga com `esquecerAvisoDaLista` depois de montar. */
export function avisoDaLista(rota: string): string | null {
  return pendente?.rota === rota ? pendente.texto : null;
}

export function esquecerAvisoDaLista(rota: string) {
  if (pendente?.rota === rota) pendente = null;
}
