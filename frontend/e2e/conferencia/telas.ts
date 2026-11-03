// T-425 · Telas que a conferência lado a lado compara: a tela de referência (`docs/telas/html/<referencia>-Desktop|Mobile.dc.html`)
// e a rota do app com o seed da Moto Rápida em 07 out 2026. Para incluir uma tela, acrescente uma linha aqui.
// `perfil`: quem entra (vistoriador não vê valores, vendedor não vê margem; o administrador e o financeiro pedem o código de 2 etapas).
// Rotas com `[id]` levam o id do seed, que é determinístico.

export type Perfil = "mariana" | "rodrigo" | "bruna" | "joao" | "lucia";

export const EMAIL_DO_PERFIL: Record<Perfil, string> = {
  mariana: "mariana@motorapida.com.br",
  rodrigo: "rodrigo@motorapida.com.br",
  bruna: "bruna@motorapida.com.br",
  joao: "joao@motorapida.com.br",
  lucia: "lucia@motorapida.com.br",
};

export type TelaDeConferencia = {
  /** Nome curto, usado no filtro `TELA=Frota,Caixa` e no nome dos arquivos. */
  nome: string;
  /** Prefixo do arquivo em `docs/telas/html` (sem `-Desktop`/`-Mobile` nem `.dc.html`). */
  referencia: string;
  /** Rota do app, com a query se precisar. */
  rota: string;
  perfil: Perfil;
};

export const TELAS: TelaDeConferencia[] = [
  { nome: "Inicio-gerente", referencia: "Gerente", rota: "/inicio", perfil: "rodrigo" },
  { nome: "Inicio-vendedor", referencia: "Vendedor", rota: "/inicio", perfil: "bruna" },
  { nome: "Inicio-vistoriador", referencia: "Vistoriador", rota: "/inicio", perfil: "joao" },
  { nome: "Inicio-financeiro", referencia: "Financeiro", rota: "/inicio", perfil: "lucia" },
  { nome: "Aprovacoes", referencia: "Aprovacoes", rota: "/aprovacoes", perfil: "rodrigo" },
  { nome: "Frota", referencia: "Frota", rota: "/veiculos", perfil: "rodrigo" },
  { nome: "Veiculo", referencia: "Veiculo", rota: "/veiculos/20", perfil: "rodrigo" },
  { nome: "Veiculo-Novo", referencia: "Veiculo-Novo", rota: "/veiculos/novo", perfil: "rodrigo" },
  { nome: "Movimentacoes", referencia: "Movimentacoes", rota: "/veiculos/movimentacoes", perfil: "rodrigo" },
  { nome: "Movimentacao-Nova", referencia: "Movimentacao-Nova", rota: "/veiculos/movimentacoes/nova", perfil: "rodrigo" },
  { nome: "Locacoes", referencia: "Locacoes", rota: "/locacoes", perfil: "rodrigo" },
  { nome: "Locacao-Nova", referencia: "Locacao", rota: "/locacoes/nova?cliente=2", perfil: "rodrigo" },
  { nome: "Clientes", referencia: "Clientes", rota: "/clientes", perfil: "rodrigo" },
  { nome: "Cliente-Detalhe", referencia: "Cliente-Detalhe", rota: "/clientes/2", perfil: "rodrigo" },
  { nome: "Caixa", referencia: "Caixa", rota: "/financeiro/caixa", perfil: "lucia" },
  { nome: "Receber", referencia: "Receber", rota: "/financeiro/receber", perfil: "lucia" },
  { nome: "Despesas", referencia: "Despesas", rota: "/financeiro/despesas", perfil: "lucia" },
  { nome: "Reembolsos", referencia: "Reembolsos", rota: "/financeiro/reembolsos", perfil: "lucia" },
  { nome: "Pendencias-Pagamento", referencia: "Pendencias-Pagamento", rota: "/financeiro/pendencias-pagamento", perfil: "lucia" },
  { nome: "Admin-Usuarios", referencia: "Admin-Usuarios", rota: "/admin/usuarios", perfil: "mariana" },
  { nome: "Admin-Assinatura", referencia: "Admin-Assinatura", rota: "/admin/assinatura", perfil: "mariana" },
  { nome: "Admin-Auditoria", referencia: "Admin-Auditoria", rota: "/admin/auditoria", perfil: "mariana" },
  { nome: "Admin-Suporte", referencia: "Admin-Suporte", rota: "/admin/suporte", perfil: "mariana" },
  { nome: "Filiais", referencia: "Filiais", rota: "/admin/filiais", perfil: "mariana" },
];
