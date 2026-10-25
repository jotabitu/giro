// Contas na API real (docs/api/contas.md, T-011 e T-072): login, 2 etapas, renovação, sair, convite e senha.
import { chamar, definirAccess, definirFilial, http, renovarAccess } from "./http";
import type { Aparelho, Configurar2fa, Convite, Eu, RespostaEntrar } from "./tipos";

/** Guarda o access de quem terminou o login (o refresh já foi para o cookie). */
function guardar(r: RespostaEntrar): RespostaEntrar {
  if (r.etapa === "pronto") definirAccess(r.access);
  return r;
}

export const contasApi = {
  async entrar(corpo: { email: string; senha: string; aparelho: Aparelho }): Promise<RespostaEntrar> {
    return guardar(await http.post<RespostaEntrar>("/api/auth/entrar/", corpo, { semSessao: true }));
  },

  configurar2fa(tokenPre: string): Promise<Configurar2fa> {
    return http.post<Configurar2fa>("/api/auth/2fa/configurar/", undefined, { token: tokenPre });
  },

  async verificar2fa(tokenPre: string, corpo: { codigo?: string; codigo_recuperacao?: string }): Promise<RespostaEntrar> {
    return guardar(await http.post<RespostaEntrar>("/api/auth/2fa/verificar/", corpo, { token: tokenPre }));
  },

  /** Reconfirma as 2 etapas sem sair do sistema (USR-02, USR-06, ADR 0032) e troca o access em memória pelo que traz `auth_time` novo. */
  async reconfirmar2fa(corpo: { codigo?: string; codigo_recuperacao?: string }): Promise<void> {
    const { access } = await http.post<{ access: string }>("/api/auth/2fa/reconfirmar/", corpo);
    definirAccess(access);
  },

  async renovar(): Promise<{ access: string }> {
    return { access: await renovarAccess() };
  },

  eu(): Promise<Eu> {
    return chamar<Eu>("GET", "/api/auth/eu/", { semFilial: true });
  },

  async sair(): Promise<void> {
    try {
      await http.post<void>("/api/auth/sair/", undefined, { comCookie: true });
    } finally {
      definirAccess(null);
      definirFilial(null);
    }
  },

  consultarConvite(corpo: { token: string }): Promise<Convite> {
    return http.post<Convite>("/api/convites/consultar/", corpo, { semSessao: true });
  },

  async aceitarConvite(corpo: { token: string; nome: string; senha: string; aparelho: Aparelho }): Promise<RespostaEntrar> {
    return guardar(await http.post<RespostaEntrar>("/api/convites/aceitar/", corpo, { semSessao: true }));
  },

  async esqueciSenha(email: string): Promise<void> {
    await http.post("/api/auth/senha/esqueci/", { email }, { semSessao: true });
  },

  async redefinirSenha(corpo: { token: string; senha_nova: string }): Promise<void> {
    await http.post("/api/auth/senha/redefinir/", corpo, { semSessao: true });
  },
};
