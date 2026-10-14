// Usuários da empresa na API real (docs/api/contas.md, "Usuários"). Só o administrador chama.
import { http } from "./http";
import type { AlteracaoDeUsuario, ConviteNovo, FiltroUsuarios, ListaUsuarios, SessaoDoUsuario, UsuarioDetalhado } from "./tipos-usuarios";

export const usuariosApi = {
  listar(f: FiltroUsuarios = {}): Promise<ListaUsuarios> {
    return http.get("/api/usuarios/", { situacao: f.situacao, perfil: f.perfil, filial: f.filial, busca: f.busca, cursor: f.cursor });
  },

  obter(id: number): Promise<UsuarioDetalhado> {
    return http.get(`/api/usuarios/${id}/`);
  },

  convidar(corpo: ConviteNovo): Promise<UsuarioDetalhado> {
    return http.post("/api/usuarios/convites/", corpo);
  },

  reenviarConvite(id: number): Promise<UsuarioDetalhado> {
    return http.post(`/api/usuarios/${id}/reenviar-convite/`, {});
  },

  cancelarConvite(id: number): Promise<UsuarioDetalhado> {
    return http.post(`/api/usuarios/${id}/cancelar-convite/`, {});
  },

  alterar(id: number, corpo: AlteracaoDeUsuario): Promise<UsuarioDetalhado> {
    return http.patch(`/api/usuarios/${id}/`, corpo);
  },

  desativar(id: number, motivo?: string): Promise<UsuarioDetalhado> {
    return http.post(`/api/usuarios/${id}/desativar/`, motivo ? { motivo } : {});
  },

  reativar(id: number): Promise<UsuarioDetalhado> {
    return http.post(`/api/usuarios/${id}/reativar/`, {});
  },

  redefinir2fa(id: number, motivo: string): Promise<UsuarioDetalhado> {
    return http.post(`/api/usuarios/${id}/redefinir-2fa/`, { motivo });
  },

  async sessoes(id: number): Promise<SessaoDoUsuario[]> {
    return (await http.get<{ resultados: SessaoDoUsuario[] }>(`/api/usuarios/${id}/sessoes/`)).resultados;
  },

  encerrarSessao(id: number, sessaoId: number): Promise<void> {
    return http.post(`/api/usuarios/${id}/sessoes/${sessaoId}/encerrar/`, {});
  },
};
