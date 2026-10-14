// DADOS FALSOS de Administração › Filiais nos testes (docs/api/filiais.md). Só api-falsa.ts importa este arquivo.
// Seed da tela: só a Filial Centro (matriz), plano Profissional com 1 de 3 filiais. O seletor do menu (falso-filiais.ts)
// ainda lista a Aldeota; as telas de administração partem do seed da referência.
import { ErroApi } from "@/lib/api/tipos";
import type { CepEncontrado, CorpoDaFilial, FeriadoDaFilial, FeriadoNovo, FilialDaLista, FilialDetalhada, ListaFiliais, SugestaoDeFeriado } from "@/lib/api/tipos";
import { pausa } from "./falso";

const SEMANA = { abre: "08:00", fecha: "18:00" };
const HORARIO_PADRAO = { seg: [SEMANA], ter: [SEMANA], qua: [SEMANA], qui: [SEMANA], sex: [SEMANA], sab: [{ abre: "08:00", fecha: "12:00" }], dom: [] };
const LIMITE_DE_FILIAIS = 3;

function resumoDoHorario(h: CorpoDaFilial["horario"]): string {
  const hora = (t: string) => `${Number(t.slice(0, 2))}h`;
  const semana = h.seg.length ? `seg a sex ${hora(h.seg[0]!.abre)}–${hora(h.seg[0]!.fecha)}` : "";
  const sab = h.sab.length ? `sáb ${hora(h.sab[0]!.abre)}–${hora(h.sab[0]!.fecha)}` : "";
  return [semana, sab].filter(Boolean).join(" · ");
}

function montar(id: number, c: CorpoDaFilial, extra: Partial<FilialDaLista> = {}): FilialDaLista {
  return {
    id,
    nome: c.nome,
    matriz: c.matriz ?? false,
    ativo: true,
    cnpj: c.cnpj ?? null,
    inscricao_estadual: c.inscricao_estadual ?? null,
    inscricao_municipal: c.inscricao_municipal ?? null,
    endereco: { complemento: null, ...c.endereco },
    contato: { telefone: null, whatsapp: null, email: null, ...c.contato },
    preco_litro_centavos: c.preco_litro_centavos ?? null,
    horario: c.horario,
    horario_resumo: resumoDoHorario(c.horario),
    endereco_resumo: `${c.endereco.logradouro}, ${c.endereco.numero} · ${c.endereco.cidade}, ${c.endereco.uf}`,
    gerentes: [],
    feriados_proximos: [],
    feriados_ano_seguinte_pendentes: false,
    criado_em: "2026-10-07T13:00:00Z",
    indicadores: { veiculos: null, locacoes_ativas: null, usuarios: null, ocupacao_pct: null },
    ...extra,
  };
}

const CENTRO_SEED = montar(
  1,
  {
    nome: "Filial Centro",
    matriz: true,
    cnpj: "12345678000195",
    endereco: { cep: "60325000", logradouro: "Av. Bezerra de Menezes", numero: "1200", complemento: null, bairro: "São Gerardo", cidade: "Fortaleza", uf: "CE" },
    contato: { telefone: "8532123344", whatsapp: "85998124410", email: "centro@motorapida.com.br" },
    horario: HORARIO_PADRAO,
  },
  {
    gerentes: [{ id: 2, nome: "Rodrigo Pinheiro" }],
    feriados_proximos: [{ data: "2026-10-12", nome: "Nossa Senhora Aparecida" }],
    indicadores: { veiculos: 86, locacoes_ativas: 42, usuarios: 5, ocupacao_pct: "71.00" },
  },
);

let lista: FilialDaLista[] = [];
let feriadosDe: Record<number, FeriadoDaFilial[]> = {};
let proximoId = 10;
let proximoFeriado = 100;

export function reiniciarFiliaisAdminFalso() {
  lista = [{ ...CENTRO_SEED }];
  feriadosDe = { 1: [{ id: 14, data: "2026-10-12", nome: "Nossa Senhora Aparecida", origem: "nacional" }] };
  proximoId = 10;
  proximoFeriado = 100;
}
reiniciarFiliaisAdminFalso();

const achar = (id: number) => {
  const f = lista.find((x) => x.id === id);
  if (!f) throw new ErroApi(404, "nao_encontrado", "Filial não encontrada.");
  return f;
};
const trocar = (id: number, mudanca: Partial<FilialDaLista>) => {
  const nova = { ...achar(id), ...mudanca };
  lista = lista.map((f) => (f.id === id ? nova : f));
  return { ...nova };
};
const ativas = () => lista.filter((f) => f.ativo).length;
const semAcento = (t: string) => t.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

const NACIONAIS = [
  ["01-01", "Confraternização Universal"],
  ["04-21", "Tiradentes"],
  ["05-01", "Dia do Trabalho"],
  ["09-07", "Independência do Brasil"],
  ["10-12", "Nossa Senhora Aparecida"],
  ["11-02", "Finados"],
  ["11-15", "Proclamação da República"],
  ["12-25", "Natal"],
] as const;

export const filiaisAdminFalso = {
  async listar(f: { ativo?: boolean; busca?: string } = {}): Promise<ListaFiliais> {
    await pausa(60);
    const filtradas = lista.filter((x) => (f.ativo === undefined || x.ativo === f.ativo) && (!f.busca || semAcento(`${x.nome} ${x.endereco.cidade}`).includes(semAcento(f.busca))));
    const usado = ativas();
    return {
      plano: { usado, limite: LIMITE_DE_FILIAIS, aviso: usado >= LIMITE_DE_FILIAIS - 1, bloqueado: usado >= LIMITE_DE_FILIAIS, nome_plano: "Profissional" },
      resultados: filtradas.map((x) => ({ ...x })),
      proximo: null,
      anterior: null,
    };
  },

  async obter(id: number): Promise<FilialDetalhada> {
    await pausa(40);
    return { ...achar(id) };
  },

  async criar(corpo: CorpoDaFilial): Promise<FilialDetalhada> {
    await pausa(60);
    if (!corpo.nome.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { nome: "Informe o nome da filial." });
    if (lista.some((x) => semAcento(x.nome) === semAcento(corpo.nome))) throw new ErroApi(409, "filial_nome_em_uso", "Já existe uma filial com esse nome");
    if (ativas() >= LIMITE_DE_FILIAIS) throw new ErroApi(422, "PLT-03", "O plano chegou ao limite de filiais.");
    const id = proximoId++;
    const primeira = lista.length === 0;
    if (corpo.matriz) lista = lista.map((x) => ({ ...x, matriz: false }));
    const nova = montar(id, { ...corpo, matriz: primeira || corpo.matriz });
    lista = [...lista, nova];
    feriadosDe[id] = [];
    return { ...nova };
  },

  async alterar(id: number, corpo: Partial<CorpoDaFilial>): Promise<FilialDetalhada> {
    await pausa(60);
    const atual = achar(id);
    if (corpo.nome && lista.some((x) => x.id !== id && semAcento(x.nome) === semAcento(corpo.nome ?? ""))) throw new ErroApi(409, "filial_nome_em_uso", "Já existe uma filial com esse nome");
    const novo = montar(id, { ...atual, ...corpo, matriz: atual.matriz } as CorpoDaFilial, { gerentes: atual.gerentes, indicadores: atual.indicadores, feriados_proximos: atual.feriados_proximos });
    return trocar(id, { ...novo, ativo: atual.ativo });
  },

  async tornarMatriz(id: number): Promise<FilialDetalhada> {
    await pausa(60);
    if (!achar(id).ativo) throw new ErroApi(422, "filial_inativa", "Filial inativa não pode ser a matriz.");
    lista = lista.map((x) => ({ ...x, matriz: x.id === id }));
    return { ...achar(id) };
  },

  async desativar(id: number, motivo: string): Promise<FilialDetalhada> {
    await pausa(60);
    const f = achar(id);
    if (!motivo.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { motivo: "Informe o motivo." });
    const operacao = { veiculos: f.indicadores.veiculos ?? 0, locacoes: f.indicadores.locacoes_ativas ?? 0, caixas: 0 };
    const impedida = f.matriz || ativas() <= 1 || operacao.veiculos > 0 || operacao.locacoes > 0;
    if (impedida) throw new ErroApi(422, "FIL-06", "Esta filial ainda não pode ser desativada", { matriz: f.matriz, ultima_filial: ativas() <= 1, operacao });
    return trocar(id, { ativo: false });
  },

  async reativar(id: number): Promise<FilialDetalhada> {
    await pausa(60);
    if (ativas() >= LIMITE_DE_FILIAIS) throw new ErroApi(422, "PLT-03", "O plano chegou ao limite de filiais.");
    return trocar(id, { ativo: true });
  },

  async feriados(id: number, ano: number): Promise<FeriadoDaFilial[]> {
    await pausa(40);
    return (feriadosDe[id] ?? []).filter((f) => f.data.startsWith(String(ano)));
  },

  async sugestoesDeFeriados(id: number, ano: number): Promise<SugestaoDeFeriado[]> {
    await pausa(40);
    const feitos = new Set((feriadosDe[id] ?? []).map((f) => f.data));
    return NACIONAIS.map(([dia, nome]) => ({ data: `${ano}-${dia}`, nome, ja_cadastrado: feitos.has(`${ano}-${dia}`) }));
  },

  async confirmarFeriados(id: number, novos: FeriadoNovo[]): Promise<FeriadoDaFilial[]> {
    await pausa(40);
    const atuais = feriadosDe[id] ?? [];
    const datas = new Set(atuais.map((f) => f.data));
    const lote = [...atuais, ...novos.filter((n) => !datas.has(n.data)).map((n) => ({ id: proximoFeriado++, ...n }))].sort((a, b) => a.data.localeCompare(b.data));
    feriadosDe[id] = lote;
    return [...lote];
  },

  async removerFeriado(id: number, feriadoId: number): Promise<void> {
    await pausa(40);
    feriadosDe[id] = (feriadosDe[id] ?? []).filter((f) => f.id !== feriadoId);
  },

  async cep(cep: string): Promise<CepEncontrado> {
    await pausa(40);
    if (cep === "60840280") return { cep, logradouro: "Av. Frei Cirilo", bairro: "Messejana", cidade: "Fortaleza", uf: "CE" };
    throw new ErroApi(404, "cep_nao_encontrado", "Não achamos esse CEP. Preencha o endereço à mão.");
  },
};
