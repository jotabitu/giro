// DADOS FALSOS enquanto a T-011 (backend de contas) não existe.
// Único módulo a trocar: quando a API real chegar, reescreva `contas` e `relatorios` em ./index.ts
// com o cliente gerado do OpenAPI e apague este arquivo. Contrato: docs/api/contas.md.
//
// Contas de teste (senha de todas: senhaforte123):
//   mariana@motorapida.com.br    administradora, 2 etapas ativa  -> verificar_2fa (código 123456)
//   rodrigo@motorapida.com.br    gerente, sem 2 etapas           -> pronto
//   financeiro@motorapida.com.br financeiro sem autenticador     -> configurar_2fa (código 123456)
// Convites: "convite-rodrigo" (gerente), "convite-financeiro" (exige 2 etapas), "convite-vencido" (410).
// Redefinir senha: token "link-valido" funciona; qualquer outro responde 410.
import {
  ErroApi,
  type Aparelho,
  type Configurar2fa,
  type Convite,
  type Eu,
  type Inicio,
  type MarcaEmpresa,
  type Perfil,
  type Pode,
  type RespostaEntrar,
} from "./tipos";

const SENHA = "senhaforte123";
const CODIGO = "123456";
const FILIAL_CENTRO = { id: 1, nome: "Filial Centro" };
const FILIAL_ALDEOTA = { id: 2, nome: "Filial Aldeota" };

const PODE: Record<Perfil, Pode> = {
  administrador: { painel: "todas_filiais", veiculos: "editar", clientes_cadastrar: true, locacoes_criar: true, vistorias_fazer: true, locacoes_cancelar: "sim", desconto_acima_limite: "sim", vendas_criar: true, caixa_receber: true, caixa_abrir_fechar: true, despesas_lancar: "todas", despesas_aprovar: true, financeiro_pagar: true, os_abrir: true, administracao: true },
  gerente: { painel: "filial", veiculos: "editar", clientes_cadastrar: true, locacoes_criar: true, vistorias_fazer: true, locacoes_cancelar: "aprova", desconto_acima_limite: "aprova", vendas_criar: true, caixa_receber: true, caixa_abrir_fechar: true, despesas_lancar: "todas", despesas_aprovar: true, financeiro_pagar: false, os_abrir: true, administracao: false },
  vendedor: { painel: "proprios", veiculos: "nao", clientes_cadastrar: true, locacoes_criar: true, vistorias_fazer: true, locacoes_cancelar: "pede", desconto_acima_limite: "pede", vendas_criar: true, caixa_receber: true, caixa_abrir_fechar: true, despesas_lancar: "todas", despesas_aprovar: false, financeiro_pagar: false, os_abrir: false, administracao: false },
  vistoriador: { painel: "nao", veiculos: "km_e_avarias", clientes_cadastrar: false, locacoes_criar: false, vistorias_fazer: true, locacoes_cancelar: "nao", desconto_acima_limite: "nao", vendas_criar: false, caixa_receber: false, caixa_abrir_fechar: false, despesas_lancar: "manutencao", despesas_aprovar: false, financeiro_pagar: false, os_abrir: true, administracao: false },
  financeiro: { painel: "todas_filiais", veiculos: "nao", clientes_cadastrar: false, locacoes_criar: false, vistorias_fazer: false, locacoes_cancelar: "nao", desconto_acima_limite: "nao", vendas_criar: false, caixa_receber: true, caixa_abrir_fechar: true, despesas_lancar: "todas", despesas_aprovar: false, financeiro_pagar: true, os_abrir: false, administracao: false },
};

type Conta = { id: number; nome: string; email: string; perfil: Perfil; filiais: Eu["filiais"]; autenticador: boolean };

const CONTAS: Conta[] = [
  { id: 1, nome: "Mariana Costa", email: "mariana@motorapida.com.br", perfil: "administrador", filiais: [FILIAL_CENTRO, FILIAL_ALDEOTA], autenticador: true },
  { id: 2, nome: "Rodrigo Pinheiro", email: "rodrigo@motorapida.com.br", perfil: "gerente", filiais: [FILIAL_CENTRO], autenticador: false },
  { id: 3, nome: "Paula Ribeiro", email: "financeiro@motorapida.com.br", perfil: "financeiro", filiais: [FILIAL_CENTRO, FILIAL_ALDEOTA], autenticador: false },
];

const exige2fa = (p: Perfil) => p === "administrador" || p === "financeiro";

function montarEu(c: Conta): Eu {
  return {
    id: c.id,
    nome: c.nome,
    email: c.email,
    celular: null,
    perfil: c.perfil,
    permissoes_extras: [],
    filiais: c.filiais,
    dois_fatores: { ativo: c.autenticador, obrigatorio: exige2fa(c.perfil), codigos_recuperacao_restantes: c.autenticador ? 8 : 0 },
    pode: PODE[c.perfil],
    suporte: null,
    empresa: { nome_exibicao: "Moto Rápida", status: "em_teste", somente_leitura: false },
  };
}

/** Perfil de quem está logado (para os outros módulos falsos decidirem o que devolver, como a API faria). */
export function perfilAtualFalso(): Perfil | null {
  const id = access?.split(".")[1];
  return CONTAS.find((x) => String(x.id) === id)?.perfil ?? null;
}

export const pausa = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const CHAVE_SESSAO = "giro_falso_sessao"; // faz o papel do cookie de refresh
let access: string | null = null;
let tentativas = 0;
const pre2fa = new Map<string, Conta>();

function guardar(c: Conta): RespostaEntrar {
  access = `falso.${c.id}.${Date.now()}`;
  try {
    sessionStorage.setItem(CHAVE_SESSAO, String(c.id));
  } catch {
    /* sem armazenamento */
  }
  return { etapa: "pronto", access, usuario: montarEu(c) };
}

function bloqueio(): ErroApi {
  return new ErroApi(429, "USR-06", "Acesso bloqueado por 15 minutos depois de 5 tentativas erradas", {
    tentar_de_novo_em: new Date(Date.now() + 15 * 60_000).toISOString(),
  });
}

function problemaDaSenha(senha: string, email?: string): string | null {
  if (senha.length < 12) return "Use 12 caracteres ou mais";
  if (!/[A-Za-z]/.test(senha) || !/\d/.test(senha)) return "Use letras e números";
  if (email && senha.toLowerCase() === email.toLowerCase()) return "Use uma senha diferente do e-mail";
  return null;
}

const CODIGOS_RECUPERACAO = ["K7QD-92MX", "PW3R-84TN", "HZ5C-61LB", "V9ME-27YA", "D4XU-50GJ", "N8FS-73RK", "B2TQ-19WC", "Y6AH-38ZP"];

export const contasFalso = {
  async entrar(corpo: { email: string; senha: string; aparelho: Aparelho }): Promise<RespostaEntrar> {
    await pausa();
    const c = CONTAS.find((x) => x.email === corpo.email.trim().toLowerCase());
    if (!c || corpo.senha !== SENHA) {
      tentativas += 1;
      if (tentativas >= 5) throw bloqueio();
      throw new ErroApi(401, "credenciais_invalidas", "E-mail ou senha incorretos");
    }
    tentativas = 0;
    if (exige2fa(c.perfil) || c.autenticador) {
      const token = `pre2fa.${c.id}`;
      pre2fa.set(token, c);
      return { etapa: c.autenticador ? "verificar_2fa" : "configurar_2fa", token_pre_2fa: token };
    }
    return guardar(c);
  },

  async configurar2fa(tokenPre: string): Promise<Configurar2fa> {
    await pausa();
    const c = pre2fa.get(tokenPre);
    if (!c) throw new ErroApi(401, "nao_autenticado", "Sua sessão venceu. Entre de novo.");
    return {
      otpauth_uri: `otpauth://totp/Moto%20R%C3%A1pida:${c.email}?secret=JBSWY3DPEHPK3PXP&issuer=Moto%20R%C3%A1pida`,
      chave: "JBSW Y3DP EHPK 3PXP",
    };
  },

  async verificar2fa(tokenPre: string, corpo: { codigo?: string; codigo_recuperacao?: string }): Promise<RespostaEntrar> {
    await pausa();
    const c = pre2fa.get(tokenPre);
    if (!c) throw new ErroApi(401, "nao_autenticado", "Sua sessão venceu. Entre de novo.");
    const valido = corpo.codigo === CODIGO || (corpo.codigo_recuperacao !== undefined && CODIGOS_RECUPERACAO.includes(corpo.codigo_recuperacao));
    if (!valido) {
      tentativas += 1;
      if (tentativas >= 5) throw bloqueio();
      throw new ErroApi(401, "codigo_invalido", "Código incorreto. Confira o horário do celular e tente de novo.");
    }
    tentativas = 0;
    const primeira = !c.autenticador;
    c.autenticador = true;
    pre2fa.delete(tokenPre);
    const r = guardar(c);
    return primeira && r.etapa === "pronto" ? { ...r, codigos_recuperacao: CODIGOS_RECUPERACAO } : r;
  },

  async renovar(): Promise<{ access: string }> {
    await pausa(80);
    let id: string | null = null;
    try {
      id = sessionStorage.getItem(CHAVE_SESSAO);
    } catch {
      /* sem armazenamento */
    }
    const c = CONTAS.find((x) => String(x.id) === id);
    if (!c) throw new ErroApi(401, "nao_autenticado", "Entre para continuar");
    access = `falso.${c.id}.${Date.now()}`;
    return { access };
  },

  async eu(): Promise<Eu> {
    await pausa(80);
    const id = access?.split(".")[1];
    const c = CONTAS.find((x) => String(x.id) === id);
    if (!c) throw new ErroApi(401, "nao_autenticado", "Entre para continuar");
    return montarEu(c);
  },

  async sair(): Promise<void> {
    await pausa(80);
    access = null;
    try {
      sessionStorage.removeItem(CHAVE_SESSAO);
    } catch {
      /* sem armazenamento */
    }
  },

  async obterConvite(token: string): Promise<Convite> {
    await pausa();
    if (token === "convite-vencido") throw new ErroApi(410, "convite_expirado", "Este convite venceu. Peça um novo ao administrador.");
    const base = { empresa: "Moto Rápida", convidado_por: "Mariana Costa", expira_em: "2026-10-14T23:59:59Z" };
    if (token === "convite-rodrigo") return { ...base, email: "rodrigo@motorapida.com.br", nome: "Rodrigo Pinheiro", perfil: "gerente", filiais: [FILIAL_CENTRO], exige_2fa: false };
    if (token === "convite-financeiro") return { ...base, email: "financeiro@motorapida.com.br", nome: "Paula Ribeiro", perfil: "financeiro", filiais: [FILIAL_CENTRO], exige_2fa: true };
    throw new ErroApi(404, "nao_encontrado", "Convite não encontrado");
  },

  async aceitarConvite(token: string, corpo: { nome: string; senha: string; aparelho: Aparelho }): Promise<RespostaEntrar> {
    const convite = await this.obterConvite(token);
    const problema = problemaDaSenha(corpo.senha, convite.email);
    if (problema) throw new ErroApi(400, "validacao", "Confira os campos", undefined, { senha: problema });
    const c = CONTAS.find((x) => x.email === convite.email);
    if (!c) throw new ErroApi(404, "nao_encontrado", "Convite não encontrado");
    c.nome = corpo.nome;
    if (convite.exige_2fa) {
      const tokenPre = `pre2fa.${c.id}`;
      pre2fa.set(tokenPre, c);
      return { etapa: "configurar_2fa", token_pre_2fa: tokenPre };
    }
    return guardar(c);
  },

  /** Sempre 202, exista ou não o e-mail. */
  async esqueciSenha(email: string): Promise<void> {
    void email;
    await pausa();
  },

  async redefinirSenha(corpo: { token: string; senha_nova: string }): Promise<void> {
    await pausa();
    if (corpo.token !== "link-valido") throw new ErroApi(410, "link_expirado", "Este link venceu. Peça outro.");
    const problema = problemaDaSenha(corpo.senha_nova);
    if (problema) throw new ErroApi(400, "validacao", "Confira os campos", undefined, { senha_nova: problema });
  },
};

/** Marca da empresa (contrato de empresas, ainda não escrito). */
export const marcaFalsa: MarcaEmpresa = { nome: "Moto Rápida", corHex: "#c8f04a" };

export const relatoriosFalso = {
  async inicio(periodo: "hoje" | "7d" | "30d" = "7d"): Promise<Inicio> {
    void periodo; // o dado falso é o mesmo em todos os períodos
    await pausa(200);
    return {
      atencao: 7,
      kpis: [
        { rotulo: "Frota ativa", valor: "86", contexto: "52 motos · 34 carros", destaque: true },
        { rotulo: "Alugados agora", valor: "42", contexto: "↗ 6 esta semana" },
        { rotulo: "Receita de locação", valor: "R$ 18,4 mil", contexto: "últimos 7 dias" },
        { rotulo: "Em atraso", valor: "7", contexto: "R$ 4.380 a receber" },
      ],
      frota: {
        nota: "ocupação de 71% · meta de 80%",
        segmentos: [
          { chave: "disponivel", rotulo: "Disponível", contagem: 16 },
          { chave: "alugado", rotulo: "Alugado", contagem: 42, destaque: "marca" },
          { chave: "reservado", rotulo: "Reservado", contagem: 9 },
          { chave: "manutencao", rotulo: "Manutenção", contagem: 7 },
          { chave: "a_venda", rotulo: "À venda", contagem: 12, destaque: "solido" },
        ],
      },
      devolucoes: {
        subtitulo: "6 contratos · atualizado há 6 min",
        linhas: [
          { id: "LOC-2841", placa: "QXA-4B21", veiculo: "Honda CG 160 Fan", cliente: "Carlos Menezes", data: "06 out", situacao: "Atrasado", tom: "critico" },
          { id: "LOC-2843", placa: "PNB-7C04", veiculo: "Yamaha Factor 150", cliente: "Juliana Rocha", data: "07 out", situacao: "Hoje", tom: "atencao" },
          { id: "LOC-2846", placa: "ROE-2A88", veiculo: "Fiat Mobi Like", cliente: "Pedro Alencar", data: "08 out", situacao: "Alugado", tom: "solido" },
          { id: "LOC-2850", placa: "SAK-1D39", veiculo: "Honda CG 160 Fan", cliente: "Aline Duarte", data: "09 out", situacao: "Renovação", tom: "info" },
          { id: "LOC-2852", placa: "PMZ-3E17", veiculo: "Honda Pop 110i", cliente: "Rafael Sousa", data: "10 out", situacao: "Alugado", tom: "solido" },
          { id: "LOC-2856", placa: "RHT-9F02", veiculo: "Renault Kwid Zen", cliente: "Beatriz Lima", data: "11 out", situacao: "Alugado", tom: "solido" },
        ],
      },
      pendencias: {
        atualizadoHa: "há 6 min",
        titulo: "7 contratos precisam de ação hoje",
        itens: [
          { texto: "3 devoluções estão atrasadas", gravidade: "critica" },
          { texto: "2 motos passaram da revisão de 5.000 km", gravidade: "atencao" },
          { texto: "2 parcelas vencem até amanhã" },
        ],
      },
      caixa: {
        subtitulo: "07 out · Filial Centro",
        saldo: "R$ 2.620,00",
        linhas: [
          { rotulo: "Recebido", valor: "R$ 3.240,00" },
          { rotulo: "A receber hoje", valor: "R$ 1.890,00" },
          { rotulo: "Despesas", valor: "R$ 620,00" },
        ],
      },
      contadores: { veiculos: 86, locacoes: 42, manutencoes: 5, receber: 7, despesas: 3, conciliacao: 6, usuarios: 2 },
    };
  },
};
