// Tipos do contrato docs/api/contas.md. TEMPORÁRIO: sai quando o cliente gerado do OpenAPI (T-011) existir.
import type { components } from "./schema";

export type Perfil = "administrador" | "gerente" | "vendedor" | "vistoriador" | "financeiro";
export type Aparelho = "desktop" | "celular";

export type Pode = {
  painel: "todas_filiais" | "filial" | "proprios" | "nao";
  veiculos: "editar" | "km_e_avarias" | "nao";
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
  financeiro_pagar: boolean;
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
  filiais: { id: number; nome: string }[];
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
export type MarcaEmpresa = components["schemas"]["Marca"];

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
