// T-503 · Venda, fase 1b da T-502: Documentos, Assinatura, entrada, vendida e transferência (VEN-06, VEN-14, VEN-15,
// VEN-17, VEN-19), com a VEN-0177 de docs/regras/dados-de-teste.md. Os textos de situação vêm prontos da API.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu, ListaDeVendas, Venda, VendaDetalhe } from "@/lib/api";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/vendas", useSearchParams: () => new URLSearchParams() }));

import { FormularioDaVenda, passoDaVenda } from "./TelaDaVenda";
import { ListaDeVendas as TelaVendas } from "./ListaDeVendas";

sessao.eu = { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { vendas_criar: true } };

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
function html(el: ReactElement, semear?: (c: QueryClient) => void) {
  const c = new QueryClient();
  semear?.(c);
  return renderToStaticMarkup(<QueryClientProvider client={c}>{el}</QueryClientProvider>);
}

const NENHUMA = { editar: false, enviar: false, registrar_resposta: false, pedir_aprovacao: false, perder: false, cancelar: false, registrar_transferencia: false, preparar_assinatura: false, cancelar_assinatura: false, copiar_link_contrato: false, reenviar_contrato: false };

const PROPOSTA: VendaDetalhe = {
  id: 177,
  codigo: "VEN-0177",
  status: "proposta",
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
  situacao_texto: "Proposta enviada",
  motivo_perda: null,
  proposta_enviada_em: "2026-10-07T13:00:00Z",
  proposta_vence_em: "2026-10-14",
  ultimo_contato_em: "2026-10-07T13:00:00Z",
  perdida_em: null,
  vendida_em: null,
  comissao_centavos: 63204,
  transferencia: { feita_em: null, registrada_por: null, pendente: false },
  acoes: { ...NENHUMA, editar: true, enviar: true, registrar_resposta: true, pedir_aprovacao: true, perder: true, preparar_assinatura: true },
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
    precisa_aprovacao: false,
    limite_desconto_pct: "5.00",
  },
  aprovacao: { situacao: "aprovado", pedido_id: 41, desconto_pedido_pct: "8.00", desconto_aprovado_pct: "8.00", motivo_recusa: null, texto: null },
  contrato: null,
  conta_entrada: null,
  documentos: { pendencias: [], gravidade: null, texto: null, pode_preparar: true },
  perder_texto: "A venda sai das abertas e o veículo fica livre para outra proposta.",
  conclusao_texto: null,
};

const CONTRATO_ENVIADO = { id: 88, status: "enviado" as const, modelo: "Compra e venda", versao: 1, enviado_em: "2026-10-07T13:20:00Z", assinado_em: null, pdf_disponivel: true, situacao_texto: "Aguardando assinatura. O cliente assina pelo celular." };
const ENTRADA_ABERTA = { id: 5120, status: "aberta" as const, valor_centavos: 500000, vencimento: "2026-10-07", rotulo: "Entrada de R$ 5.000,00", texto: "Aguardando pagamento · vence hoje" };

const NA_ASSINATURA: VendaDetalhe = {
  ...PROPOSTA,
  situacao_texto: "Aguardando assinatura",
  acoes: { ...NENHUMA, perder: true, cancelar_assinatura: true, copiar_link_contrato: true, reenviar_contrato: true },
  documentos: null,
  contrato: CONTRATO_ENVIADO,
  conta_entrada: ENTRADA_ABERTA,
};

const passoAtual = (h: string) => /aria-current="step"[^>]*>([^<]+)</.exec(h)?.[1];

describe("Venda: passo 2 · Documentos (VEN-14, VEN-19)", () => {
  it("test_ven_19_cadastro_incompleto_trava_a_assinatura", () => {
    const venda: VendaDetalhe = { ...PROPOSTA, documentos: { pendencias: ["endereco", "cnh_frente"], gravidade: "alerta", texto: "Falta completar o cadastro de Diego Martins para preparar a assinatura.", pode_preparar: false } };
    const h = html(<FormularioDaVenda venda={venda} />);
    const t = texto(h);
    for (const esperado of ["Documentos", "Falta completar o cadastro de Diego Martins para preparar a assinatura.", "Endereço", "CNH (frente)", "Completar cadastro", "Preparar assinatura"]) expect(t).toContain(esperado);
    expect(h).toContain('href="/clientes/1312"');
    expect(h).toMatch(/<button[^>]*disabled[^>]*>Preparar assinatura</);
    expect(passoAtual(h)).toBe("2 · Documentos");
  });

  it("test_ven_19_cliente_bloqueado_em_tom_critico", () => {
    const venda: VendaDetalhe = { ...PROPOSTA, documentos: { pendencias: [], gravidade: "critica", texto: "Diego Martins está bloqueado e não pode comprar. A assinatura fica liberada depois do desbloqueio. Peça o desbloqueio ao gerente.", pode_preparar: false } };
    const h = html(<FormularioDaVenda venda={venda} />);
    expect(texto(h)).toContain("Diego Martins está bloqueado e não pode comprar. A assinatura fica liberada depois do desbloqueio. Peça o desbloqueio ao gerente.");
    expect(h).toContain("wl-note--critical");
    expect(h).toMatch(/<button[^>]*disabled[^>]*>Preparar assinatura</);
  });

  it("test_ven_15_cadastro_completo_libera_preparar_assinatura", () => {
    const h = html(<FormularioDaVenda venda={PROPOSTA} />);
    expect(texto(h)).toContain("Cadastro completo");
    expect(h).not.toMatch(/<button[^>]*disabled[^>]*>Preparar assinatura</);
    expect(h).not.toContain("Completar cadastro");
  });
});

describe("Venda: passo 3 · Assinatura (VEN-15, VEN-19)", () => {
  it("test_ven_15_contrato_enviado_falta_assinar_e_pagar", () => {
    const h = html(<FormularioDaVenda venda={NA_ASSINATURA} />, (c) => c.setQueryData(["contas-receber", "detalhe", 5120], { id: 5120, acoes: { gerar_pix: true, gerar_boleto: true, receber: true } }));
    const t = texto(h);
    for (const esperado of [
      "Aguardando assinatura",
      "Contrato enviado",
      "Copiar link para assinar",
      "Reenviar contrato",
      "Assinatura do cliente",
      "Aguardando assinatura. O cliente assina pelo celular.",
      "Entrada de R$ 5.000,00",
      "Aguardando pagamento · vence hoje",
      "Gerar Pix",
      "Gerar boleto",
      "Receber no caixa",
      "Venda concluída",
      "Com o contrato assinado e a entrada paga, em qualquer ordem, a venda é concluída sozinha.",
      "Cancelar assinatura",
    ])
      expect(t).toContain(esperado);
    expect(passoAtual(h)).toBe("3 · Assinatura");
    // Com contrato, a proposta não se edita (409 VEN-06): sem "Salvar alterações" nem o bloco Documentos.
    expect(t).not.toContain("Salvar alterações");
    expect(t).not.toContain("Preparar assinatura");
  });

  it("test_ven_15_sem_as_acoes_da_conta_nao_mostra_pix_nem_caixa", () => {
    const t = texto(html(<FormularioDaVenda venda={NA_ASSINATURA} />, (c) => c.setQueryData(["contas-receber", "detalhe", 5120], { id: 5120, acoes: { gerar_pix: false, gerar_boleto: false, receber: false } })));
    for (const ausente of ["Gerar Pix", "Gerar boleto", "Receber no caixa"]) expect(t).not.toContain(ausente);
  });

  it("test_ven_19_vendedor_nao_marca_perdida_com_a_entrada_paga", () => {
    const venda: VendaDetalhe = {
      ...NA_ASSINATURA,
      situacao_texto: "Aguardando assinatura",
      acoes: { ...NENHUMA, copiar_link_contrato: true, reenviar_contrato: true },
      conta_entrada: { ...ENTRADA_ABERTA, status: "paga", texto: "Paga em 07/10/2026" },
      perder_texto: "Só o gerente ou o administrador marca como perdida uma venda com a entrada paga.",
    };
    const t = texto(html(<FormularioDaVenda venda={venda} />));
    expect(t).toContain("Paga em 07/10/2026");
    expect(t).toContain("Só o gerente ou o administrador marca como perdida uma venda com a entrada paga.");
    expect(t).not.toContain("Marcar como perdida");
    expect(t).not.toContain("Cancelar assinatura");
  });
});

describe("Venda: vendida e transferência (VEN-06, VEN-17)", () => {
  const vendida: VendaDetalhe = {
    ...NA_ASSINATURA,
    status: "vendida",
    situacao_texto: "Vendida 07 out",
    vendida_em: "2026-10-07T14:02:00Z",
    acoes: { ...NENHUMA, registrar_transferencia: true },
    contrato: { ...CONTRATO_ENVIADO, status: "assinado", assinado_em: "2026-10-07T13:41:00Z", situacao_texto: "Contrato assinado" },
    conta_entrada: { ...ENTRADA_ABERTA, status: "paga", texto: "Paga em 07/10/2026" },
    transferencia: { feita_em: null, registrada_por: null, pendente: true },
    perder_texto: null,
    conclusao_texto: "Venda concluída. As 12 parcelas estão em Contas a receber, a comissão de R$ 632,04 foi lançada e o veículo saiu da frota de locação.",
  };

  it("test_ven_06_vendida_com_a_conclusao_da_api_e_o_contrato", () => {
    const h = html(<FormularioDaVenda venda={vendida} />);
    const t = texto(h);
    for (const esperado of ["Vendida 07 out", "Assinado em", "Paga em 07/10/2026", "Venda concluída. As 12 parcelas estão em Contas a receber, a comissão de R$ 632,04 foi lançada e o veículo saiu da frota de locação.", "Contrato"]) expect(t).toContain(esperado);
    expect(passoAtual(h)).toBe("3 · Assinatura");
    for (const ausente of ["Marcar como perdida", "Cancelar assinatura", "Copiar link para assinar"]) expect(t).not.toContain(ausente);
  });

  it("test_ven_17_transferencia_pendente_da_venda_de_balcao", () => {
    const t = texto(html(<FormularioDaVenda venda={vendida} />));
    expect(t).toContain("Transferência no Detran");
    expect(t).toContain("Falta a transferência no Detran");
    expect(t).toContain("Transferência feita");
    const feita = texto(html(<FormularioDaVenda venda={{ ...vendida, acoes: NENHUMA, transferencia: { feita_em: "2026-10-15", registrada_por: { id: 2, nome: "Rodrigo Pinheiro" }, pendente: false } }} />));
    expect(feita).toContain("Transferência feita em 15/10/2026 · Rodrigo Pinheiro");
  });

  it("test_ven_15_passo_pelo_que_a_api_mandou", () => {
    expect(passoDaVenda()).toBe(0);
    expect(passoDaVenda({ ...PROPOSTA, documentos: null })).toBe(0);
    expect(passoDaVenda(PROPOSTA)).toBe(1);
    expect(passoDaVenda(NA_ASSINATURA)).toBe(2);
    expect(passoDaVenda(vendida)).toBe(2);
  });
});

describe("Vendas (lista) na 1b", () => {
  const hoje = new Date().toISOString().slice(0, 10);
  const lista = (resultados: Venda[]): ListaDeVendas => ({ proximo: null, anterior: null, resultados });
  const vendida: Venda = { ...PROPOSTA, id: 173, codigo: "VEN-0173", status: "vendida", situacao_texto: "Vendida 06 out", acoes: NENHUMA, transferencia: { feita_em: null, registrada_por: null, pendente: true } };

  it("test_ven_17_vendida_de_balcao_com_contrato_e_transferencia_pendente", () => {
    const h = html(<TelaVendas />, (c) => {
      c.setQueryData(["vendas", "pendentes"], lista([vendida]));
      c.setQueryData(["vendas", "abertas", "todas", null], lista([PROPOSTA]));
      c.setQueryData(["vendas", "vendidas", hoje.slice(0, 7), null], lista([vendida]));
    });
    const t = texto(h);
    expect(t).toContain("Transferências pendentes");
    expect(t).toContain("Falta a transferência no Detran");
    expect(t).toContain("Contrato");
    expect(h).toContain('href="/vendas/173"');
    // As abas são o SegmentedControl no cabeçalho do painel, e "Ver proposta" é o botão quieto.
    expect(h).toContain('class="wl-seg"');
    expect(h).toMatch(/class="[^"]*wl-btn--quiet[^"]*"[^>]*>Ver proposta</);
  });
});
