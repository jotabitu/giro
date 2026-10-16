// DADOS FALSOS dos usuários nos testes (contrato: docs/api/contas.md, "Usuários"). Só api-falsa.ts importa este arquivo.
// Seed da tela Admin-Usuarios: 6 pessoas, 5 de 10 no plano (as ativas e os convites pendentes contam; o desativado não).
import { ErroApi } from "@/lib/api/tipos";
import type { AlteracaoDeUsuario, ConviteNovo, FiltroUsuarios, ListaUsuarios, PermissaoDoUsuario, SessaoDoUsuario, UsuarioDetalhado } from "@/lib/api/tipos-usuarios";
import { pausa } from "./falso";

const CENTRO = { id: 1, nome: "Filial Centro" };
const ALDEOTA = { id: 2, nome: "Filial Aldeota" };

const permissoes = (perfil: UsuarioDetalhado["perfil"], marcadas: PermissaoDoUsuario["chave"][] = []): PermissaoDoUsuario[] => {
  const padrao: PermissaoDoUsuario["chave"][] = perfil === "administrador" ? ["aprovar_desconto", "cancelar_contrato", "relatorios_todas_filiais"] : perfil === "gerente" ? ["aprovar_desconto"] : [];
  return (["aprovar_desconto", "cancelar_contrato", "relatorios_todas_filiais"] as const).map((chave) => ({
    chave,
    marcada: padrao.includes(chave) || marcadas.includes(chave),
    padrao_do_perfil: padrao.includes(chave),
  }));
};

function pessoa(p: Pick<UsuarioDetalhado, "id" | "nome" | "email" | "perfil" | "status"> & Partial<UsuarioDetalhado>): UsuarioDetalhado {
  const todas = p.perfil === "administrador";
  const pendente = p.status === "convite_pendente";
  return {
    celular: null,
    filiais: todas ? [CENTRO, ALDEOTA] : [CENTRO],
    todas_filiais: todas,
    dois_fatores_ativo: false,
    ultimo_acesso_em: null,
    convite_expira_em: null,
    eu: false,
    permissoes_extras: permissoes(p.perfil),
    entrou_em: null,
    ...p,
    // Os botões do convite, como a API manda ao administrador (T-249).
    acoes: { reenviar_convite: pendente, copiar_link_convite: pendente, cancelar_convite: pendente },
  };
}

const SEED: UsuarioDetalhado[] = [
  pessoa({ id: 1, nome: "Mariana Costa", email: "mariana@motorapida.com.br", perfil: "administrador", status: "ativo", dois_fatores_ativo: true, ultimo_acesso_em: "2026-10-07T15:00:00Z", eu: true, entrou_em: "2026-09-01T12:00:00Z" }),
  pessoa({ id: 2, nome: "Rodrigo Pinheiro", email: "rodrigo@motorapida.com.br", perfil: "gerente", status: "ativo", dois_fatores_ativo: true, ultimo_acesso_em: "2026-10-07T13:00:00Z", entrou_em: "2026-10-07T09:20:00Z", permissoes_extras: permissoes("gerente", ["cancelar_contrato"]) }),
  pessoa({ id: 4, nome: "Bruna Alves", email: "bruna@motorapida.com.br", perfil: "vendedor", status: "ativo", ultimo_acesso_em: "2026-10-06T14:00:00Z", entrou_em: "2026-09-10T12:00:00Z" }),
  pessoa({ id: 5, nome: "João Silva", email: "joao@motorapida.com.br", perfil: "vistoriador", status: "convite_pendente", convite_expira_em: "2026-10-14T12:00:00Z" }),
  pessoa({ id: 3, nome: "Financeiro", email: "financeiro@motorapida.com.br", perfil: "financeiro", status: "convite_pendente", convite_expira_em: "2026-10-14T12:00:00Z", filiais: [CENTRO, ALDEOTA], todas_filiais: true }),
  pessoa({ id: 8, nome: "Felipe Nunes", email: "felipe@motorapida.com.br", perfil: "vendedor", status: "desativado", ultimo_acesso_em: "2026-09-12T15:00:00Z" }),
];

let pessoas: UsuarioDetalhado[] = [];
let proximoId = 20;
let sessoes: Record<number, SessaoDoUsuario[]> = {};

export function reiniciarUsuariosFalso() {
  pessoas = SEED.map((p) => ({ ...p, permissoes_extras: p.permissoes_extras.map((x) => ({ ...x })) }));
  proximoId = 20;
  sessoes = {
    2: [
      { id: 71, tipo: "desktop", aparelho: "Chrome no Windows", ip: "177.10.0.1", criada_em: "2026-10-07T09:20:00Z", ultimo_uso: "2026-10-07T13:00:00Z", atual: false },
      { id: 72, tipo: "desktop", aparelho: "Safari no iPhone", ip: "177.10.0.2", criada_em: "2026-10-06T09:20:00Z", ultimo_uso: "2026-10-06T18:00:00Z", atual: false },
    ] as SessaoDoUsuario[],
  };
}
reiniciarUsuariosFalso();

const naoEncontrado = () => new ErroApi(404, "nao_encontrado", "Usuário não encontrado.");
const ativas = () => pessoas.filter((p) => p.status !== "desativado").length;
const LIMITE = 10;
const achar = (id: number) => {
  const p = pessoas.find((x) => x.id === id);
  if (!p) throw naoEncontrado();
  return p;
};
const trocar = (id: number, mudanca: Partial<UsuarioDetalhado>) => {
  const novo = { ...achar(id), ...mudanca };
  pessoas = pessoas.map((x) => (x.id === id ? novo : x));
  return { ...novo };
};
const administradoresAtivos = () => pessoas.filter((p) => p.perfil === "administrador" && p.status === "ativo");

export const usuariosFalso = {
  async listar(f: FiltroUsuarios = {}): Promise<ListaUsuarios> {
    await pausa(60);
    const situacao = { ativos: "ativo", convites: "convite_pendente", desativados: "desativado" } as const;
    const lista = pessoas.filter((p) => (!f.situacao || p.status === situacao[f.situacao]) && (!f.perfil || p.perfil === f.perfil));
    const usado = ativas();
    return {
      plano: { usado, limite: LIMITE, aviso: usado >= 9, bloqueado: usado >= LIMITE },
      contagens: {
        todos: pessoas.length,
        ativos: pessoas.filter((p) => p.status === "ativo").length,
        convites: pessoas.filter((p) => p.status === "convite_pendente").length,
        desativados: pessoas.filter((p) => p.status === "desativado").length,
      },
      resultados: lista.map((p) => ({ ...p })),
      proximo: null,
      anterior: null,
    };
  },

  async obter(id: number): Promise<UsuarioDetalhado> {
    await pausa(40);
    return { ...achar(id) };
  },

  async convidar(corpo: ConviteNovo): Promise<UsuarioDetalhado> {
    await pausa(60);
    if (pessoas.some((p) => p.email === corpo.email)) throw new ErroApi(409, "email_em_uso", "Já existe um usuário com este e-mail");
    if (ativas() >= LIMITE) throw new ErroApi(422, "PLT-03", "O plano chegou ao limite de usuários.");
    if (corpo.perfil !== "administrador" && !corpo.filiais?.length) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { filiais: "Escolha ao menos uma filial." });
    const nova = pessoa({
      id: proximoId++,
      nome: corpo.nome || corpo.email.split("@")[0]!,
      email: corpo.email,
      celular: corpo.celular ?? null,
      perfil: corpo.perfil,
      status: "convite_pendente",
      convite_expira_em: "2026-10-14T12:00:00Z",
      permissoes_extras: permissoes(corpo.perfil, corpo.permissoes_extras),
    });
    pessoas = [...pessoas, nova];
    return { ...nova };
  },

  async reenviarConvite(id: number): Promise<UsuarioDetalhado> {
    await pausa(60);
    if (achar(id).status !== "convite_pendente") throw new ErroApi(409, "transicao_usuario", "Só convite pendente pode ser reenviado.");
    return trocar(id, { convite_expira_em: "2026-10-14T18:00:00Z" });
  },

  async cancelarConvite(id: number): Promise<UsuarioDetalhado> {
    await pausa(60);
    if (achar(id).status !== "convite_pendente") throw new ErroApi(409, "transicao_usuario", "Só convite pendente pode ser cancelado.");
    return trocar(id, { status: "desativado", convite_expira_em: null });
  },

  async alterar(id: number, corpo: AlteracaoDeUsuario): Promise<UsuarioDetalhado> {
    await pausa(60);
    const atual = achar(id);
    if (corpo.perfil && corpo.perfil !== "administrador" && atual.perfil === "administrador" && administradoresAtivos().length <= 1) {
      throw new ErroApi(422, "ultimo_administrador", "A empresa precisa de ao menos um administrador ativo");
    }
    const perfil = corpo.perfil ?? atual.perfil;
    const marcadas = corpo.permissoes_extras ?? atual.permissoes_extras.filter((x) => x.marcada).map((x) => x.chave);
    const todas = perfil === "administrador";
    return trocar(id, {
      perfil,
      todas_filiais: todas,
      filiais: todas ? [CENTRO, ALDEOTA] : [CENTRO, ALDEOTA].filter((f) => (corpo.filiais ?? atual.filiais.map((x) => x.id)).includes(f.id)),
      permissoes_extras: permissoes(perfil, marcadas),
    });
  },

  async desativar(id: number): Promise<UsuarioDetalhado> {
    await pausa(60);
    const atual = achar(id);
    if (atual.eu) throw new ErroApi(422, "desativar_a_si_mesmo", "Peça a outro administrador para desativar seu acesso");
    if (atual.perfil === "administrador" && administradoresAtivos().length <= 1) throw new ErroApi(422, "ultimo_administrador", "A empresa precisa de ao menos um administrador ativo");
    return trocar(id, { status: "desativado" });
  },

  async reativar(id: number): Promise<UsuarioDetalhado> {
    await pausa(60);
    const atual = achar(id);
    if (atual.status !== "desativado") throw new ErroApi(409, "transicao_usuario", "Só usuário desativado pode ser reativado.");
    if (ativas() >= LIMITE) throw new ErroApi(422, "PLT-03", "O plano chegou ao limite de usuários.");
    return trocar(id, atual.entrou_em || atual.ultimo_acesso_em ? { status: "ativo" } : { status: "convite_pendente", convite_expira_em: "2026-10-14T12:00:00Z" });
  },

  async redefinir2fa(id: number, motivo: string): Promise<UsuarioDetalhado> {
    await pausa(60);
    if (!motivo.trim()) throw new ErroApi(400, "validacao", "Dados inválidos.", undefined, { motivo: "Informe o motivo." });
    return trocar(id, { dois_fatores_ativo: false });
  },

  async sessoes(id: number): Promise<SessaoDoUsuario[]> {
    await pausa(40);
    return (sessoes[id] ?? []).map((s) => ({ ...s }));
  },

  async encerrarSessao(id: number, sessaoId: number): Promise<void> {
    await pausa(40);
    sessoes = { ...sessoes, [id]: (sessoes[id] ?? []).filter((s) => s.id !== sessaoId) };
  },
};
