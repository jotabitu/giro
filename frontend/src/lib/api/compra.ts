// Compra pública (docs/api/compra.md): sem login, no domínio principal. CNPJ, e-mail e a chave do
// pedido vão no corpo ou no caminho da API, nunca na URL da página.
import { http } from "./http";
import type {
  AndamentoDoPedido,
  CatalogoDaCompra,
  CodigoReenviado,
  PedidoCriado,
  PedidoEntrada,
  SituacaoDoCnpj,
  Subdominio,
} from "./tipos-compra";

const BASE = "/api/publico/compra";

export const compraApi = {
  planos(): Promise<CatalogoDaCompra> {
    return http.get(`${BASE}/planos/`);
  },
  cnpj(cnpj: string): Promise<SituacaoDoCnpj> {
    return http.post(`${BASE}/cnpj/`, { cnpj }, { semSessao: true });
  },
  subdominio(corpo: { subdominio: string } | { nome: string }): Promise<Subdominio> {
    return http.post(`${BASE}/subdominio/`, corpo, { semSessao: true });
  },
  criarPedido(corpo: PedidoEntrada): Promise<PedidoCriado> {
    return http.post(`${BASE}/pedidos/`, corpo, { semSessao: true });
  },
  confirmar(chave: string, codigo: string): Promise<AndamentoDoPedido> {
    return http.post(`${BASE}/pedidos/${encodeURIComponent(chave)}/confirmar/`, { codigo }, { semSessao: true });
  },
  reenviarCodigo(chave: string): Promise<CodigoReenviado> {
    return http.post(`${BASE}/pedidos/${encodeURIComponent(chave)}/reenviar-codigo/`, undefined, { semSessao: true });
  },
  andamento(chave: string): Promise<AndamentoDoPedido> {
    return http.get(`${BASE}/pedidos/${encodeURIComponent(chave)}/`);
  },
};
