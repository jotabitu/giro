// DADOS FALSOS de docs/api/contas.md, "Controle do administrador" (Moto Rápida em 07 out 2026). Só api-falsa.ts importa este arquivo.
import { ErroApi } from "@/lib/api/tipos";
import type { AcessoDoSuporte, BloqueioDoSuporte, ControleDoSuporte, SituacaoDoSuporte } from "@/lib/api/tipos-suporte";
import { pausa } from "./falso";

const SEED: AcessoDoSuporte[] = [
  { id: 31, nome: "Diego Santos", motivo: "Chamado #1042", permissao: "ver", permissao_rotulo: "Só ver", inicio: "2026-10-07T14:30:00Z", fim: "2026-10-07T15:30:00Z", status: "ativo", status_rotulo: "Ativo agora", acoes: { revogar: true } },
  { id: 29, nome: "Camila Rocha", motivo: "Chamado #1018", permissao: "ver_editar", permissao_rotulo: "Ver e editar", inicio: "2026-10-05T10:15:00Z", fim: "2026-10-05T10:37:00Z", status: "encerrado", status_rotulo: "Encerrado", acoes: { revogar: false } },
  { id: 27, nome: "Diego Santos", motivo: "Chamado #0987", permissao: "ver", permissao_rotulo: "Só ver", inicio: "2026-10-02T09:00:00Z", fim: "2026-10-02T09:30:00Z", status: "revogado", status_rotulo: "Revogado", acoes: { revogar: false } },
];

let bloqueado = false;
let acessos: AcessoDoSuporte[] = SEED.map((a) => ({ ...a }));

/** Volta ao estado do seed (os testes chamam entre um caso e outro). */
export function reiniciarSuporteFalso() {
  bloqueado = false;
  acessos = SEED.map((a) => ({ ...a }));
}

const encerrado = (a: AcessoDoSuporte) => a.status !== "ativo";

export const suporteFalso = {
  async listar(situacao: SituacaoDoSuporte = "todos"): Promise<ControleDoSuporte> {
    await pausa(80);
    const ativos = acessos.filter((a) => !encerrado(a));
    const filtrados = situacao === "ativos" ? ativos : situacao === "encerrados" ? acessos.filter(encerrado) : acessos;
    return {
      bloqueado,
      situacao_rotulo: bloqueado ? "Acesso do suporte bloqueado" : "Acesso do suporte liberado",
      contagens: { todos: acessos.length, ativos: ativos.length, encerrados: acessos.length - ativos.length },
      acessos: filtrados,
    };
  },

  async bloquear(): Promise<BloqueioDoSuporte> {
    await pausa(80);
    bloqueado = true;
    acessos = acessos.map((a) => (a.status === "ativo" ? { ...a, status: "revogado", status_rotulo: "Revogado", acoes: { revogar: false } } : a));
    return { bloqueado };
  },

  async liberar(): Promise<BloqueioDoSuporte> {
    await pausa(80);
    bloqueado = false;
    return { bloqueado };
  },

  async revogar(id: number): Promise<AcessoDoSuporte> {
    await pausa(80);
    const a = acessos.find((x) => x.id === id);
    if (!a) throw new ErroApi(404, "nao_encontrado", "Acesso não encontrado");
    const novo: AcessoDoSuporte = { ...a, status: "revogado", status_rotulo: "Revogado", acoes: { revogar: false } };
    acessos = acessos.map((x) => (x.id === id ? novo : x));
    return novo;
  },
};
