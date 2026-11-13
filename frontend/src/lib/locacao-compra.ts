import type { LocacaoCompleta } from "@/lib/api";
import { dataCompleta, placa } from "@/lib/formatos";

// Textos da locação com intenção de compra que não vêm prontos da API (LOC-16, "Na tela"), montados só com campos dela.

/** "Fazer a transferência no Detran: RTA-2C55 para Lucas Ferreira. LOC-2901 quitada em 10/10/2028." (o aviso dos gerentes, `LOC-16`). */
export function textoDaTransferencia(l: Pick<LocacaoCompleta, "codigo" | "veiculo" | "cliente" | "compra">): string {
  const quitada = l.compra?.quitada_em;
  return `Fazer a transferência no Detran: ${placa(l.veiculo.placa)} para ${l.cliente.nome}. ${l.codigo} quitada${quitada ? ` em ${dataCompleta(quitada)}` : ""}.`;
}
