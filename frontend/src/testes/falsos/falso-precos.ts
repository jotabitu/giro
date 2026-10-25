// Tabelas de preço sem backend: o seed de 07 out 2026 (docs/qa/criterios/T-013.md) e as regras do contrato
// (LOC-01, LOC-02, LOC-15; docs/api/veiculos.md "Categorias e preços", docs/api/locacoes.md "Planos especiais").
import { ErroApi } from "@/lib/api/tipos";
import type {
  CategoriaDePreco,
  CorpoDaCategoria,
  CorpoDoExtra,
  CorpoDoPlanoEspecial,
  CorpoDoPrecoComData,
  ExtraDePreco,
  MudancaDePreco,
  PlanoEspecialDePreco,
  PrecoDoHistorico,
  PrecoGravado,
} from "@/lib/api/tipos-precos";
import { pausa } from "./falso";

const HOJE = "2026-10-07";

type Estado = {
  categorias: CategoriaDePreco[];
  historicos: Record<number, PrecoDoHistorico[]>;
  extras: ExtraDePreco[];
  planos: PlanoEspecialDePreco[];
  proximoId: number;
};

const preco = (diaria: number, semanal: number, mensal: number, caucao: number, desde = "2026-10-01", por: string | null = "Mariana Costa"): PrecoDoHistorico => ({
  vigente_desde: desde,
  diaria_centavos: diaria,
  semanal_centavos: semanal,
  mensal_centavos: mensal,
  caucao_centavos: caucao,
  alterado_por: por,
  alterado_em: `${desde}T12:00:00Z`,
});

const MODELOS: Record<number, string> = { 1: "Pop 110i, Biz 125", 2: "CG 160, Factor 150", 3: "NMax 160", 4: "Kwid, Mobi" };
const VEICULOS: Record<number, number> = { 1: 42, 2: 32, 3: 6, 4: 6 };
const EM_ANDAMENTO: Record<number, number> = { 1: 12, 2: 9, 3: 2, 4: 3 };

function semente(): Estado {
  const historicos: Estado["historicos"] = {
    1: [preco(4490, 29940, 109000, 30000)],
    2: [preco(5490, 32900, 119000, 30000), preco(5490, 29940, 119000, 30000, "2026-01-01")],
    3: [preco(7990, 44900, 159000, 50000)],
    4: [preco(10900, 64900, 229000, 80000)],
  };
  const nomes: [number, string, "moto" | "carro"][] = [
    [1, "Urbana 110–125", "moto"],
    [2, "Street 150–160", "moto"],
    [3, "Scooter premium", "moto"],
    [4, "Carro compacto", "carro"],
  ];
  return {
    categorias: nomes.map(([id, nome, tipo]) => montar({ id, nome, tipo_veiculo: tipo, filial: null, ativo: true, modelos_resumo: MODELOS[id]!, veiculos: VEICULOS[id]! }, historicos[id]!)),
    historicos,
    extras: [
      { id: 1, nome: "Capacete extra", valor_centavos: 1500, cobranca: "por_periodo", ativo: true },
      { id: 2, nome: "Cadeado", valor_centavos: 800, cobranca: "unica", ativo: true },
    ],
    planos: [
      {
        id: 1,
        nome: "Entregador",
        periodicidade: "semanal",
        regra: "preco_fixo",
        preco_centavos: 27900,
        desconto_pct: null,
        a_partir_do_periodo: null,
        categorias: [],
        condicoes: "Semanal com km livre e troca de óleo inclusa",
        locacoes_ativas: 18,
        ativo: true,
      },
      {
        id: 2,
        nome: "Mensal fidelidade",
        periodicidade: "mensal",
        regra: "desconto",
        preco_centavos: null,
        desconto_pct: "10.00",
        a_partir_do_periodo: 3,
        categorias: [],
        condicoes: "3 meses seguidos ganham 10% de desconto",
        locacoes_ativas: 7,
        ativo: true,
      },
    ],
    proximoId: 100,
  };
}

/** Preço vigente hoje e o próximo agendado, como `GET /api/categorias/` devolve. */
function montar(base: Omit<CategoriaDePreco, "preco_vigente" | "proximo_preco">, historico: PrecoDoHistorico[]): CategoriaDePreco {
  const comData = (p: PrecoDoHistorico) => ({ vigente_desde: p.vigente_desde, diaria_centavos: p.diaria_centavos, semanal_centavos: p.semanal_centavos, mensal_centavos: p.mensal_centavos, caucao_centavos: p.caucao_centavos });
  const vigente = historico.filter((p) => p.vigente_desde <= HOJE).sort((a, b) => b.vigente_desde.localeCompare(a.vigente_desde))[0];
  const proximo = historico.filter((p) => p.vigente_desde > HOJE).sort((a, b) => a.vigente_desde.localeCompare(b.vigente_desde))[0];
  return { ...base, preco_vigente: vigente ? comData(vigente) : null, proximo_preco: proximo ? comData(proximo) : null };
}

let estado = semente();

/** Volta ao seed (ou ao estado dado) entre os testes. */
export function definirPrecosFalsos(novo: Estado | null) {
  estado = novo ?? semente();
}
export const precosDoSeed = semente;

const campo = (nome: string, mensagem: string) => new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { [nome]: mensagem });

function achar(id: number): CategoriaDePreco {
  const c = estado.categorias.find((x) => x.id === id);
  if (!c) throw new ErroApi(404, "nao_encontrado", "Categoria não encontrada");
  return c;
}

function recalcular(id: number) {
  const i = estado.categorias.findIndex((c) => c.id === id);
  const base = { ...estado.categorias[i]! };
  delete base.preco_vigente;
  delete base.proximo_preco;
  estado.categorias[i] = montar(base, estado.historicos[id] ?? []);
}

function conferirPreco(p: CorpoDoPrecoComData) {
  for (const k of ["diaria_centavos", "semanal_centavos", "mensal_centavos", "caucao_centavos"] as const) {
    if (!Number.isInteger(p[k]) || p[k] < 0) throw campo(k, "Informe um valor");
  }
}

function gravar(id: number, corpo: CorpoDoPrecoComData, trocando: boolean): PrecoGravado {
  conferirPreco(corpo);
  const desde = corpo.vigente_desde ?? HOJE;
  const lista = (estado.historicos[id] ??= []);
  const existente = lista.find((p) => p.vigente_desde === desde);
  if (!trocando && existente) throw new ErroApi(409, "preco_ja_definido", "Já existe preço a partir desta data");
  if (desde < HOJE && !trocando) throw campo("vigente_desde", "O passado não se reescreve. Escolha hoje ou uma data futura.");
  if (trocando) {
    if (!existente) throw new ErroApi(404, "nao_encontrado", "Não há preço agendado nesta data");
    if (desde <= HOJE) throw new ErroApi(409, "preco_ja_vigente", "Este preço já está valendo e não pode ser trocado");
    lista.splice(lista.indexOf(existente), 1);
  } else if (existente) {
    throw new ErroApi(409, "preco_ja_definido", "Já existe preço a partir desta data");
  }
  const novo: PrecoDoHistorico = {
    vigente_desde: desde,
    diaria_centavos: corpo.diaria_centavos,
    semanal_centavos: corpo.semanal_centavos,
    mensal_centavos: corpo.mensal_centavos,
    caucao_centavos: corpo.caucao_centavos,
    alterado_por: "Mariana Costa",
    alterado_em: `${HOJE}T15:00:00Z`,
  };
  lista.push(novo);
  lista.sort((a, b) => b.vigente_desde.localeCompare(a.vigente_desde));
  recalcular(id);
  return { ...novo, locacoes_em_andamento_mantidas: EM_ANDAMENTO[id] ?? 0 };
}

export const precosFalso = {
  async categorias(f: { filial?: number; ativo?: boolean } = {}): Promise<CategoriaDePreco[]> {
    await pausa(40);
    return estado.categorias.filter((c) => (f.ativo === undefined || c.ativo === f.ativo) && (f.filial === undefined || c.filial === null || c.filial.id === f.filial));
  },

  async criarCategoria(corpo: CorpoDaCategoria): Promise<CategoriaDePreco> {
    await pausa(40);
    if (!corpo.nome.trim()) throw campo("nome", "Informe o nome da categoria");
    if (estado.categorias.some((c) => c.nome.toLowerCase() === corpo.nome.trim().toLowerCase() && (c.filial?.id ?? null) === (corpo.filial_id ?? null))) {
      throw new ErroApi(409, "categoria_nome_em_uso", "Já existe uma categoria com este nome nesta filial");
    }
    if (!corpo.preco) throw campo("preco", "Informe o primeiro preço");
    conferirPreco(corpo.preco);
    const id = estado.proximoId++;
    estado.historicos[id] = [{ ...corpo.preco, vigente_desde: HOJE, alterado_por: "Mariana Costa", alterado_em: `${HOJE}T15:00:00Z` }];
    estado.categorias.push(
      montar({ id, nome: corpo.nome.trim(), tipo_veiculo: corpo.tipo_veiculo, filial: corpo.filial_id ? { id: corpo.filial_id, nome: "Filial" } : null, ativo: true, modelos_resumo: "", veiculos: 0 }, estado.historicos[id]),
    );
    return achar(id);
  },

  async alterarCategoria(id: number, corpo: Partial<Omit<CorpoDaCategoria, "preco">>): Promise<CategoriaDePreco> {
    await pausa(40);
    const c = achar(id);
    if (corpo.nome !== undefined && estado.categorias.some((x) => x.id !== id && x.nome.toLowerCase() === corpo.nome!.trim().toLowerCase() && x.filial?.id === c.filial?.id)) {
      throw new ErroApi(409, "categoria_nome_em_uso", "Já existe uma categoria com este nome nesta filial");
    }
    if (c.veiculos > 0 && corpo.tipo_veiculo !== undefined && corpo.tipo_veiculo !== c.tipo_veiculo) {
      throw new ErroApi(422, "categoria_com_veiculos", "A categoria tem veículos. Mude o tipo só em categoria sem veículos.");
    }
    Object.assign(c, { nome: corpo.nome?.trim() ?? c.nome, tipo_veiculo: corpo.tipo_veiculo ?? c.tipo_veiculo });
    return c;
  },

  async desativarCategoria(id: number): Promise<CategoriaDePreco> {
    await pausa(40);
    const c = achar(id);
    if (c.veiculos > 0) throw new ErroApi(422, "categoria_com_veiculos", "A categoria ainda tem veículos ativos. Mude os veículos de categoria antes.");
    c.ativo = false;
    return c;
  },

  async reativarCategoria(id: number): Promise<CategoriaDePreco> {
    await pausa(40);
    const c = achar(id);
    c.ativo = true;
    return c;
  },

  async historicoDaCategoria(id: number): Promise<PrecoDoHistorico[]> {
    await pausa(40);
    achar(id);
    return [...(estado.historicos[id] ?? [])];
  },

  async definirPreco(id: number, corpo: CorpoDoPrecoComData): Promise<PrecoGravado> {
    await pausa(40);
    achar(id);
    return gravar(id, corpo, false);
  },

  async trocarPrecoAgendado(id: number, vigenteDesde: string, corpo: CorpoDoPrecoComData): Promise<PrecoGravado> {
    await pausa(40);
    achar(id);
    return gravar(id, { ...corpo, vigente_desde: vigenteDesde }, true);
  },

  async historico(): Promise<MudancaDePreco[]> {
    await pausa(40);
    const campos = [
      ["diaria_centavos", "diária"],
      ["semanal_centavos", "semanal"],
      ["mensal_centavos", "mensal"],
      ["caucao_centavos", "caução"],
    ] as const;
    const saida: MudancaDePreco[] = [];
    for (const c of estado.categorias) {
      const lista = [...(estado.historicos[c.id] ?? [])].sort((a, b) => a.vigente_desde.localeCompare(b.vigente_desde));
      lista.forEach((p, i) => {
        const antes = lista[i - 1];
        for (const [chave, rotulo] of campos) {
          if (antes && antes[chave] !== p[chave]) {
            saida.push({ categoria: { id: c.id, nome: c.nome }, vigente_desde: p.vigente_desde, campo: rotulo, antes_centavos: antes[chave], depois_centavos: p[chave], alterado_por: p.alterado_por, alterado_em: p.alterado_em });
          }
        }
      });
    }
    return saida.sort((a, b) => b.alterado_em.localeCompare(a.alterado_em));
  },

  async extras(f: { ativo?: boolean } = {}): Promise<ExtraDePreco[]> {
    await pausa(40);
    return estado.extras.filter((e) => f.ativo === undefined || e.ativo === f.ativo);
  },

  async criarExtra(corpo: CorpoDoExtra): Promise<ExtraDePreco> {
    await pausa(40);
    if (!corpo.nome.trim()) throw campo("nome", "Informe o nome do extra");
    if (!Number.isInteger(corpo.valor_centavos) || corpo.valor_centavos <= 0) throw campo("valor_centavos", "Informe o valor");
    const extra: ExtraDePreco = { id: estado.proximoId++, nome: corpo.nome.trim(), valor_centavos: corpo.valor_centavos, cobranca: corpo.cobranca, ativo: true };
    estado.extras.push(extra);
    return extra;
  },

  async alterarExtra(id: number, corpo: Partial<CorpoDoExtra>): Promise<ExtraDePreco> {
    await pausa(40);
    const e = estado.extras.find((x) => x.id === id);
    if (!e) throw new ErroApi(404, "nao_encontrado", "Extra não encontrado");
    if (corpo.valor_centavos !== undefined && (!Number.isInteger(corpo.valor_centavos) || corpo.valor_centavos <= 0)) throw campo("valor_centavos", "Informe o valor");
    Object.assign(e, corpo, corpo.nome !== undefined ? { nome: corpo.nome.trim() } : {});
    return e;
  },

  async desativarExtra(id: number): Promise<ExtraDePreco> {
    await pausa(40);
    const e = estado.extras.find((x) => x.id === id);
    if (!e) throw new ErroApi(404, "nao_encontrado", "Extra não encontrado");
    e.ativo = false;
    return e;
  },

  async planosEspeciais(f: { ativo?: boolean | "todos" } = {}): Promise<PlanoEspecialDePreco[]> {
    await pausa(40);
    return estado.planos.filter((p) => f.ativo === "todos" || p.ativo === (f.ativo ?? true));
  },

  async criarPlanoEspecial(corpo: CorpoDoPlanoEspecial): Promise<PlanoEspecialDePreco> {
    await pausa(40);
    if (!corpo.nome.trim()) throw campo("nome", "Informe o nome do plano");
    const plano: PlanoEspecialDePreco = {
      id: estado.proximoId++,
      nome: corpo.nome.trim(),
      periodicidade: corpo.periodicidade,
      regra: corpo.regra,
      preco_centavos: corpo.preco_centavos ?? null,
      desconto_pct: corpo.desconto_pct ?? null,
      a_partir_do_periodo: corpo.a_partir_do_periodo ?? null,
      categorias: [],
      condicoes: corpo.condicoes,
      locacoes_ativas: 0,
      ativo: true,
    };
    estado.planos.push(plano);
    return plano;
  },

  async alterarPlanoEspecial(id: number, corpo: Partial<CorpoDoPlanoEspecial>): Promise<PlanoEspecialDePreco> {
    await pausa(40);
    const p = estado.planos.find((x) => x.id === id);
    if (!p) throw new ErroApi(404, "nao_encontrado", "Plano não encontrado");
    const resto = { ...corpo };
    delete resto.categorias;
    Object.assign(p, resto);
    return p;
  },

  async desativarPlanoEspecial(id: number): Promise<PlanoEspecialDePreco> {
    await pausa(40);
    const p = estado.planos.find((x) => x.id === id);
    if (!p) throw new ErroApi(404, "nao_encontrado", "Plano não encontrado");
    p.ativo = false;
    return p;
  },
};
