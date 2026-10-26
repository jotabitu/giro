// Modelos de contrato sem backend: o seed da Moto Rápida e as regras do contrato (IMP-04, S-09, LOC-15; docs/api/contratos.md).
import { ErroApi } from "@/lib/api/tipos";
import type { CorpoDaEdicaoDoModelo, CorpoDoNovoModelo, MarcadorDeContrato, ModeloDeContrato, ModeloDeContratoDaLista, ModeloProntoDeContrato } from "@/lib/api/tipos-contratos";
import { pausa } from "./falso";

const M = (chave: string, rotulo: string, exemplo: string): MarcadorDeContrato => ({ chave, rotulo, exemplo });

export const MARCADORES: MarcadorDeContrato[] = [
  M("empresa.nome", "Nome da empresa", "Moto Rápida"),
  M("empresa.razao_social", "Razão social", "Moto Rápida Locações Ltda"),
  M("empresa.cnpj", "CNPJ da empresa", "12.345.678/0001-95"),
  M("empresa.endereco", "Endereço da empresa", "Av. Beira Mar, 1200"),
  M("empresa.cidade", "Cidade da empresa", "Fortaleza"),
  M("filial.nome", "Nome da filial", "Filial Centro"),
  M("cliente.nome", "Nome do cliente", "Lucas Ferreira"),
  M("cliente.cpf", "CPF do cliente", "123.456.789-09"),
  M("cliente.nascimento", "Nascimento do cliente", "14/03/1994"),
  M("cliente.endereco", "Endereço do cliente", "Rua das Flores, 45"),
  M("cliente.celular", "Celular do cliente", "(85) 98877-6655"),
  M("cliente.cnh_numero", "Número da CNH", "04512345678"),
  M("veiculo.marca", "Marca do veículo", "Honda"),
  M("veiculo.modelo", "Modelo do veículo", "CG 160 Fan"),
  M("veiculo.placa", "Placa", "QXA4B21"),
  M("veiculo.chassi", "Chassi", "9C2KC2210PR004401"),
  M("locacao.codigo", "Código da locação", "LOC-2841"),
  M("locacao.inicio", "Início da locação", "07/10/2026"),
  M("locacao.fim_previsto", "Fim previsto", "14/10/2026"),
  M("locacao.valor", "Valor por período", "R$ 329,00"),
  M("locacao.caucao", "Caução", "R$ 300,00"),
  M("locacao.parcelas", "Tabela de vencimentos", "07/10 · R$ 329,00"),
  M("cobranca.multa_atraso_pct", "Multa por atraso (%)", "2,00"),
  M("cobranca.juros_mes_pct", "Juros ao mês (%)", "1,00"),
  M("contrato.data", "Data do contrato", "07/10/2026"),
  M("contrato.cidade_assinatura", "Cidade da assinatura", "Fortaleza"),
];

const PRONTOS: ModeloProntoDeContrato[] = [
  ["locacao_semanal_moto", "Locação semanal de moto", "semana"],
  ["locacao_diaria_moto", "Locação diária de moto", "dia"],
  ["locacao_mensal_moto", "Locação mensal de moto", "mês"],
  ["locacao_semanal_carro", "Locação semanal de carro", "semana"],
].map(([chave, nome, periodo]) => ({
  chave: chave!,
  nome: nome!,
  texto: `<h1>CONTRATO DE ${nome!.toUpperCase()}</h1><p><strong>Locadora:</strong> {{empresa.nome}}, CNPJ {{empresa.cnpj}}.</p><p><strong>Locatário:</strong> {{cliente.nome}}, CPF {{cliente.cpf}}.</p><p><strong>Cláusula 1.</strong> Locação do veículo {{veiculo.modelo}}, placa {{veiculo.placa}}, a partir de {{locacao.inicio}}, por {{locacao.valor}} por ${periodo!}.</p><p><strong>Cláusula 2.</strong> Caução de {{locacao.caucao}}. Multa de {{cobranca.multa_atraso_pct}}% e juros de {{cobranca.juros_mes_pct}}% ao mês em caso de atraso.</p>`,
}));

type Interno = ModeloDeContrato & { textoPublicado: string };

const TEXTO_SEMANAL = PRONTOS[0]!.texto;

function semente(): Interno[] {
  return [
    {
      id: 10,
      grupo: "00000000-0000-4000-8000-000000000010",
      nome: "Locação semanal",
      finalidade: "locacao",
      versao_publicada: 3,
      tem_rascunho: false,
      status: "publicado",
      arquivado: false,
      contratos_gerados: 38,
      editado_em: "2026-10-01T12:00:00Z",
      texto: TEXTO_SEMANAL,
      textoPublicado: TEXTO_SEMANAL,
      marcadores_usados: usados(TEXTO_SEMANAL),
      versoes: [
        { versao: 3, publicado_em: "2026-10-01T12:00:00Z", contratos_gerados: 38 },
        { versao: 2, publicado_em: "2026-09-10T12:00:00Z", contratos_gerados: 0 },
        { versao: 1, publicado_em: "2026-08-20T12:00:00Z", contratos_gerados: 0 },
      ],
    },
    {
      id: 11,
      grupo: "00000000-0000-4000-8000-000000000011",
      nome: "Compra e venda parcelada",
      finalidade: "venda",
      versao_publicada: 1,
      tem_rascunho: false,
      status: "publicado",
      arquivado: false,
      contratos_gerados: 3,
      editado_em: "2026-09-20T12:00:00Z",
      texto: "<p>Contrato de compra e venda de {{veiculo.modelo}}.</p>",
      textoPublicado: "<p>Contrato de compra e venda de {{veiculo.modelo}}.</p>",
      marcadores_usados: ["veiculo.modelo"],
      versoes: [{ versao: 1, publicado_em: "2026-09-20T12:00:00Z", contratos_gerados: 3 }],
    },
  ];
}

function usados(texto: string): string[] {
  return [...new Set([...texto.matchAll(/\{\{([a-z_]+\.[a-z_]+)\}\}/g)].map((m) => m[1]!))];
}

let modelos = semente();
let proximoId = 100;

/** Volta ao seed entre os testes. */
export function definirModelosFalsos() {
  modelos = semente();
  proximoId = 100;
}

function conferirMarcadores(texto: string) {
  const validos = new Set(MARCADORES.map((m) => m.chave));
  const ruim = usados(texto).find((c) => !validos.has(c));
  if (ruim) {
    throw new ErroApi(400, "marcador_invalido", `Campo desconhecido: {{${ruim}}}`, undefined, { texto: `Campo desconhecido: {{${ruim}}}` });
  }
}

function achar(id: number): Interno {
  const m = modelos.find((x) => x.id === id);
  if (!m) throw new ErroApi(404, "nao_encontrado", "Modelo não encontrado");
  return m;
}

const publico = (m: Interno): ModeloDeContrato => {
  const copia: Partial<Interno> = { ...m };
  delete copia.textoPublicado;
  return copia as ModeloDeContrato;
};
const resumo = (m: Interno): ModeloDeContratoDaLista => ({
  id: m.id,
  grupo: m.grupo,
  nome: m.nome,
  finalidade: m.finalidade,
  versao_publicada: m.versao_publicada,
  tem_rascunho: m.tem_rascunho,
  status: m.status,
  arquivado: m.arquivado,
  contratos_gerados: m.contratos_gerados,
  editado_em: m.editado_em,
});

export const modelosContratoFalso = {
  async listar(): Promise<ModeloDeContratoDaLista[]> {
    await pausa(40);
    return modelos.map(resumo);
  },

  async obter(id: number): Promise<ModeloDeContrato> {
    await pausa(40);
    return publico(achar(id));
  },

  async marcadores(): Promise<MarcadorDeContrato[]> {
    await pausa(40);
    return MARCADORES;
  },

  async prontos(): Promise<ModeloProntoDeContrato[]> {
    await pausa(40);
    return PRONTOS;
  },

  async criar(corpo: CorpoDoNovoModelo): Promise<ModeloDeContrato> {
    await pausa(40);
    const pronto = corpo.a_partir_de ? PRONTOS.find((p) => p.chave === corpo.a_partir_de) : undefined;
    if (corpo.a_partir_de && !pronto) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { a_partir_de: "Modelo pronto desconhecido" });
    const nome = (corpo.nome ?? pronto?.nome ?? "").trim();
    if (!nome) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { nome: "Informe o nome do modelo" });
    const texto = pronto?.texto ?? corpo.texto ?? "";
    conferirMarcadores(texto);
    const id = proximoId++;
    const novo: Interno = {
      id,
      grupo: `00000000-0000-4000-8000-${String(id).padStart(12, "0")}`,
      nome,
      finalidade: corpo.finalidade ?? "locacao",
      versao_publicada: null,
      tem_rascunho: true,
      status: "rascunho",
      arquivado: false,
      contratos_gerados: 0,
      editado_em: "2026-10-07T15:00:00Z",
      texto,
      textoPublicado: "",
      marcadores_usados: usados(texto),
      versoes: [],
    };
    modelos.push(novo);
    return publico(novo);
  },

  async alterar(id: number, corpo: CorpoDaEdicaoDoModelo): Promise<ModeloDeContrato> {
    await pausa(40);
    const m = achar(id);
    if (corpo.texto !== undefined) {
      conferirMarcadores(corpo.texto);
      m.texto = corpo.texto;
      m.marcadores_usados = usados(corpo.texto);
      m.tem_rascunho = true;
    }
    if (corpo.nome !== undefined) m.nome = corpo.nome.trim() || m.nome;
    m.editado_em = "2026-10-07T15:00:00Z";
    return publico(m);
  },

  async previa(id: number): Promise<string> {
    await pausa(40);
    const m = achar(id);
    return m.texto.replace(/\{\{([a-z_]+\.[a-z_]+)\}\}/g, (_x, chave: string) => MARCADORES.find((k) => k.chave === chave)?.exemplo ?? "");
  },

  async publicar(id: number): Promise<ModeloDeContrato> {
    await pausa(40);
    const m = achar(id);
    conferirMarcadores(m.texto);
    const versao = (m.versao_publicada ?? 0) + 1;
    m.versao_publicada = versao;
    m.textoPublicado = m.texto;
    m.tem_rascunho = false;
    m.status = "publicado";
    m.versoes = [{ versao, publicado_em: "2026-10-07T15:00:00Z", contratos_gerados: 0 }, ...m.versoes];
    return publico(m);
  },

  async arquivar(id: number): Promise<ModeloDeContrato> {
    await pausa(40);
    const m = achar(id);
    const outros = modelos.filter((x) => x.id !== id && x.finalidade === "locacao" && x.status === "publicado" && !x.arquivado);
    if (m.finalidade === "locacao" && m.status === "publicado" && outros.length === 0) {
      throw new ErroApi(422, "IMP-04", "A empresa precisa de ao menos um modelo de locação publicado");
    }
    m.arquivado = true;
    return publico(m);
  },
};
