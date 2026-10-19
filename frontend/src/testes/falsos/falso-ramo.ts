// DADOS FALSOS de docs/api/empresas.md ("Ramo da empresa"). Só api-falsa.ts importa este arquivo.
import { ErroApi } from "@/lib/api/tipos";
import type { CorpoDoRamo, Ramo } from "@/lib/api/tipos-configuracoes";
import { pausa } from "./falso";

const ALUGA: Ramo["atividades"][number] = { valor: "aluga", titulo: "Locação", descricao: "Aluguel por dia, semana ou mês", aviso: null };
const VENDE: Ramo["atividades"][number] = { valor: "vende", titulo: "Venda de veículos", descricao: "Novos, seminovos e consignados", aviso: null };
const TIPOS: Ramo["tipos"] = [
  { valor: "motos", titulo: "Motos" },
  { valor: "carros", titulo: "Carros" },
];

export const RAMO_PROFISSIONAL: Ramo = {
  atividade: "ambos",
  trabalha_com: "motos",
  atividades: [ALUGA, VENDE],
  atividades_aceitas: ["aluga", "vende", "ambos"],
  tipos: TIPOS,
  modulos: {
    aluga: ["Locação e vistoria", "Contas a receber", "Contrato digital", "Manutenção e despesas", "Relatórios"],
    vende: ["Contas a receber", "Contrato digital", "Vendas e comissões", "Manutenção e despesas", "Relatórios"],
    ambos: ["Locação e vistoria", "Contas a receber", "Contrato digital", "Vendas e comissões", "Manutenção e despesas", "Relatórios"],
  },
};

export const RAMO_ESSENCIAL: Ramo = {
  atividade: "aluga",
  trabalha_com: "motos",
  atividades: [ALUGA, { ...VENDE, aviso: "Vendas faz parte do plano Profissional." }],
  atividades_aceitas: ["aluga", "ambos"],
  tipos: TIPOS,
  modulos: { aluga: ["Locação e vistoria", "Contas a receber", "Contrato digital"], ambos: ["Locação e vistoria", "Contas a receber", "Contrato digital"] },
};

let atual: Ramo = RAMO_PROFISSIONAL;

export const ramoFalso = {
  async obter(): Promise<Ramo> {
    await pausa();
    return atual;
  },
  /** Deixar de alugar recusa com 51 locações abertas, como a referência; o resto grava. */
  async trocar(corpo: CorpoDoRamo): Promise<Ramo> {
    await pausa();
    if (atual.atividade !== "vende" && corpo.atividade === "vende")
      throw new ErroApi(422, "PLT-12", "Para deixar de alugar, resolva o que está aberto: 51 locações abertas.", { motivo: "abertos", recurso: "locacoes_vistoria", abertos_texto: "51 locações abertas" });
    atual = { ...atual, ...corpo };
    return atual;
  },
};
