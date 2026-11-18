// T-496: tela de preços do veículo e o painel "Preços desta moto" da ficha (VEI-12 a VEI-17). A tela só mostra o que a API calculou.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { PrecosDoVeiculo as Precos } from "@/lib/api";
import { PRECOS_POP } from "@/testes/falsos/falso-precos-veiculo";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/900/precos", useSearchParams: () => new URLSearchParams() }));

import { PrecosDoVeiculo } from "./PrecosDoVeiculo";
import { PrecosNaFicha } from "./PrecosNaFicha";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

function pagina(d: Precos): string {
  const cache = new QueryClient();
  cache.setQueryData(["veiculo-precos", 900], d);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <PrecosDoVeiculo id={900} />
    </QueryClientProvider>,
  );
}

function ficha(d: Precos): string {
  const cache = new QueryClient();
  cache.setQueryData(["veiculo-precos", 900], d);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <PrecosNaFicha id={900} />
    </QueryClientProvider>,
  );
}

const compra = PRECOS_POP.plano_compra as NonNullable<Precos["plano_compra"]>;
const semPlano: Precos = {
  ...PRECOS_POP,
  aviso_preco: "A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda.",
  planos: PRECOS_POP.planos.map((p) => ({ ...p, ligado: false })),
  plano_compra: { ...compra, ligado: false },
};
// Gerente: lê tudo, não edita. Vendedor: sem custos, sem "pago na moto" e sem margem (as chaves vêm ausentes, USR-09).
const gerente: Precos = { ...PRECOS_POP, pode_editar: false };
const { custos: _c, pago_na_moto: _p, ...semCusto } = PRECOS_POP;
const vendedor: Precos = { ...semCusto, pode_editar: false, planos: PRECOS_POP.planos.map(({ margem: _m, ...p }) => p), plano_compra: { ...compra, resultado: { ...(compra.resultado as NonNullable<typeof compra.resultado>), lucro_centavos: undefined, margem_sobre_pago_pct: undefined } } };

describe("tela de preços do veículo", () => {
  const h = pagina(PRECOS_POP);
  const t = texto(h);

  it("vei_13_custo_e_venda_vem_da_api", () => {
    expect(t).toContain("Planos e preços");
    expect(t).toContain("Honda Pop 110i");
    expect(t).toContain("R$ 13.800,00");
    expect(t).toContain("compra R$ 13.490,00 + despesas R$ 310,00");
    expect(t).toContain("FIPE R$ 13.900,00");
    expect(t).toContain("R$ 530,00");
    expect(t).toContain("Revenda estimada em 24 meses");
    expect(h).toContain('value="R$ 9.000,00"');
    expect(t).toContain("85%");
    expect(t).toContain("frota nos últimos 90 dias: 84%");
    expect(h).toContain("Editar custos mensais");
    expect(h).toContain("Salvar preços");
  });

  it("vei_12_planos_com_valor_pagamento_caucao_e_margem_da_api", () => {
    for (const rotulo of ["Diária", "Semanal", "Mensal", "Entregador"]) expect(t).toContain(rotulo);
    expect(h).toContain('value="R$ 269,00"');
    expect(h).toContain('value="R$ 990,00"');
    expect(t).toContain("4 semanais de R$ 247,50");
    expect(t).toContain("56,3%");
    expect(t).toContain("R$ 681,82/mês");
    expect(t).toContain("R$ 289,00 a partir de 01 dez");
    expect(t).toContain("Ligue para definir valor, prazo mínimo e caução.");
    expect(h).toContain('aria-label="Oferecer semanal"');
  });

  it("vei_12_linha_aberta_do_semanal_tem_formas_franquia_e_preco_agendado", () => {
    expect(t).toContain("Formas aceitas");
    expect(t).toContain("Franquia por semana");
    expect(t).toContain("Preço agendado");
    expect(t).toContain("Agendar preço");
    expect(t).toContain("Desfazer agendamento");
    expect(h).toContain('value="1.000 km"');
  });

  it("vei_16_locacao_com_compra_mostra_o_resultado_da_api_sem_conta_no_cliente", () => {
    expect(t).toContain("O cliente paga");
    expect(t).toContain("R$ 191,01");
    expect(t).toContain("R$ 161,24 da moto + R$ 29,77 de adicional");
    expect(t).toContain("R$ 17.768,96");
    expect(t).toContain("R$ 3.968,96");
    expect(t).toContain("R$ 1.868,96");
    expect(t).toContain("28,8%");
    expect(t).toContain("Financia R$ 14.900,00");
    expect(t).toContain("104 semanas = 24 meses");
    expect(t).toContain("0,23% por semana · Price");
    for (const v of ["R$ 27,19", "R$ 382,39", "R$ 830,39"]) expect(t).toContain(v);
    expect(h).toContain('aria-pressed="true">Semanais');
    expect(h).toContain('aria-pressed="true">Calcular pelos juros');
  });

  it("vei_14_regras_da_moto", () => {
    for (const r of ["Km excedente", "Atraso na devolução", "Desconto sem aprovação", "Devolver a caução em", "Multa mínima da devolução antecipada"]) expect(t).toContain(r);
    expect(h).toContain('value="R$ 0,35 por km"');
    expect(h).toContain('value="até 10%"');
  });

  it("vei_15_aviso_de_tabela_nao_preenchida_so_quando_a_api_manda", () => {
    expect(t).not.toContain("não está preenchida");
    expect(texto(pagina(semPlano))).toContain("A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda.");
  });

  it("vei_16_alertas_da_api_aparecem_no_resultado", () => {
    const alerta = { codigo: "VEI-16", mensagem: "Locadora não é financeira: juros acima de 1% ao mês (12% ao ano) pedem confirmação. Valide o contrato com seu advogado." };
    expect(texto(pagina({ ...PRECOS_POP, alertas: [alerta] }))).toContain(alerta.mensagem);
  });

  it("vei_12_gerente_so_le: sem salvar, sem editar custos, campos desabilitados", () => {
    const hg = pagina(gerente);
    expect(hg).not.toContain("Salvar preços");
    expect(hg).not.toContain("Editar custos mensais");
    expect(hg).toMatch(/role="switch"[^>]*disabled/);
    expect(hg).toMatch(/value="R\$ 269,00"[^>]*disabled|disabled=""[^>]*value="R\$ 269,00"/);
    expect(texto(hg)).toContain("só o administrador altera");
  });

  it("vei_13_vendedor_nao_ve_custo_lucro_nem_margem", () => {
    const tv = texto(pagina(vendedor));
    expect(tv).not.toContain("Pago na moto");
    expect(tv).not.toContain("Custos por mês");
    expect(tv).not.toContain("56,3%");
    expect(tv).not.toContain("Lucro");
    expect(tv).toContain("Recebe pela moto");
  });

  it("vei_12_carregando_e_erro", () => {
    const cache = new QueryClient();
    const carregando = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <PrecosDoVeiculo id={901} />
      </QueryClientProvider>,
    );
    expect(texto(carregando)).toContain("Carregando os preços…");
  });
});

describe("Preços desta moto na ficha", () => {
  const h = ficha(PRECOS_POP);
  const t = texto(h);

  it("vei_12_cartoes_dos_planos_com_o_que_a_api_devolve", () => {
    expect(t).toContain("Preços desta moto");
    expect(t).toContain("Vale só para a TBC-5H21");
    expect(t).toContain("Margem calculada sobre o custo desta moto: R$ 530,00 por mês, com ocupação de 85%");
    expect(t).toContain("R$ 269,00");
    expect(t).toContain("R$ 289,00 a partir de 01 dez");
    expect(t).toContain("Pix ou boleto");
    expect(t).toContain("R$ 500,00 em 2x");
    expect(t).toContain("4 semanais de R$ 247,50");
    expect(t).toContain("1.000 km por semana");
    expect(t).toContain("margem 56,3%");
    expect(t).toContain("Lucro R$ 681,82 por mês");
  });

  it("vei_16_cartao_da_compra", () => {
    expect(t).toContain("Locação com compra");
    expect(t).toContain("a moto vira do cliente");
    expect(t).toContain("R$ 191,01");
    expect(t).toContain("juros 1,00% ao mês");
    expect(t).toContain("Recebe pela moto");
    expect(t).toContain("R$ 17.768,96");
    expect(h).toContain(`/veiculos/900/precos`);
  });

  it("vei_14_regras_e_plano_desligado", () => {
    expect(t).toContain("R$ 0,35 por km");
    expect(t).toContain("até 10%");
    expect(t).toContain("até 3 dias após a devolução");
    expect(t).toContain("Multa mínima da devolução antecipada");
    expect(t).toContain("Não aparece na nova locação. Ligue e defina valor, caução e franquia só para esta moto.");
    expect(h).toContain("Editar preços");
  });

  it("vei_15_sem_plano_ligado_mostra_o_aviso_da_api", () => {
    const ts = texto(ficha(semPlano));
    expect(ts).toContain("A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda.");
    expect(ts).toContain("Desligado");
  });

  it("vei_12_gerente_sem_editar_preços_e_com_interruptores_desabilitados", () => {
    const hg = ficha(gerente);
    expect(hg).not.toContain("Editar preços");
    expect(hg).toMatch(/role="switch"[^>]*disabled/);
  });

  it("vei_13_vendedor_sem_linha_de_margem", () => {
    const tv = texto(ficha(vendedor));
    expect(tv).not.toContain("Lucro R$");
    expect(tv).not.toContain("margem 56");
    expect(tv).not.toContain("Margem calculada");
  });
});
