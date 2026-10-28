// Cliente HTTP da API (docs/api/README.md, ADR 0013). Mesma origem: o navegador chama /api/ no host do
// próprio frontend e o proxy (Next em desenvolvimento, proxy reverso nos outros ambientes) manda ao Django.
// O access token fica só em memória; o refresh vai em cookie HttpOnly que o navegador manda sozinho.
import { ErroApi } from "./tipos";

type Valor = string | number | boolean | null | undefined;

export type OpcoesDaChamada = {
  /** Objeto vira JSON; `FormData` vai como multipart. */
  corpo?: unknown;
  query?: Record<string, Valor>;
  /** Token a usar no lugar do access da sessão (ex.: `token_pre_2fa`). */
  token?: string;
  /** Rota sem sessão (login, convite, esqueci a senha): sem `Authorization` e sem tentar renovar. */
  semSessao?: boolean;
  /** Rotas do cookie de refresh (`renovar`, `sair`) exigem `X-Requested-With: giro` (ADR 0013). */
  comCookie?: boolean;
  /** Rota que não depende da filial escolhida (`/auth/eu/`, `/filiais/minhas/`): sem `X-Filial`. */
  semFilial?: boolean;
  /** A resposta é um arquivo: devolve o `Blob` em vez de JSON (download de exportação). */
  blob?: boolean;
};

const MSG_GENERICA = "Não foi possível concluir agora. Tente de novo.";

let access: string | null = null;
let filial: string | null = null;
let renovando: Promise<string> | null = null;
let suporte = false;
const ouvintes = new Set<() => void>();
const ouvintesDoSuporte = new Set<() => void>();

export function definirAccess(token: string | null) {
  access = token;
  suporte = false;
}

/**
 * Guarda o token de suporte (PLT-07, ADR 0013) só em memória. Ele não tem refresh: um 401 não tenta `auth/renovar/`,
 * apaga o token e avisa quem escuta em `aoTerminarSuporte`.
 */
export function definirAccessDeSuporte(token: string) {
  access = token;
  suporte = true;
}

export function emModoSuporte(): boolean {
  return suporte && access !== null;
}

/** Avisa quando o acesso de suporte acabou no meio do uso (401 do token de suporte). */
export function aoTerminarSuporte(ouvinte: () => void): () => void {
  ouvintesDoSuporte.add(ouvinte);
  return () => ouvintesDoSuporte.delete(ouvinte);
}

function terminouSuporte() {
  access = null;
  filial = null;
  suporte = false;
  ouvintesDoSuporte.forEach((o) => o());
}

/** Filial escolhida no seletor (`"todas"` ou o id), enviada em `X-Filial` (docs/api/filiais.md). `null` = sem cabeçalho. */
export function definirFilial(escolha: string | null) {
  filial = escolha;
}

export function accessAtual(): string | null {
  return access;
}

/** Avisa quando a sessão acabou no meio do uso (renovação recusada, sessão encerrada). */
export function aoPerderSessao(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte);
  return () => ouvintes.delete(ouvinte);
}

function perdeuSessao() {
  access = null;
  filial = null;
  ouvintes.forEach((o) => o());
}

function montarUrl(caminho: string, query?: OpcoesDaChamada["query"]): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const texto = params.toString();
  return texto ? `${caminho}?${texto}` : caminho;
}

function primeiraMensagem(v: unknown): string | undefined {
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return v.map(primeiraMensagem).find((x) => x !== undefined);
  if (v && typeof v === "object") return Object.values(v).map(primeiraMensagem).find((x) => x !== undefined);
  return undefined;
}

/** `{ campo: ["texto"] }` da API vira `{ campo: "texto" }`, que é o que os formulários mostram. */
function camposDoErro(v: unknown): Record<string, string> | undefined {
  if (!v || typeof v !== "object") return undefined;
  const saida: Record<string, string> = {};
  for (const [campo, msg] of Object.entries(v)) {
    const texto = primeiraMensagem(msg);
    if (texto) saida[campo] = texto;
  }
  return Object.keys(saida).length ? saida : undefined;
}

async function lerErro(r: Response): Promise<ErroApi> {
  let json: unknown = null;
  try {
    json = await r.json();
  } catch {
    /* corpo que não é JSON (página de erro do proxy) */
  }
  if (!json || typeof json !== "object") return new ErroApi(r.status, r.status >= 500 ? "erro_servidor" : "erro", MSG_GENERICA);
  const e = json as { codigo?: unknown; mensagem?: unknown; detalhes?: unknown; campos?: unknown };
  const detalhes = e.detalhes && typeof e.detalhes === "object" ? (e.detalhes as Record<string, unknown>) : undefined;
  return new ErroApi(r.status, typeof e.codigo === "string" ? e.codigo : "erro", typeof e.mensagem === "string" ? e.mensagem : MSG_GENERICA, detalhes, camposDoErro(e.campos));
}

async function enviar(metodo: string, caminho: string, o: OpcoesDaChamada, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (o.comCookie) headers["X-Requested-With"] = "giro";
  if (filial && token && !o.comCookie && !o.semFilial) headers["X-Filial"] = filial;
  let corpo: BodyInit | undefined;
  if (o.corpo instanceof FormData) corpo = o.corpo;
  else if (o.corpo !== undefined) {
    headers["Content-Type"] = "application/json";
    corpo = JSON.stringify(o.corpo);
  }
  try {
    return await fetch(montarUrl(caminho, o.query), { method: metodo, headers, body: corpo, credentials: "same-origin", cache: "no-store" });
  } catch {
    throw new ErroApi(0, "sem_conexao", "Sem conexão com o servidor. Confira a internet e tente de novo.");
  }
}

/** Troca o cookie de refresh por um access novo. Uma renovação por vez: as chamadas que falham juntas esperam a mesma. */
export function renovarAccess(): Promise<string> {
  renovando ??= (async () => {
    try {
      const r = await enviar("POST", "/api/auth/renovar/", { comCookie: true }, null);
      if (!r.ok) throw await lerErro(r);
      const { access: novo } = (await r.json()) as { access: string };
      access = novo;
      return novo;
    } finally {
      renovando = null;
    }
  })();
  return renovando;
}

/** Chamada à API; devolve o status junto, para as rotas em que ele muda o sentido (200 x 202). */
export async function chamarComStatus<T>(metodo: string, caminho: string, o: OpcoesDaChamada = {}): Promise<{ status: number; dados: T }> {
  const token = o.semSessao ? null : (o.token ?? access);
  let r = await enviar(metodo, caminho, o, token);

  // Token de suporte não tem refresh: qualquer 401 encerra o modo suporte, sem renovar (PLT-07).
  if (r.status === 401 && suporte && !o.semSessao && !o.token && !o.comCookie && token === access) {
    const erro = await lerErro(r);
    terminouSuporte();
    throw erro;
  }

  // Access vencido (5 min): renova uma vez e repete. Token passado à mão (pré-2 etapas) não renova.
  if (r.status === 401 && !o.semSessao && !o.token && !o.comCookie) {
    const erro = await lerErro(r.clone());
    if (erro.codigo === "nao_autenticado") {
      // Outra pessoa entrou enquanto esta chamada voava (sair e entrar de novo): repete com o access novo, sem renovar.
      if (access && access !== token) {
        r = await enviar(metodo, caminho, o, access);
      } else {
        try {
          await renovarAccess();
        } catch {
          if (access === token) perdeuSessao();
          throw erro;
        }
        r = await enviar(metodo, caminho, o, access);
      }
    }
  }

  if (!r.ok) {
    const erro = await lerErro(r);
    // Um 401 atrasado da sessão que já acabou não derruba a sessão nova.
    if (erro.status === 401 && !o.semSessao && !o.token && !o.comCookie && (access === token || access === null)) perdeuSessao();
    throw erro;
  }
  if (r.status === 204) return { status: 204, dados: undefined as T };
  if (o.blob) return { status: r.status, dados: (await r.blob()) as T };
  return { status: r.status, dados: cursoresDaLista(await r.json()) as T };
}

/**
 * Nas listas, `proximo` e `anterior` chegam como URL completa (CursorPagination do DRF). As telas
 * guardam só o cursor e o devolvem em `?cursor=`, então a URL vira o valor do parâmetro.
 */
export function cursoresDaLista(dados: unknown): unknown {
  if (!dados || typeof dados !== "object" || Array.isArray(dados) || !("resultados" in dados)) return dados;
  const lista = dados as Record<string, unknown>;
  for (const chave of ["proximo", "anterior"]) {
    const v = lista[chave];
    if (typeof v !== "string") continue;
    try {
      lista[chave] = new URL(v, "http://giro.local").searchParams.get("cursor");
    } catch {
      lista[chave] = null;
    }
  }
  return lista;
}

export async function chamar<T>(metodo: string, caminho: string, o: OpcoesDaChamada = {}): Promise<T> {
  return (await chamarComStatus<T>(metodo, caminho, o)).dados;
}

export const http = {
  get: <T>(caminho: string, query?: OpcoesDaChamada["query"]) => chamar<T>("GET", caminho, { query }),
  post: <T>(caminho: string, corpo?: unknown, o: OpcoesDaChamada = {}) => chamar<T>("POST", caminho, { ...o, corpo }),
  patch: <T>(caminho: string, corpo?: unknown) => chamar<T>("PATCH", caminho, { corpo }),
  put: <T>(caminho: string, corpo?: unknown) => chamar<T>("PUT", caminho, { corpo }),
  delete: <T>(caminho: string) => chamar<T>("DELETE", caminho),
};
