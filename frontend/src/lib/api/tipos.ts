// Tipos do contrato docs/api/contas.md. TEMPORÁRIO: sai quando o cliente gerado do OpenAPI (T-011) existir.
import type { components } from "./schema";

export type Perfil = "administrador" | "gerente" | "vendedor" | "vistoriador" | "financeiro";
export type Aparelho = "desktop" | "celular";

export type Pode = {
  painel: "todas_filiais" | "filial" | "proprios" | "nao";
  veiculos: "editar" | "km_e_avarias" | "ver" | "nao";
  /** MOV-02: `gerir` (administrador e gerente), `levar` (vendedor e vistoriador, só as chegadas que levam), `nao`. */
  movimentacoes: "gerir" | "levar" | "nao";
  clientes_cadastrar: boolean;
  locacoes_criar: boolean;
  vistorias_fazer: boolean;
  locacoes_cancelar: "sim" | "aprova" | "pede" | "nao";
  desconto_acima_limite: "sim" | "aprova" | "pede" | "nao";
  vendas_criar: boolean;
  caixa_receber: boolean;
  caixa_abrir_fechar: boolean;
  despesas_lancar: "todas" | "manutencao" | "nao";
  despesas_aprovar: boolean;
  despesas_exportar: boolean;
  financeiro_pagar: boolean;
  lancamento_avulso: boolean;
  os_abrir: boolean;
  administracao: boolean;
};

/** Item do menu vindo da API (docs/api/contas.md, "Menu e início"). A rota e o ícone saem de `chave` em lib/menu.ts. */
export type ItemNavegacao = { chave: string; rotulo: string; contador: string | null };
export type GrupoNavegacao = { grupo: string | null; itens: ItemNavegacao[] };
export type VarianteInicio = "implantacao" | "geral" | "gerente" | "vendedor" | "vistoriador" | "financeiro";
export type Navegacao = {
  inicio: { rota: string; variante: VarianteInicio };
  menu_inicio: GrupoNavegacao[];
  menu_completo: GrupoNavegacao[];
  /** Chaves dos cinco destinos da barra do celular, já filtradas. */
  barra_celular: string[];
};

export type Eu = {
  id: number;
  nome: string;
  email: string;
  celular: string | null;
  perfil: Perfil;
  permissoes_extras: string[];
  filiais: { id: number; nome: string; nome_curto: string }[];
  dois_fatores: { ativo: boolean; obrigatorio: boolean; codigos_recuperacao_restantes: number };
  pode: Pode;
  navegacao: Navegacao;
  suporte: { acesso_suporte_id: number; nome: string; permissao: "ver" | "ver_editar"; fim: string; motivo: string } | null;
  empresa: { nome_exibicao: string; status: string; somente_leitura: boolean };
};

export type RespostaEntrar =
  | { etapa: "pronto"; access: string; usuario: Eu; codigos_recuperacao?: string[] }
  | { etapa: "verificar_2fa"; token_pre_2fa: string }
  | { etapa: "configurar_2fa"; token_pre_2fa: string };

export type Configurar2fa = { otpauth_uri: string; chave: string };

export type Convite = {
  empresa: string;
  email: string;
  nome: string;
  perfil: Perfil;
  filiais: { id: number; nome: string }[];
  convidado_por: string;
  expira_em: string;
  exige_2fa: boolean;
};

/** Marca da empresa (GET /api/marca/, docs/api/empresas.md): nome, iniciais, logo e as quatro cores já calculadas. */
/** Filial do seletor (GET /api/filiais/minhas/): só as ativas e ligadas à pessoa. */
export type MinhaFilial = components["schemas"]["MinhaFilial"];
export type MinhasFiliais = components["schemas"]["MinhasFiliais"];

export type MarcaEmpresa = components["schemas"]["Marca"];
/** Prévia da marca (POST /api/marca/simular/): as mesmas contas da leitura, sem gravar. */
export type MarcaSimulada = components["schemas"]["MarcaSimulada"];
/** O que a simulação aceita: o que não vem usa o valor salvo. `cor: ""` simula a cor padrão. */
export type CorpoDaSimulacao = { cor?: string; nome_exibicao?: string };
/** PATCH /api/marca/: só o que muda. `logo` vai como arquivo (multipart); `logo` e `remover_logo` juntos dão 400. */
export type CorpoDaMarca = { cor?: string; nome_exibicao?: string; logo?: File; remover_logo?: boolean };

/** Erro no formato da API: { codigo, mensagem, detalhes }. `campos` vem em 400 `validacao`. */
export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly codigo: string,
    mensagem: string,
    readonly detalhes?: Record<string, unknown>,
    readonly campos?: Record<string, string>,
  ) {
    super(mensagem);
    this.name = "ErroApi";
  }
}

/** GET /api/ambiente/ e /api/plataforma/ambiente/ (docs/api/README.md, "Ambiente"; ADR 0021). TEMPORÁRIO: sai quando a T-142 puser a rota no OpenAPI. */
export type Ambiente = { hoje: string; data_simulada: boolean };
export type EscopoDoAmbiente = "empresa" | "plataforma";

// Administração › Filiais (docs/api/filiais.md), a partir do cliente gerado.
export type DiaDaSemana = "seg" | "ter" | "qua" | "qui" | "sex" | "sab" | "dom";
export type Intervalo = components["schemas"]["Intervalo"];
export type HorarioDaFilial = Record<DiaDaSemana, Intervalo[]>;
export type EnderecoDaFilial = components["schemas"]["Endereco"];
export type FilialDaLista = Omit<components["schemas"]["FilialNaLista"], "horario"> & { horario: HorarioDaFilial };
export type FilialDetalhada = Omit<components["schemas"]["Filial"], "horario"> & { horario: HorarioDaFilial };
export type PlanoDeFiliais = components["schemas"]["PlanoDasFiliais"];
export type ListaFiliais = Omit<components["schemas"]["ListaDeFiliais"], "resultados"> & { resultados: FilialDaLista[] };
export type FeriadoDaFilial = components["schemas"]["Feriado"];
export type SugestaoDeFeriado = components["schemas"]["Sugestao"];
export type FeriadoNovo = components["schemas"]["FeriadoEntrada"];
export type CepEncontrado = components["schemas"]["Cep"];
/** Corpo do POST e do PATCH: o gerador deixou `horario` solto; aqui ele tem os sete dias. */
export type CorpoDaFilial = Omit<components["schemas"]["FilialEntrada"], "horario"> & { horario: HorarioDaFilial };
export type ImpedimentosDaDesativacao = { matriz: boolean; ultima_filial: boolean; operacao: { veiculos: number; locacoes: number; caixas: number } };
