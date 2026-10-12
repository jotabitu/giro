// Marca da empresa na API real (docs/api/empresas.md): pública, a mesma antes e depois do login.
import { chamar } from "./http";
import { ErroApi, type MarcaEmpresa } from "./tipos";

export const marcaApi = {
  /** `null` quando o host não tem empresa (404 do urlconf): a tela fica com a marca neutra. */
  async obter(): Promise<MarcaEmpresa | null> {
    try {
      return await chamar<MarcaEmpresa>("GET", "/api/marca/", { semSessao: true });
    } catch (e) {
      if (e instanceof ErroApi && e.status === 404) return null;
      throw e;
    }
  },
};
