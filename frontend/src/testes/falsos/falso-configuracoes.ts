// DADOS FALSOS de docs/api/configuracoes.md (Moto Rápida em 07 out 2026, depois da 1ª locação). Só api-falsa.ts importa este arquivo.
import type { Configuracoes } from "@/lib/api/tipos-configuracoes";
import { pausa } from "./falso";

export const CARTOES_DO_SEED: Configuracoes["cartoes"] = [
  { chave: "marca", titulo: "Empresa e marca", resumo: "Logo, cor, nome e endereço do sistema" },
  { chave: "ramo", titulo: "O que a empresa faz", resumo: "Locação e venda · motos" },
  { chave: "filiais", titulo: "Filiais", resumo: "1 filial · Filial Centro, Fortaleza" },
  { chave: "usuarios", titulo: "Usuários e perfis", resumo: "5 de 10 usuários" },
  { chave: "precos", titulo: "Tabelas de preço", resumo: "4 categorias" },
  { chave: "modelos_contrato", titulo: "Modelos de contrato", resumo: "1 modelo" },
  { chave: "assinatura", titulo: "Assinatura", resumo: "Profissional · teste até 21 out" },
  { chave: "auditoria", titulo: "Auditoria", resumo: "Quem fez o quê no sistema" },
  { chave: "exportar", titulo: "Exportar dados", resumo: "Baixe a auditoria em CSV" },
];

export const IMPLANTANDO: NonNullable<Configuracoes["implantacao"]> = {
  concluidos: 6,
  total: 10,
  titulo: "Implantação concluída em 6 de 10 passos",
  faltam: "Faltam contrato, recebimentos, importar dados e a 1ª locação.",
  acao: null,
};

export const configuracoesFalso = {
  async resumo(): Promise<Configuracoes> {
    await pausa();
    return { cartoes: CARTOES_DO_SEED, implantacao: null };
  },
};
