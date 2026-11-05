import { z } from "zod";
import type { CombustivelDoVeiculo, DocumentoDoVeiculo, DocumentoDoVeiculoEntrada, EdicaoVeiculo, EspecieDoVeiculo, NovoVeiculo, RastreadorEntrada, VeiculoDetalhe } from "@/lib/api";

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
  crlv_validade: texto,
  // VEI-09: todos opcionais. O formato (faixa, tamanho, letras) é conferido pela API e o erro volta no campo.
  combustivel: texto,
  potencia_cv: texto,
  cilindrada_cc: texto,
  especie: texto,
  tipo_documento: texto,
  carroceria: texto,
  lotacao: texto,
  peso_bruto_kg: texto,
  numero_motor: texto,
  observacoes_crlv: texto,
  rastreador_numero: texto,
  rastreador_empresa: texto,
  anotacoes: texto,
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
  crlv_validade: "",
  combustivel: "",
  potencia_cv: "",
  cilindrada_cc: "",
  especie: "",
  tipo_documento: "",
  carroceria: "",
  lotacao: "",
  peso_bruto_kg: "",
  numero_motor: "",
  observacoes_crlv: "",
  rastreador_numero: "",
  rastreador_empresa: "",
  anotacoes: "",
};

/** Rótulos da tela (docs/api/veiculos.md, "Na representação"). */
export const COMBUSTIVEIS: { valor: CombustivelDoVeiculo; rotulo: string }[] = [
  { valor: "gasolina", rotulo: "Gasolina" },
  { valor: "etanol", rotulo: "Etanol" },
  { valor: "flex", rotulo: "Flex" },
  { valor: "diesel", rotulo: "Diesel" },
  { valor: "eletrico", rotulo: "Elétrico" },
  { valor: "hibrido", rotulo: "Híbrido" },
];
export const ESPECIES: { valor: EspecieDoVeiculo; rotulo: string }[] = [
  { valor: "passageiro", rotulo: "Passageiro" },
  { valor: "carga", rotulo: "Carga" },
  { valor: "misto", rotulo: "Misto" },
  { valor: "competicao", rotulo: "Competição" },
  { valor: "tracao", rotulo: "Tração" },
  { valor: "especial", rotulo: "Especial" },
  { valor: "colecao", rotulo: "Coleção" },
];
export const rotuloDoCombustivel = (c: string | null | undefined) => COMBUSTIVEIS.find((x) => x.valor === c)?.rotulo ?? null;
export const rotuloDaEspecie = (e: string | null | undefined) => ESPECIES.find((x) => x.valor === e)?.rotulo ?? null;

/** VEI-09: campo da tela ↔ chave pontuada da API (corpo, erro 400 e `lidos` da leitura). */
export const CAMPOS_VEI_09 = [
  { nome: "potencia_cv", chave: "documento.potencia_cv", inteiro: true },
  { nome: "cilindrada_cc", chave: "documento.cilindrada_cc", inteiro: true },
  { nome: "especie", chave: "documento.especie" },
  { nome: "tipo_documento", chave: "documento.tipo" },
  { nome: "carroceria", chave: "documento.carroceria" },
  { nome: "lotacao", chave: "documento.lotacao", inteiro: true },
  { nome: "peso_bruto_kg", chave: "documento.peso_bruto_kg", inteiro: true },
  { nome: "numero_motor", chave: "documento.numero_motor", soAdminEGerente: true, maiusculas: true },
  { nome: "observacoes_crlv", chave: "documento.observacoes", soAdminEGerente: true },
  { nome: "rastreador_numero", chave: "rastreador.numero", maiusculas: true },
  { nome: "rastreador_empresa", chave: "rastreador.empresa" },
  { nome: "anotacoes", chave: "anotacoes" },
] as const satisfies readonly { nome: keyof ValoresVeiculo; chave: string; inteiro?: boolean; soAdminEGerente?: boolean; maiusculas?: boolean }[];

type CampoVei09 = (typeof CAMPOS_VEI_09)[number];

/** Chave da API (`documento.potencia_cv`, `valor_compra_centavos`) → campo da tela, para mostrar o erro 400 no campo certo. */
export const NOME_DO_CAMPO_DA_API: Record<string, keyof ValoresVeiculo> = {
  valor_compra_centavos: "valor_compra",
  ...Object.fromEntries(CAMPOS_VEI_09.map((c) => [c.chave, c.nome])),
};

/** Inteiro vai como número; texto que não é inteiro vai como veio, e a API recusa no campo ("Informe a potência em cv, de 1 a 999."). */
function inteiroOuTexto(t: string): number {
  return (/^\d+$/.test(t) ? Number(t) : t) as number;
}

type Blocos = { documento?: DocumentoDoVeiculoEntrada; rastreador?: RastreadorEntrada; anotacoes?: string | null };

/**
 * Os blocos `documento`, `rastreador` e `anotacoes` do corpo (VEI-09). No cadastro só entra o que tem valor; no editar entra tudo
 * (vazio vai `null` e apaga), menos o motor e as observações quando a API não os mostrou: sem eles na ficha, a tela não os envia.
 */
function blocosVei09(v: ValoresVeiculo, editar: boolean, comMotorEObservacoes: boolean): Blocos {
  const documento: Record<string, unknown> = {};
  const rastreador: Record<string, unknown> = {};
  for (const c of CAMPOS_VEI_09 as readonly CampoVei09[]) {
    if ("soAdminEGerente" in c && !comMotorEObservacoes) continue;
    if (c.chave === "anotacoes") continue;
    const texto = v[c.nome].trim();
    if (!editar && !texto) continue;
    let valor: unknown = null;
    if (texto) valor = "inteiro" in c ? inteiroOuTexto(texto) : "maiusculas" in c ? texto.replace(/\s/g, "").toUpperCase() : texto;
    if (c.chave.startsWith("documento.")) documento[c.chave.slice("documento.".length)] = valor;
    else rastreador[c.chave.slice("rastreador.".length)] = valor;
  }
  const corpo: Blocos = {};
  if (Object.keys(documento).length) corpo.documento = documento as DocumentoDoVeiculoEntrada;
  if (Object.keys(rastreador).length) corpo.rastreador = rastreador as RastreadorEntrada;
  const anotacoes = v.anotacoes.trim();
  if (anotacoes) corpo.anotacoes = anotacoes;
  else if (editar) corpo.anotacoes = null;
  return corpo;
}

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
  if (v.combustivel) corpo.combustivel = v.combustivel as CombustivelDoVeiculo;
  const { anotacoes, ...blocos } = blocosVei09(v, false, true);
  Object.assign(corpo, blocos);
  if (anotacoes) corpo.anotacoes = anotacoes;
  return corpo;
}

/** Centavos no texto do campo ("1.390.000" → "13.900,00"): só a forma de editar; o valor é o que a API devolveu. */
export function textoDeCentavos(centavos: number): string {
  const [inteiro = "0", frac = "00"] = (centavos / 100).toFixed(2).split(".");
  return `${inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${frac}`;
}

/** Ficha da API → campos da edição. Placa, chassi, km e filial entram só para mostrar (a API não os muda no PATCH). */
export function valoresDoVeiculo(v: VeiculoDetalhe): ValoresVeiculo {
  return {
    tipo: v.tipo_veiculo,
    placa: v.placa,
    marca: v.marca,
    modelo: v.modelo,
    ano_fabricacao: String(v.ano_fabricacao),
    ano_modelo: String(v.ano_modelo),
    chassi: v.chassi,
    renavam: v.renavam ?? "",
    cor: v.cor,
    km_atual: String(v.km_atual),
    filial_id: String(v.filial.id),
    categoria_id: String(v.categoria.id),
    capacidade_tanque_litros: v.capacidade_tanque_litros ?? "",
    data_compra: v.data_compra ?? "",
    valor_compra: v.valor_compra_centavos != null ? textoDeCentavos(v.valor_compra_centavos) : "",
    crlv_validade: "",
    combustivel: v.combustivel ?? "",
    potencia_cv: numeroNoCampo(v.documento.potencia_cv),
    cilindrada_cc: numeroNoCampo(v.documento.cilindrada_cc),
    especie: v.documento.especie ?? "",
    tipo_documento: v.documento.tipo ?? "",
    carroceria: v.documento.carroceria ?? "",
    lotacao: numeroNoCampo(v.documento.lotacao),
    peso_bruto_kg: numeroNoCampo(v.documento.peso_bruto_kg),
    numero_motor: v.documento.numero_motor ?? "",
    observacoes_crlv: v.documento.observacoes ?? "",
    rastreador_numero: v.rastreador.numero ?? "",
    rastreador_empresa: v.rastreador.empresa ?? "",
    anotacoes: v.anotacoes ?? "",
  };
}

const numeroNoCampo = (n: number | null | undefined) => (n == null ? "" : String(n));

/** O número do motor e as observações só estão no `documento` para administrador e gerente (CA-421-12). */
export const temMotorEObservacoes = (d: DocumentoDoVeiculo) => "numero_motor" in d || "observacoes" in d;

/** Corpo do PATCH: só os campos que a API aceita; opcional apagado vai como `null` para limpar. */
export function paraCorpoEdicao(v: ValoresVeiculo, opcoes: { comMotorEObservacoes?: boolean; leitura?: string } = {}): EdicaoVeiculo {
  const compra = v.valor_compra ? centavosDoTexto(v.valor_compra) : null;
  return {
    marca: v.marca.trim(),
    modelo: v.modelo.trim(),
    ano_fabricacao: Number(v.ano_fabricacao),
    ano_modelo: Number(v.ano_modelo),
    cor: v.cor.trim(),
    categoria_id: Number(v.categoria_id),
    renavam: v.renavam ? v.renavam.replace(/\D/g, "") : null,
    capacidade_tanque_litros: v.capacidade_tanque_litros ? v.capacidade_tanque_litros.replace(",", ".") : null,
    data_compra: v.data_compra || null,
    valor_compra_centavos: compra,
    combustivel: v.combustivel ? (v.combustivel as CombustivelDoVeiculo) : null,
    ...blocosVei09(v, true, opcoes.comMotorEObservacoes ?? false),
    ...(opcoes.leitura ? { leitura: opcoes.leitura } : {}),
  };
}

/** Campos da leitura que têm campo próprio no formulário, com a chave da API em `campos` e `lidos`. Rastreador e anotações nunca vêm da leitura (CA-421-04). */
const CAMPOS_DA_LEITURA = [
  ...(["placa", "chassi", "renavam", "marca", "modelo", "ano_fabricacao", "ano_modelo", "cor", "combustivel"] as const).map((nome) => ({ nome, chave: nome as string })),
  ...CAMPOS_VEI_09.filter((c) => c.chave.startsWith("documento.")).map((c) => ({ nome: c.nome, chave: c.chave as string })),
];
export type CampoLido = "placa" | "chassi" | "renavam" | "marca" | "modelo" | "ano_fabricacao" | "ano_modelo" | "cor" | "combustivel" | "potencia_cv" | "cilindrada_cc" | "especie" | "tipo_documento" | "carroceria" | "lotacao" | "peso_bruto_kg" | "numero_motor" | "observacoes_crlv";

/** O que a API leu → valores do formulário. Só entram os campos de `lidos`; o resto da tela não muda (VEI-08, VEI-09). */
export function valoresDaLeitura(l: { campos: object; lidos: string[] }): { valores: Partial<Pick<ValoresVeiculo, CampoLido>>; lidos: CampoLido[] } {
  const campos = l.campos as Record<string, unknown>;
  const valores: Partial<Pick<ValoresVeiculo, CampoLido>> = {};
  const lidos: CampoLido[] = [];
  for (const { nome, chave } of CAMPOS_DA_LEITURA) {
    const valor = campos[chave];
    if (!l.lidos.includes(chave) || valor === null || valor === undefined) continue;
    valores[nome as CampoLido] = String(valor);
    lidos.push(nome as CampoLido);
  }
  return { valores, lidos };
}
