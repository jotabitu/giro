// T-503 · Telas Vendas e Venda, fase 1a da T-502 (VEN-02, VEN-03, VEN-10, VEN-13, VEN-14, VEN-16, VEN-19), com a VEN-0177 de
// docs/regras/dados-de-teste.md. Tudo que é número, situação e ação vem da API; a tela só mostra.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu, ListaDeVendas, Venda, VendaDetalhe } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown, busca: "" }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/vendas", useSearchParams: () => new URLSearchParams(sessao.busca) }));

import { formularioDaVenda, FormularioDaVenda, propostaDoFormulario } from "./TelaDaVenda";
import { ListaDeVendas as TelaVendas } from "./ListaDeVendas";

sessao.eu = { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { vendas_criar: true } };

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
function html(el: ReactElement, semear?: (c: QueryClient) => void) {
  const c = new QueryClient();
  semear?.(c);
  return renderToStaticMarkup(<QueryClientProvider client={c}>{el}</QueryClientProvider>);
}

const NENHUMA = { editar: false, enviar: false, registrar_resposta: false, pedir_aprovacao: false, perder: false, cancelar: false, registrar_transferencia: false, preparar_assinatura: false, cancelar_assinatura: false, copiar_link_contrato: false, reenviar_contrato: false };

const BASE: Venda = {
  id: 177,
  codigo: "VEN-0177",
  status: "aguardando_aprovacao",
  origem: "balcao",
  origem_rotulo: "Balcão",
  descricao: "",
  cliente: { id: 1312, nome: "Diego Martins" },
  interessado: null,
  comprador_nome: "Diego Martins",
  veiculo: { id: 702, placa: "RTA2C55", modelo: "Honda CB 300F" },
  filial: { id: 1, nome: "Filial Centro" },
  vendedor: { id: 3, nome: "Bruna Alves" },
  locacao: null,
  valor: 2106800,
  preco_final_centavos: 2106800,
  forma: "entrada_parcelas",
  forma_texto: "entrada + 12×",
  situacao_texto: "Aguardando gerente",
  motivo_perda: null,
  proposta_enviada_em: null,
  proposta_vence_em: null,
  ultimo_contato_em: "2026-10-07T12:00:00Z",
  perdida_em: null,
  vendida_em: null,
  comissao_centavos: 63204,
  transferencia: { feita_em: null, registrada_por: null, pendente: false },
  acoes: { ...NENHUMA, perder: true },
};

const VEN_0177: VendaDetalhe = {
  ...BASE,
  documentos: null,
  perder_texto: null,
  conclusao_texto: null,
  calculo: {
    preco_tabela_centavos: 2290000,
    desconto_pct: "8.00",
    desconto_centavos: 183200,
    preco_final_centavos: 2106800,
    forma: "entrada_parcelas",
    entrada_centavos: 500000,
    saldo_centavos: 1606800,
    num_parcelas: 12,
    juros_pct: "0.00",
    parcela_centavos: 133900,
    ultima_parcela_centavos: 133900,
    total_parcelas_centavos: 1606800,
    comissao_centavos: 63204,
    precisa_aprovacao: true,
    limite_desconto_pct: "5.00",
  },
  aprovacao: { situacao: "pendente", pedido_id: 41, desconto_pedido_pct: "8.00", desconto_aprovado_pct: null, motivo_recusa: null, texto: "Pedido de 8% enviado para Rodrigo Pinheiro. Você não edita a proposta até ele decidir." },
  contrato: null,
  conta_entrada: null,
};

describe("Venda: aguardando o gerente (VEN-02, VEN-13, VEN-19)", () => {
  it("test_ven_02_resumo_da_ven_0177_e_o_aviso_do_pedido", () => {
    const h = html(<FormularioDaVenda venda={VEN_0177} />);
    const t = texto(h);
    for (const esperado of ["VEN-0177 · Diego Martins", "Aguardando gerente", "Pedido de 8% enviado para Rodrigo Pinheiro. Você não edita a proposta até ele decidir.", "R$ 22.900,00", "Desconto 8%", "− R$ 1.832,00", "R$ 21.068,00", "R$ 5.000,00", "12 × R$ 1.339,00", "Comissão", "R$ 632,04", "Marcar como perdida", "Ver o pedido"])
      expect(t).toContain(esperado);
    expect(h).toContain('href="/aprovacoes/41"');
  });

  it("test_ven_19_nao_edita_enquanto_o_gerente_decide", () => {
    const t = texto(html(<FormularioDaVenda venda={VEN_0177} />));
    expect(t).not.toContain("Salvar alterações");
    expect(t).not.toContain("Pedir aprovação do gerente");
    expect(t).not.toContain("Reenviar proposta");
    // Campos travados: a proposta não se edita (409 APR-01 na API).
    expect(html(<FormularioDaVenda venda={VEN_0177} />)).toMatch(/aria-label="Forma de pagamento"[\s\S]*disabled/);
  });

  it("test_ven_18_sem_financiamento_cartao_nem_troca", () => {
    const t = texto(html(<FormularioDaVenda venda={VEN_0177} />));
    expect(t).toContain("À vista");
    expect(t).toContain("Entrada + parcelas");
    expect(t).not.toContain("Financiamento");
    expect(t).not.toContain("cartão");
    expect(t).not.toContain("Cliente vai dar um veículo");
  });
});

describe("Venda: recusada, enviada e perdida", () => {
  it("test_ven_19_desconto_recusado_com_o_motivo", () => {
    const recusada: VendaDetalhe = {
      ...VEN_0177,
      status: "proposta",
      situacao_texto: "Proposta enviada",
      acoes: { ...NENHUMA, editar: true, enviar: true, pedir_aprovacao: true, registrar_resposta: true, perder: true },
      calculo: { ...VEN_0177.calculo!, desconto_pct: "0.00", desconto_centavos: 0, preco_final_centavos: 2290000, precisa_aprovacao: false },
      aprovacao: { situacao: "recusado", pedido_id: 41, desconto_pedido_pct: "8.00", desconto_aprovado_pct: null, motivo_recusa: "margem baixa neste mês", texto: "Desconto de 8% recusado por Rodrigo Pinheiro: margem baixa neste mês. Dê até 5% ou peça uma nova aprovação." },
    };
    const h = html(<FormularioDaVenda venda={recusada} />);
    expect(texto(h)).toContain("Desconto de 8% recusado por Rodrigo Pinheiro: margem baixa neste mês. Dê até 5% ou peça uma nova aprovação.");
    expect(h).toContain("wl-note--critical");
    expect(texto(h)).toContain("Reenviar proposta");
    expect(texto(h)).toContain("Salvar alterações");
  });

  it("test_ven_13_proposta_enviada_mostra_envio_e_vencimento_e_as_acoes", () => {
    const enviada: VendaDetalhe = {
      ...VEN_0177,
      status: "proposta",
      situacao_texto: "Proposta enviada",
      proposta_enviada_em: "2026-10-07T13:00:00Z",
      proposta_vence_em: "2026-10-14",
      aprovacao: null,
      acoes: { ...NENHUMA, editar: true, enviar: true, pedir_aprovacao: true, registrar_resposta: true, perder: true },
      calculo: { ...VEN_0177.calculo!, desconto_pct: "5.00", desconto_centavos: 114500, preco_final_centavos: 2175500, precisa_aprovacao: false },
    };
    const t = texto(html(<FormularioDaVenda venda={enviada} />));
    expect(t).toMatch(/Enviada em\|07 out/);
    expect(t).toMatch(/Vence em\|14 out/);
    for (const b of ["Reenviar proposta", "Registrar resposta do cliente", "Marcar como perdida", "Salvar alterações"]) expect(t).toContain(b);
    expect(t).not.toContain("Pedir aprovação do gerente");
  });

  it("test_ven_13_perdida_mostra_o_motivo_sem_acoes", () => {
    const perdida: VendaDetalhe = { ...VEN_0177, status: "perdida", situacao_texto: "Perdida · proposta vencida", motivo_perda: "proposta vencida", aprovacao: null, acoes: NENHUMA };
    const t = texto(html(<FormularioDaVenda venda={perdida} />));
    expect(t).toContain("Perdida · proposta vencida");
    expect(t).toContain("Motivo da perda: proposta vencida");
    expect(t).not.toContain("Marcar como perdida");
    expect(t).not.toContain("Depois de assinada");
  });

  it("test_ven_14_interessado_sem_cadastro_com_whatsapp", () => {
    const interessado: VendaDetalhe = {
      ...VEN_0177,
      id: 179,
      codigo: "VEN-0179",
      status: "interessado",
      situacao_texto: "Interessado",
      cliente: null,
      interessado: { nome: "Carla Mendes", celular: "85988771100" },
      comprador_nome: "Carla Mendes",
      aprovacao: null,
      acoes: { ...NENHUMA, editar: true, enviar: true, pedir_aprovacao: true, perder: true },
      calculo: { ...VEN_0177.calculo!, desconto_pct: "0.00", desconto_centavos: 0, preco_final_centavos: 2290000, precisa_aprovacao: false },
    };
    const h = html(<FormularioDaVenda venda={interessado} />);
    const t = texto(h);
    expect(t).toContain("O CPF é pedido para enviar a proposta, e o cadastro completo, na etapa Documentos.");
    expect(t).toContain("Salvar proposta e enviar ao cliente");
    expect(h).toContain('href="https://wa.me/5585988771100"');
    expect(h).toContain('value="(85) 98877-1100"');
  });
});

describe("Nova venda", () => {
  it("test_ven_13_nova_venda_comeca_no_negocio", () => {
    const t = texto(html(<FormularioDaVenda />));
    for (const esperado of ["Nova venda", "1 · Negócio", "2 · Documentos", "3 · Assinatura", "Nenhum veículo escolhido", "Cliente sem cadastro: só nome e celular", "Salvar proposta e enviar ao cliente", "Salvar como interessado", "Escolha o veículo para ver o preço."])
      expect(t).toContain(esperado);
  });

  it("test_ven_02_formulario_manda_o_que_se_digitou_sem_conta", () => {
    expect(propostaDoFormulario({ forma: "entrada_parcelas", desconto: "8%", entrada: "R$ 5.000,00", parcelas: "12" })).toEqual({ forma: "entrada_parcelas", desconto_pct: "8.00", entrada_centavos: 500000, num_parcelas: 12 });
    expect(propostaDoFormulario({ forma: "a_vista", desconto: "", entrada: "5.000,00", parcelas: "12" })).toEqual({ forma: "a_vista", desconto_pct: "0" });
    expect(formularioDaVenda(VEN_0177)).toEqual({ forma: "entrada_parcelas", desconto: "8%", entrada: "R$ 5.000,00", parcelas: "12" });
  });
});

describe("Vendas (lista)", () => {
  const hoje = new Date().toISOString().slice(0, 10);
  const lista = (resultados: Venda[]): ListaDeVendas => ({ proximo: null, anterior: null, resultados });
  const enviada: Venda = { ...BASE, id: 175, codigo: "VEN-0175", status: "proposta", comprador_nome: "Thiago Ramos", forma: "a_vista", forma_texto: "Pix à vista", situacao_texto: "Proposta enviada", preco_final_centavos: 1320000, veiculo: { id: 5, placa: "QYB5H60", modelo: "Honda Biz 125" } };
  const vendida: Venda = { ...BASE, id: 173, codigo: "VEN-0173", status: "vendida", comprador_nome: "Paulo Rocha", forma: "a_vista", forma_texto: "Pix à vista", situacao_texto: "Vendida 06 out", preco_final_centavos: 790000, comissao_centavos: 23700, acoes: NENHUMA };
  const quitacao: Venda = { ...BASE, id: 18, codigo: "VEN-0178", status: "vendida", origem: "quitacao_locacao", origem_rotulo: "Quitação de locação", comprador_nome: "Lucas Ferreira", locacao: { id: 2901, codigo: "LOC-2901" }, forma: "", forma_texto: "", situacao_texto: "Quitação de locação", preco_final_centavos: 0, comissao_centavos: null, transferencia: { feita_em: null, registrada_por: null, pendente: true }, acoes: NENHUMA };
  const semear = (c: QueryClient) => {
    c.setQueryData(["vendas", "pendentes"], lista([quitacao]));
    c.setQueryData(["vendas", "abertas", "todas", null], lista([BASE, enviada]));
    c.setQueryData(["vendas", "vendidas", hoje.slice(0, 7), null], lista([vendida, quitacao]));
  };

  it("test_ven_19_situacao_e_forma_como_a_api_manda", () => {
    const h = html(<TelaVendas />, semear);
    const t = texto(h);
    for (const esperado of ["Vendas", "Nova venda", "Propostas abertas · 2", "Todas", "Minhas", "Aguardando gerente", "Diego Martins", "VEN-0177 · Bruna", "R$ 21.068,00", "entrada + 12×", "Thiago Ramos", "Pix à vista", "Proposta enviada", "Ver proposta", "Vendida 06 out", "R$ 237,00"])
      expect(t).toContain(esperado);
    expect(h).toContain('href="/vendas/177"');
    expect(h).toContain('href="/vendas/nova"');
  });

  it("test_ven_11_quitacao_com_rotulo_e_transferencia_pendente", () => {
    const h = html(<TelaVendas />, semear);
    const t = texto(h);
    expect(t).toContain("Transferências pendentes");
    expect(t).toContain("Quitação de locação");
    expect(t).toContain("Falta a transferência no Detran");
    expect(h).toContain('href="/locacoes/2901"');
  });

  it("test_ven_08_sem_numeros_inventados_ate_o_resumo", () => {
    const t = texto(html(<TelaVendas />, semear));
    // Funil, meta, vendido no mês e total das vendidas vêm do resumo da 1c; até lá não aparecem.
    for (const ausente of ["Funil", "meta", "Definir metas", "Em negociação|R$", "conversão"]) expect(t).not.toContain(ausente);
  });

  it("test_ven_08_vendedor_sem_permissao_nao_ve_nova_venda", () => {
    const antes = sessao.eu;
    sessao.eu = { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { vendas_criar: false } };
    expect(html(<TelaVendas />, semear)).not.toContain('href="/vendas/nova"');
    sessao.eu = antes;
  });
});
