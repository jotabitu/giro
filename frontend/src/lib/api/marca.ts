// Marca da empresa na API real (docs/api/empresas.md): a leitura é pública, a mesma antes e depois do login;
// a simulação e o PATCH são do administrador.
import { chamar } from "./http";
import { ErroApi, type CorpoDaMarca, type CorpoDaSimulacao, type MarcaEmpresa, type MarcaSimulada } from "./tipos";

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

  /** Prévia das cores sem gravar (ADR 0005). 400 `validacao` com a `mensagem` em `campos.cor` ou `campos.nome_exibicao`. */
  simular(corpo: CorpoDaSimulacao): Promise<MarcaSimulada> {
    return chamar<MarcaSimulada>("POST", "/api/marca/simular/", { corpo });
  },

  /** Salva e devolve o corpo de `GET /api/marca/`, já com a `versao` nova. Com logo novo vai como multipart. */
  salvar(corpo: CorpoDaMarca): Promise<MarcaEmpresa> {
    const { logo, ...resto } = corpo;
    if (!logo) return chamar<MarcaEmpresa>("PATCH", "/api/marca/", { corpo: resto });
    const form = new FormData();
    form.append("logo", logo);
    if (resto.cor !== undefined) form.append("cor", resto.cor);
    if (resto.nome_exibicao !== undefined) form.append("nome_exibicao", resto.nome_exibicao);
    return chamar<MarcaEmpresa>("PATCH", "/api/marca/", { corpo: form });
  },
};
