// DADOS FALSOS de docs/api/painel.md (seed Moto Rápida em 07 out 2026) enquanto o app `relatorios` não existe.
// Único módulo a trocar: reescreva `relatorios` em ./index.ts com o cliente gerado e apague este arquivo.
// Os blocos de módulo inexistente (fase 2) vêm `null`, como a API faz (USR-08).
import { contaAtualFalsa, pausa } from "./falso";
import { ErroApi } from "./tipos";
import type {
  Contadores,
  Inicio,
  InicioFinanceiro,
  InicioGeral,
  InicioGerente,
  InicioImplantacao,
  InicioVendedor,
  InicioVistoriador,
  Periodo,
} from "./tipos-painel";

const atualizadoHa6Min = () => new Date(Date.now() - 6 * 60_000).toISOString();

// Valor de cada contador do contrato (seed em 07 out). `null` = módulo que ainda não existe.
const CONTADORES: Record<string, number | null> = { veiculos: 86, locacoes: 42, aprovacoes: 3, receber: 7, despesas: 1, usuarios: 2, agenda: 6, avarias: 2, contas_a_pagar: 4, manutencoes: null, conciliacao: null, propostas: null };
const CONTADORES_DA_IMPLANTACAO: Record<string, number | null> = { ...CONTADORES, veiculos: 83, locacoes: 0, aprovacoes: 0, receber: 0, despesas: 0 };
const CONTADORES_DO_VENDEDOR: Record<string, number | null> = { ...CONTADORES, locacoes: 12 };

function geral(periodo: Periodo): InicioGeral {
  const receita = { hoje: 262_000, "7d": 1_840_000, "30d": 7_960_000 }[periodo];
  const rotuloPeriodo = { hoje: "hoje", "7d": "últimos 7 dias", "30d": "últimos 30 dias" }[periodo];
  return {
    variante: "geral",
    atencao: { quantidade: 7, texto: "7 contratos pedem atenção" },
    kpis: [
      { chave: "frota_ativa", rotulo: "Frota ativa", valor: { tipo: "numero", valor: 86 }, contexto: "52 motos · 34 carros", destaque: true },
      { chave: "alugados_agora", rotulo: "Alugados agora", valor: { tipo: "numero", valor: 42 }, contexto: "6 a mais esta semana", tendencia: "sobe" },
      { chave: "receita_locacao", rotulo: "Receita de locação", valor: { tipo: "centavos", valor: receita }, contexto: rotuloPeriodo },
      { chave: "em_atraso", rotulo: "Em atraso", valor: { tipo: "numero", valor: 2 }, contexto: "R$ 1.646,40 a receber" },
    ],
    frota: {
      ocupacao_pct: "71.00",
      meta_ocupacao_pct: "80.00",
      nota: "ocupação de 71% · meta de 80%",
      segmentos: [
        { status: "disponivel", rotulo: "Disponível", quantidade: 16 },
        { status: "alugado", rotulo: "Alugado", quantidade: 42 },
        { status: "reservado", rotulo: "Reservado", quantidade: 9 },
        { status: "em_manutencao", rotulo: "Manutenção", quantidade: 7 },
        { status: "a_venda", rotulo: "À venda", quantidade: 12 },
      ],
    },
    devolucoes_semana: {
      subtitulo: "6 contratos",
      linhas: [
        { locacao_id: 2841, codigo: "LOC-2841", placa: "QXA4B21", veiculo: "Honda CG 160 Fan", cliente: "Carlos Menezes", data: "2026-10-06", situacao: { rotulo: "Atrasado", tom: "perigo" } },
        { locacao_id: 2843, codigo: "LOC-2843", placa: "PNB7C04", veiculo: "Yamaha Factor 150", cliente: "Juliana Rocha", data: "2026-10-07", situacao: { rotulo: "Devolve hoje", tom: "info" } },
        { locacao_id: 2846, codigo: "LOC-2846", placa: "ROE2A88", veiculo: "Fiat Mobi Like", cliente: "Pedro Alencar", data: "2026-10-08", situacao: { rotulo: "Em dia", tom: "sucesso" } },
        { locacao_id: 2850, codigo: "LOC-2850", placa: "SAK1D39", veiculo: "Honda CG 160 Fan", cliente: "Aline Duarte", data: "2026-10-09", situacao: { rotulo: "Em dia", tom: "sucesso" } },
        { locacao_id: 2852, codigo: "LOC-2852", placa: "PMZ3E17", veiculo: "Honda Pop 110i", cliente: "Rafael Sousa", data: "2026-10-10", situacao: { rotulo: "Em dia", tom: "sucesso" } },
        { locacao_id: 2856, codigo: "LOC-2856", placa: "RHT9F02", veiculo: "Renault Kwid Zen", cliente: "Beatriz Lima", data: "2026-10-11", situacao: { rotulo: "Em dia", tom: "sucesso" } },
      ],
    },
    pendencias: {
      titulo: "7 contratos precisam de ação hoje",
      itens: [
        { texto: "3 devoluções estão atrasadas", gravidade: "critica", destino: { chave: "locacoes", filtro: "aba=precisam_acao" } },
        { texto: "2 parcelas vencem até amanhã", gravidade: "info", destino: { chave: "receber", filtro: "situacao=vencem_hoje" } },
      ],
    },
    caixa_hoje: { filial: "Filial Centro", data: "2026-10-07", status: "aberto", recebido_centavos: 118_260, a_receber_hoje_centavos: 189_000, despesas_centavos: 4_800, saldo_dia_centavos: 113_460 },
  };
}

const implantacao = (): InicioImplantacao => ({
  variante: "implantacao",
  teste: { fim: "2026-10-21", dias_restantes: 14, texto: "Seu teste grátis termina em 14 dias (21 out)." },
  primeiros_passos: {
    concluidos: 2,
    total: 3,
    pct: "66.67",
    itens: [
      { chave: "configuracao_inicial", rotulo: "Configuração inicial", detalhe: "Marca, filial, preços, contrato e 83 veículos importados", concluido: true },
      { chave: "convidar_equipe", rotulo: "Convidar a equipe", detalhe: "3 convites enviados", concluido: true },
      { chave: "primeira_locacao", rotulo: "Fazer uma locação de teste", detalhe: "Contrato, vistoria e assinatura com um cliente seu ou de teste", concluido: false, acao: { rotulo: "Começar", destino: "nova_locacao" } },
    ],
  },
  convites: [
    { nome: "Rodrigo Pinheiro", contato: "rodrigo@motorapida.com.br", perfil: "gerente", status: "aceito" },
    { nome: "João Silva", contato: "(85) 99654-2210", perfil: "vistoriador", status: "pendente" },
  ],
  indicadores: { frota_cadastrada: 83, alugados_agora: 0, clientes: 0, a_receber_centavos: 0 },
});

const gerente = (): InicioGerente => ({
  variante: "gerente",
  aprovacoes: {
    total: 3,
    mais_antigo: "há 2 h",
    itens: [
      { id: 88, tipo: "APR-01", titulo: "Desconto de 8% para Diego Martins", detalhe: "Bruna · CB 300F Twister · R$ 22.900,00 → R$ 21.068,00 (limite dela: 5%)", acoes: ["recusar", "aprovar"] },
      { id: 89, tipo: "APR-02", titulo: "Cancelar contrato LOC-2812", detalhe: "Patrícia Gomes pediu encerramento antecipado · multa de R$ 84,80", acoes: ["aprovar"] },
      { id: 90, tipo: "APR-03", titulo: "Despesa de R$ 1.200,00 · 2 pneus", detalhe: "João · PMZ3E17 · depois segue para o financeiro", acoes: ["recusar", "aprovar"] },
    ],
  },
  kpis: [
    { chave: "ocupacao", rotulo: "Ocupação", valor: { tipo: "pct", valor: "71.00" }, contexto: "meta de 80%" },
    { chave: "receita_semana", rotulo: "Receita da semana", valor: { tipo: "centavos", valor: 1_840_000 }, contexto: "6% a mais que a anterior", tendencia: "sobe" },
    { chave: "devolucoes_atrasadas", rotulo: "Devoluções atrasadas", valor: { tipo: "numero", valor: 3 }, contexto: "1 há mais de 2 dias" },
    { chave: "em_manutencao", rotulo: "Em manutenção", valor: null, contexto: null },
  ],
  equipe_hoje: [
    { usuario_id: 4, nome: "Bruna Alves", perfil: "vendedor", resumo: "3 locações hoje", online: true },
    { usuario_id: 5, nome: "João Silva", perfil: "vistoriador", resumo: "2 de 6 vistorias feitas", online: true },
    { usuario_id: 7, nome: "Lúcia Freitas", perfil: "financeiro", resumo: "último acesso ontem", online: false },
  ],
  frota_filial: {
    total: 83,
    segmentos: [
      { rotulo: "Livres", quantidade: 16 },
      { rotulo: "Alugados", quantidade: 42 },
      { rotulo: "Reserv.", quantidade: 9 },
      { rotulo: "Oficina e venda", quantidade: 16 },
    ],
  },
});

const vendedor = (): InicioVendedor => ({
  variante: "vendedor",
  kpis: [
    { chave: "minhas_locacoes_ativas", rotulo: "Minhas locações ativas", valor: { tipo: "numero", valor: 12 }, contexto: null },
    { chave: "devolvem_hoje", rotulo: "Devolvem hoje", valor: { tipo: "numero", valor: 2 }, contexto: null },
    { chave: "parcelas_atrasadas", rotulo: "Parcelas atrasadas", valor: { tipo: "numero", valor: 1 }, contexto: "R$ 299,40 de 1 cliente" },
  ],
  parcelas_atrasadas: [{ conta_id: 9010, cliente: "Carlos Menezes", locacao: "LOC-2841", vencimento: "2026-09-30", valor_centavos: 29_940, dias: 7, acao: "cobrar" }],
  precisam_acao: [{ locacao_id: 2856, codigo: "LOC-2856", cliente: "Lucas Ferreira", situacao: { rotulo: "Aguardando assinatura", tom: "alerta" } }],
  meta: null,
  funil: null,
  comissao_prevista: null,
  propostas: null,
});

const vistoriador = (): InicioVistoriador => ({
  variante: "vistoriador",
  avarias_abertas: 2,
  agenda: {
    resumo: "Terça, 07 out · 3 saídas e 3 devoluções",
    proxima: { item_id: "saida-2856", em_minutos: 20 },
    avarias_abertas: 2,
    resultados: [
      { id: "devolucao-2841", tipo: "devolucao", horario: "2026-10-06T21:00:00Z", veiculo: { id: 77, placa: "QXA4B21", modelo: "Honda CG 160" }, cliente: { nome: "Carlos Menezes" }, locacao: { id: 2841, codigo: "LOC-2841" }, situacao: { codigo: "atrasada", rotulo: "Atrasada", tom: "perigo" }, vistoria_id: null, acao: { codigo: "abrir", rotulo: "Abrir" } },
      { id: "saida-2856", tipo: "saida", horario: "2026-10-07T12:30:00Z", veiculo: { id: 501, placa: "SAK1D39", modelo: "Honda CG 160 Fan" }, cliente: { nome: "Lucas Ferreira" }, locacao: { id: 2856, codigo: "LOC-2856" }, situacao: { codigo: "agendada", rotulo: "Agendada", tom: "neutro" }, vistoria_id: null, acao: { codigo: "iniciar", rotulo: "Iniciar" } },
      { id: "devolucao-2843", tipo: "devolucao", horario: "2026-10-07T13:00:00Z", veiculo: { id: 78, placa: "PNB7C04", modelo: "Yamaha Factor 150" }, cliente: { nome: "Juliana Rocha" }, locacao: { id: 2843, codigo: "LOC-2843" }, situacao: { codigo: "hoje", rotulo: "Hoje", tom: "info" }, vistoria_id: null, acao: { codigo: "abrir", rotulo: "Abrir" } },
      { id: "saida-2858", tipo: "saida", horario: "2026-10-07T14:00:00Z", veiculo: { id: 502, placa: "PNB9A11", modelo: "Yamaha Factor 150" }, cliente: { nome: "Ana Lima" }, locacao: { id: 2858, codigo: "LOC-2858" }, situacao: { codigo: "em_andamento", rotulo: "Em andamento", tom: "alerta" }, vistoria_id: 3002, acao: { codigo: "continuar", rotulo: "Continuar" } },
    ],
  },
});

const financeiro = (): InicioFinanceiro => ({
  variante: "financeiro",
  kpis: [
    { chave: "entra_hoje", rotulo: "Entra hoje", valor: { tipo: "centavos", valor: 189_000 }, contexto: "9 parcelas" },
    { chave: "sai_hoje", rotulo: "Sai hoje", valor: { tipo: "centavos", valor: 41_230 }, contexto: "1 conta a pagar" },
    { chave: "em_atraso", rotulo: "Em atraso", valor: { tipo: "centavos", valor: 164_640 }, contexto: "2 clientes" },
    { chave: "saldo_em_contas", rotulo: "Saldo em contas", valor: null, contexto: null },
  ],
  caixas_do_dia: [{ filial: "Filial Centro", status: "aberto", aberto_por: "Bruna Alves", esperado_gaveta_centavos: 28_100 }],
  para_hoje: [
    { texto: "Devolver R$ 183,00 a Juliana Rocha por Pix", tipo: "reembolso", destino: { chave: "reembolsos", id: 31 } },
    { texto: "Pagar conta de luz · R$ 412,30", tipo: "despesa", destino: { chave: "contas_a_pagar", id: 803 } },
  ],
  fluxo_previsto: null,
  conciliacao: null,
});

function saudacaoDe(nome: string): string {
  const h = Number(new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", hour: "2-digit", hour12: false }).format(new Date())) % 24;
  return `${h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"}, ${nome.split(" ")[0]}`;
}

export const relatoriosFalso = {
  /** GET /api/painel/contadores/ */
  async contadores(): Promise<Contadores> {
    await pausa(80);
    const conta = contaAtualFalsa();
    if (!conta) throw new ErroApi(401, "nao_autenticado", "Entre para continuar");
    // Como na API: só vêm as chaves dos itens do menu que a pessoa vê.
    const valores = conta.variante === "implantacao" ? CONTADORES_DA_IMPLANTACAO : conta.variante === "vendedor" ? CONTADORES_DO_VENDEDOR : CONTADORES;
    const nav = conta.eu.navegacao;
    const chaves = [...nav.menu_inicio, ...nav.menu_completo].flatMap((g) => g.itens.flatMap((i) => (i.contador ? [i.contador] : [])));
    return { atualizado_em: atualizadoHa6Min(), contadores: Object.fromEntries(chaves.map((k) => [k, valores[k] ?? null])) };
  },

  /** GET /api/painel/inicio/: o corpo é o da variante da pessoa logada. */
  async inicio(periodo: Periodo = "7d"): Promise<Inicio> {
    await pausa(200);
    const conta = contaAtualFalsa();
    if (!conta) throw new ErroApi(401, "nao_autenticado", "Entre para continuar");
    const base = { saudacao: saudacaoDe(conta.nome), atualizado_em: atualizadoHa6Min() };
    switch (conta.variante) {
      case "geral":
        return { ...base, ...geral(periodo) };
      case "implantacao":
        return { ...base, ...implantacao() };
      case "gerente":
        return { ...base, ...gerente() };
      case "vendedor":
        return { ...base, ...vendedor() };
      case "vistoriador":
        return { ...base, ...vistoriador() };
      case "financeiro":
        return { ...base, ...financeiro() };
    }
  },
};
