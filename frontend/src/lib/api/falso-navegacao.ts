// Faz o papel de `navegacao` em GET /api/auth/eu/ (docs/api/contas.md, "Menu e início") enquanto a T-011 não existe.
// Na API real isto é montado em `contas`; o frontend só lê o resultado.
import type { GrupoNavegacao, ItemNavegacao, Navegacao, Perfil, Pode, VarianteInicio } from "./tipos";

const item = (chave: string, rotulo: string, contador: string | null = null): ItemNavegacao => ({ chave, rotulo, contador });
const grupo = (nome: string | null, itens: (ItemNavegacao | false)[]): GrupoNavegacao => ({ grupo: nome, itens: itens.filter((i): i is ItemNavegacao => i !== false) });
const semVazios = (gs: GrupoNavegacao[]) => gs.filter((g) => g.itens.length > 0);

/** Tabela "Itens do menu_completo" do contrato: permissão da pessoa; plano e atividade valem para todos no falso. */
function menuCompleto(p: Pode, decideAprovacoes: boolean): GrupoNavegacao[] {
  return semVazios([
    grupo(null, [
      item("inicio", "Visão geral"),
      decideAprovacoes && item("aprovacoes", "Aprovações", "aprovacoes"),
      p.veiculos !== "nao" && item("veiculos", "Veículos", "veiculos"),
    ]),
    grupo("Operação", [
      (p.locacoes_criar || p.vistorias_fazer) && item("locacoes", "Locações", "locacoes"),
      p.vendas_criar && item("vendas", "Vendas"),
      (p.clientes_cadastrar || p.caixa_receber) && item("clientes", "Clientes"),
      p.os_abrir && item("manutencoes", "Manutenções", "manutencoes"),
    ]),
    grupo("Financeiro", [
      (p.caixa_receber || p.caixa_abrir_fechar) && item("caixa", "Caixa do dia"),
      p.caixa_receber && item("receber", "Contas a receber", "receber"),
      p.despesas_lancar !== "nao" && item("despesas", "Despesas", "despesas"),
      p.financeiro_pagar && item("comissoes", "Comissões"),
      p.financeiro_pagar && item("conciliacao", "Conciliação", "conciliacao"),
      (p.painel === "todas_filiais" || p.painel === "filial") && item("relatorios", "Relatórios"),
    ]),
    grupo("Administração", p.administracao ? [
      item("config", "Configurações"),
      item("marca", "Empresa e marca"),
      item("filiais", "Filiais"),
      item("usuarios", "Usuários", "usuarios"),
      item("assinatura", "Assinatura"),
      item("auditoria", "Auditoria"),
    ] : []),
  ]);
}

/** Menu da tela inicial de cada perfil (telas Gerente, Vendedor, Vistoriador e Financeiro). */
function menuInicio(variante: VarianteInicio, p: Pode, completo: GrupoNavegacao[]): GrupoNavegacao[] {
  switch (variante) {
    case "gerente":
      return semVazios([
        grupo(null, [item("inicio", "Visão da filial"), item("aprovacoes", "Aprovações", "aprovacoes"), item("veiculos", "Veículos", "veiculos")]),
        grupo("Operação", [item("locacoes", "Locações", "locacoes"), item("clientes", "Clientes"), p.os_abrir && item("manutencoes", "Manutenções", "manutencoes")]),
        grupo("Filial", [item("caixa", "Caixa da filial"), item("relatorios", "Relatórios")]),
      ]);
    case "vendedor":
      return semVazios([grupo(null, [item("inicio", "Início")]), grupo("Operação", [item("locacoes", "Locações", "locacoes"), item("clientes", "Clientes")])]);
    case "vistoriador":
      return [grupo(null, [item("agenda", "Vistorias de hoje", "agenda"), item("consultar_veiculo", "Consultar veículo"), item("avarias", "Avarias abertas", "avarias")])];
    case "financeiro":
      return [
        grupo(null, [
          item("inicio", "Início"),
          item("receber", "Contas a receber", "receber"),
          item("contas_a_pagar", "Contas a pagar", "contas_a_pagar"),
          item("caixa_e_bancos", "Caixa e bancos"),
          item("relatorios", "Relatórios"),
        ]),
      ];
    default:
      return completo;
  }
}

export function navegacaoFalsa(perfil: Perfil, pode: Pode, variante: VarianteInicio): Navegacao {
  const decide = perfil === "administrador" || perfil === "gerente";
  const completo = menuCompleto(pode, decide);
  const barra = ["inicio", "veiculos", "nova_locacao", "locacoes", "mais"].filter((c) => {
    if (c === "inicio") return pode.painel !== "nao" || perfil === "vistoriador";
    if (c === "veiculos") return pode.veiculos !== "nao";
    if (c === "nova_locacao") return pode.locacoes_criar;
    if (c === "locacoes") return pode.locacoes_criar || pode.vistorias_fazer;
    return true;
  });
  return { inicio: { rota: "/inicio", variante }, menu_inicio: menuInicio(variante, pode, completo), menu_completo: completo, barra_celular: barra };
}
