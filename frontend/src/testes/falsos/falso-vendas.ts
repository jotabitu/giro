// Vendas sem backend: a venda da quitação (VEN-11, docs/api/vendas.md). Só ./api-falsa.ts importa este arquivo.
import { ErroApi } from "@/lib/api/tipos";
import type { FiltroDeVendas, ListaDeVendas, Venda } from "@/lib/api/tipos-vendas";
import { pausa, perfilAtualFalso } from "./falso";

export const VENDA_DA_QUITACAO: Venda = {
  id: 18,
  codigo: "VEN-0178",
  status: "vendida",
  origem: "quitacao_locacao",
  origem_rotulo: "Quitação de locação",
  descricao: "Quitação da LOC-2901",
  cliente: { id: 1206, nome: "Lucas Ferreira" },
  veiculo: { id: 640, placa: "RTA2C55", modelo: "Honda CG 160 Fan" },
  filial: { id: 1, nome: "Filial Centro" },
  vendedor: { id: 3, nome: "Bruna Alves" },
  locacao: { id: 2901, codigo: "LOC-2901" },
  preco_final_centavos: 0,
  vendida_em: "2028-10-10T13:20:00Z",
  transferencia: { feita_em: null, registrada_por: null, pendente: true },
  acoes: { cancelar: false, registrar_transferencia: true },
};

export const vendasFalso = {
  async listar(f: FiltroDeVendas = {}): Promise<ListaDeVendas> {
    await pausa(150);
    if (perfilAtualFalso() === "vistoriador") throw new ErroApi(403, "sem_permissao", "Você não tem permissão para ver as vendas");
    const todas = [VENDA_DA_QUITACAO].filter((v) => (!f.origem || v.origem === f.origem) && (!f.transferencia_pendente || v.transferencia.pendente));
    return { proximo: null, anterior: null, resultados: todas };
  },
};
