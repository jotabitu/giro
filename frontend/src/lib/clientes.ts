import { z } from "zod";
import type { AcaoPrincipal, NovoCliente } from "@/lib/api";
import { soDigitos } from "@/lib/formatos";

/** Para onde cada ação principal da lista leva. Rotas de módulos ainda não feitos já apontam para o destino final. */
export function rotaDaAcao(a: AcaoPrincipal): string {
  const id = a.alvo?.id;
  switch (a.codigo) {
    case "cobrar":
      return "/financeiro/receber";
    case "completar_cadastro":
      return id ? `/clientes/${id}` : "/clientes";
    case "ver_proposta":
      return id ? `/vendas/${id}` : "/vendas";
    case "ver_locacao":
      return id ? `/locacoes/${id}` : "/locacoes";
    case "nova_locacao":
      return id ? `/locacoes/nova?cliente=${id}` : "/locacoes/nova";
  }
}

const texto = z.string().trim();

/** Só o que a API exige para salvar; formato de CPF, CNH e CEP é conferido pela API e o erro volta no campo. */
export const esquemaCliente = z.object({
  tipo: z.enum(["pf", "pj"]),
  nome: texto.min(1, "Informe o nome"),
  documento: texto.min(1, "Informe o documento"),
  celular: texto.min(1, "Informe o celular"),
  nascimento: texto,
  email: texto,
  profissao: texto,
  cnh: z.object({ numero: texto, categoria: texto, validade: texto, primeira_habilitacao: texto }),
  responsavel: z.object({ nome: texto, cpf: texto, celular: texto }),
  endereco: z.object({ cep: texto, logradouro: texto, numero: texto, bairro: texto, cidade: texto, uf: texto }),
  referencia: z.object({ nome: texto, parentesco: texto, telefone: texto }),
  consentimento: z.boolean(),
});
export type ValoresCliente = z.infer<typeof esquemaCliente>;

export const VALORES_INICIAIS: ValoresCliente = {
  tipo: "pf",
  nome: "",
  documento: "",
  celular: "",
  nascimento: "",
  email: "",
  profissao: "",
  cnh: { numero: "", categoria: "", validade: "", primeira_habilitacao: "" },
  responsavel: { nome: "", cpf: "", celular: "" },
  endereco: { cep: "", logradouro: "", numero: "", bairro: "", cidade: "", uf: "" },
  referencia: { nome: "", parentesco: "", telefone: "" },
  consentimento: false,
};

const preenchido = (o: Record<string, string>) => Object.values(o).some((v) => v !== "");
function semVazios<T extends Record<string, string>>(o: T): Partial<T> {
  return Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "")) as Partial<T>;
}

/** Corpo do POST /api/clientes/: só dígitos em documento e telefones, e blocos vazios ficam de fora. */
export function paraCorpo(v: ValoresCliente): NovoCliente {
  const pj = v.tipo === "pj";
  const corpo: NovoCliente = { tipo: v.tipo, nome: v.nome.trim(), documento: soDigitos(v.documento), celular: soDigitos(v.celular) };
  if (!pj && v.nascimento) corpo.nascimento = v.nascimento;
  if (v.email) corpo.email = v.email;
  if (v.profissao) corpo.profissao = v.profissao;
  if (preenchido(v.cnh)) corpo.cnh = semVazios(v.cnh);
  if (pj && preenchido(v.responsavel)) {
    corpo.responsavel = semVazios({ nome: v.responsavel.nome, cpf: soDigitos(v.responsavel.cpf), celular: soDigitos(v.responsavel.celular) });
  }
  if (preenchido(v.endereco)) corpo.endereco = semVazios({ ...v.endereco, cep: soDigitos(v.endereco.cep), uf: v.endereco.uf.toUpperCase() });
  if (preenchido(v.referencia)) corpo.referencia = semVazios({ ...v.referencia, telefone: soDigitos(v.referencia.telefone) });
  if (v.consentimento) corpo.consentimento = true;
  return corpo;
}

export const ROTULO_PENDENCIA: Record<string, string> = {
  cnh_frente: "CNH (frente)",
  cnh_verso: "CNH (verso)",
  selfie_documento: "selfie com documento",
  comprovante_residencia: "comprovante de residência",
  consentimento: "autorização de uso dos dados",
  cnh: "dados da CNH",
  endereco: "endereço",
  referencia: "referência pessoal",
  nascimento: "data de nascimento",
  responsavel: "responsável pela empresa",
};

/** "Faltam a selfie e o comprovante para liberar a locação." a partir de `pendencias` da API. */
export function textoDePendencias(pendencias: string[]): string | null {
  const nomes = pendencias.map((p) => ROTULO_PENDENCIA[p] ?? p);
  const ultimo = nomes.pop();
  if (!ultimo) return null;
  return nomes.length ? `Faltam ${nomes.join(", ")} e ${ultimo} para liberar a locação.` : `Falta ${ultimo} para liberar a locação.`;
}
