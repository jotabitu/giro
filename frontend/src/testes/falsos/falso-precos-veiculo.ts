// Fixture de `GET /api/veiculos/{id}/precos/` (T-496, ADR 0041, docs/api/veiculos.md "Preços do veículo"): a Pop TBC-5H21 do contrato.
// Os números são os da API de exemplo; o fixture não calcula nada. Só os testes importam esta pasta.
import { ErroApi } from "@/lib/api/tipos";
import type { PlanoDoVeiculo, PrecosDoVeiculo, PrecosEntrada } from "@/lib/api/tipos-precos-veiculo";

const margem = (receita: number, lucro: number, pct: string) => ({ receita_mes_centavos: receita, lucro_mes_centavos: lucro, margem_pct: pct, abaixo_da_minima: false, sem_custo_compra: false });

const base = (p: Partial<PlanoDoVeiculo> & Pick<PlanoDoVeiculo, "tipo" | "rotulo">): PlanoDoVeiculo => ({
  id: null,
  nome: null,
  periodo: null,
  ligado: false,
  valor_centavos: 0,
  como_paga: null,
  formas_aceitas: [],
  caucao_centavos: null,
  caucao_parcelas: 1,
  caucao_parcelada: null,
  franquia_km: null,
  prazo_minimo_periodos: null,
  agendado: null,
  parcela_do_mes: null,
  margem: null,
  ...p,
});

export const PRECOS_POP: PrecosDoVeiculo = {
  veiculo: { id: 900, placa: "TBC5H21", marca: "Honda", modelo: "Pop 110i", status: "disponivel" },
  valor_venda_centavos: 1590000,
  fipe_centavos: 1390000,
  ocupacao_real_90d_pct: "84.00",
  margem_minima_pct: null,
  pago_na_moto: { total_centavos: 1380000, compra_centavos: 1349000, despesas_centavos: 31000 },
  custos: {
    manutencao_mes_centavos: 10000,
    seguro_mes_centavos: 8000,
    rastreador_mes_centavos: 5000,
    ipva_ano_centavos: 120000,
    ipva_mes_centavos: 10000,
    revenda_estimada_centavos: 900000,
    ocupacao_esperada_pct: "85.00",
    custo_mes_centavos: 53000,
    sem_custo_compra: false,
    revenda_acima_do_pago: false,
  },
  planos: [
    base({ id: 30, tipo: "diaria", rotulo: "Diária", periodo: "dia", ligado: true, valor_centavos: 4490, como_paga: "tudo_na_retirada", formas_aceitas: ["pix", "boleto"], caucao_centavos: 30000, franquia_km: 150, margem: margem(134700, 65678, "48.76") }),
    base({
      id: 31,
      tipo: "semanal",
      rotulo: "Semanal",
      periodo: "semana",
      ligado: true,
      valor_centavos: 26900,
      como_paga: "semana_adiantado",
      formas_aceitas: ["pix", "boleto"],
      caucao_centavos: 30000,
      franquia_km: 1000,
      agendado: { valor_centavos: 28900, caucao_centavos: null, a_partir_de: "2026-12-01" },
      margem: margem(121182, 68182, "56.26"),
    }),
    base({
      id: 32,
      tipo: "mensal",
      rotulo: "Mensal",
      periodo: "mes",
      ligado: true,
      valor_centavos: 99000,
      como_paga: "mes_quatro_semanais",
      formas_aceitas: ["pix", "cartao"],
      caucao_centavos: 50000,
      caucao_parcelas: 2,
      caucao_parcelada: { parcelas: 2, parcela_centavos: 25000, ultima_parcela_centavos: 25000 },
      franquia_km: 4000,
      parcela_do_mes: { parcelas: 4, parcela_centavos: 24750, ultima_parcela_centavos: 24750 },
      margem: margem(99000, 35333, "35.69"),
    }),
    base({ tipo: "entregador", rotulo: "Entregador" }),
  ],
  regras: { km_excedente_centavos: 35, dia_atraso_centavos: 4490, multa_minima_centavos: 4490, desconto_sem_aprovacao_pct: "10.00", prazo_devolucao_caucao_dias: 3 },
  plano_compra: {
    ligado: true,
    periodicidade: "semanal",
    parcelas: 104,
    entrada_centavos: 100000,
    juros_mes_pct: "1.00",
    modo: "calcular",
    parcela_moto_centavos: 16124,
    adicional_centavos: 2977,
    caucao_centavos: 30000,
    resultado: {
      financiado_centavos: 1490000,
      meses_do_prazo: "24.00",
      taxa_periodo_pct: "0.23",
      juros_mes_pct: "1.00",
      parcela_moto_centavos: 16124,
      adicional_centavos: 2977,
      parcela_cliente_centavos: 19101,
      recebe_pela_moto_centavos: 1776896,
      juros_no_prazo_centavos: 186896,
      venda_abaixo_do_pago: false,
      lucro_centavos: 396896,
      margem_sobre_pago_pct: "28.76",
      pago_sobre_recebe_pct: "77.67",
      lucro_sobre_recebe_pct: "22.33",
      sem_custo_compra: false,
      nas_periodicidades: [
        { periodicidade: "diaria", parcelas: 730, parcela_cliente_centavos: 2719 },
        { periodicidade: "semanal", parcelas: 104, parcela_cliente_centavos: 19101 },
        { periodicidade: "quinzenal", parcelas: 52, parcela_cliente_centavos: 38239 },
        { periodicidade: "mensal", parcelas: 24, parcela_cliente_centavos: 83039 },
      ],
    },
  },
  alertas: [],
  aviso_preco: null,
  pede_confirmacao_juros: false,
  pode_editar: true,
};

/** A Biz ADJ-4T71 sem valor de compra (T-505, VEI-13): o pago vazio, só as despesas; custo R$ 330,00 sem a
 * desvalorização; semanal R$ 299,40 a 85% com margem 70,08% marcada "sem custo de compra" e sem a faixa amarela,
 * mesmo com a mínima de 80%; na compra, sem lucro e sem margem sobre o pago. Números da API (`test_t505`). */
const compraPop = PRECOS_POP.plano_compra as NonNullable<PrecosDoVeiculo["plano_compra"]>;
const resultadoPop = compraPop.resultado as NonNullable<typeof compraPop.resultado>;
export const PRECOS_BIZ_SEM_COMPRA: PrecosDoVeiculo = {
  ...PRECOS_POP,
  veiculo: { id: 900, placa: "ADJ4T71", marca: "Honda", modelo: "Biz 125", status: "disponivel" },
  margem_minima_pct: "80.00",
  pago_na_moto: { total_centavos: null, compra_centavos: null, despesas_centavos: 0 },
  custos: { ...(PRECOS_POP.custos as NonNullable<PrecosDoVeiculo["custos"]>), custo_mes_centavos: 33000, sem_custo_compra: true },
  planos: PRECOS_POP.planos.map((p) =>
    p.tipo === "semanal" ? { ...p, valor_centavos: 29940, agendado: null, margem: { receita_mes_centavos: 110279, lucro_mes_centavos: 77279, margem_pct: "70.08", abaixo_da_minima: false, sem_custo_compra: true } } : p.margem ? { ...p, margem: { ...p.margem, sem_custo_compra: true } } : p,
  ),
  plano_compra: { ...compraPop, resultado: { ...resultadoPop, lucro_centavos: null, margem_sobre_pago_pct: null, pago_sobre_recebe_pct: null, lucro_sobre_recebe_pct: null, sem_custo_compra: true } },
};

/** Só o que `PUT` e `simular` precisam nos testes: devolve o documento do contrato; os testes de tela não conferem conta. */
export const precosDoVeiculoFalso = {
  async precos(id: number): Promise<PrecosDoVeiculo> {
    if (id !== 900) throw new ErroApi(404, "nao_encontrado", "Veículo não encontrado");
    return structuredClone(PRECOS_POP);
  },
  async salvarPrecos(_id: number, _corpo: PrecosEntrada): Promise<PrecosDoVeiculo> {
    return structuredClone(PRECOS_POP);
  },
  async simularPrecos(_id: number, _corpo: PrecosEntrada): Promise<PrecosDoVeiculo> {
    return structuredClone(PRECOS_POP);
  },
  async ligarPlano(_id: number, planoId: number, ligado: boolean): Promise<PrecosDoVeiculo> {
    const d = structuredClone(PRECOS_POP);
    const p = d.planos.find((x) => x.id === planoId);
    if (!p) throw new ErroApi(404, "nao_encontrado", "Plano não encontrado");
    p.ligado = ligado;
    return d;
  },
};
