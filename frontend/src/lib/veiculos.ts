import { z } from "zod";
import type { NovoVeiculo } from "@/lib/api";

const texto = z.string().trim();

/** Só o que a API exige para salvar; formato de placa, chassi e anos é conferido pela API e o erro volta no campo. */
export const esquemaVeiculo = z.object({
  tipo: z.enum(["moto", "carro"]),
  placa: texto.min(1, "Informe a placa"),
  marca: texto.min(1, "Informe a marca"),
  modelo: texto.min(1, "Informe o modelo"),
  ano_fabricacao: texto.min(1, "Informe o ano"),
  ano_modelo: texto.min(1, "Informe o ano"),
  chassi: texto.min(1, "Informe o chassi"),
  renavam: texto,
  cor: texto.min(1, "Informe a cor"),
  km_atual: texto.min(1, "Informe o km"),
  filial_id: texto.min(1, "Escolha a filial"),
  categoria_id: texto.min(1, "Escolha a categoria"),
  capacidade_tanque_litros: texto,
  data_compra: texto,
  valor_compra: texto.refine((t) => t === "" || centavosDoTexto(t) !== null, "Informe um valor, como R$ 13.490,00"),
});
export type ValoresVeiculo = z.infer<typeof esquemaVeiculo>;

export const VALORES_INICIAIS_VEICULO: ValoresVeiculo = {
  tipo: "moto",
  placa: "",
  marca: "",
  modelo: "",
  ano_fabricacao: "",
  ano_modelo: "",
  chassi: "",
  renavam: "",
  cor: "",
  km_atual: "0",
  filial_id: "",
  categoria_id: "",
  capacidade_tanque_litros: "",
  data_compra: "",
  valor_compra: "",
};

/** "13.490,00" ou "R$ 13.490,00" em centavos (1349000). Texto que não é valor volta `null`; a API confere o resto. */
export function centavosDoTexto(t: string): number | null {
  const limpo = t.replace(/[R$\s.]/g, "").replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(limpo)) return null;
  const [inteiro = "0", frac = ""] = limpo.split(".");
  return Number(inteiro) * 100 + Number(frac.padEnd(2, "0"));
}

/** Corpo do POST /api/veiculos/: placa sem hífen e em maiúsculas, opcionais vazios ficam de fora. */
export function paraCorpoVeiculo(v: ValoresVeiculo): NovoVeiculo {
  const corpo: NovoVeiculo = {
    placa: v.placa.replace(/[\s-]/g, "").toUpperCase(),
    chassi: v.chassi.replace(/\s/g, "").toUpperCase(),
    marca: v.marca.trim(),
    modelo: v.modelo.trim(),
    ano_fabricacao: Number(v.ano_fabricacao),
    ano_modelo: Number(v.ano_modelo),
    cor: v.cor.trim(),
    km_atual: Number(v.km_atual.replace(/\./g, "")),
    categoria_id: Number(v.categoria_id),
    filial_id: Number(v.filial_id),
  };
  if (v.renavam) corpo.renavam = v.renavam.replace(/\D/g, "");
  if (v.capacidade_tanque_litros) corpo.capacidade_tanque_litros = v.capacidade_tanque_litros.replace(",", ".");
  if (v.data_compra) corpo.data_compra = v.data_compra;
  if (v.valor_compra) {
    const c = centavosDoTexto(v.valor_compra);
    if (c !== null) corpo.valor_compra_centavos = c;
  }
  return corpo;
}
