// DADOS FALSOS da assinatura nos testes (docs/api/assinatura.md e docs/api/cancelamento.md). Só api-falsa.ts importa este arquivo.
// Seed: Moto Rápida em teste (07 a 21 out, 14 dias), plano Profissional R$ 449,00; uso 86/150, 1/3 e 5/10, sem aviso (PLT-03);
// sem forma de pagamento, FAT-0001 aberta (vence 22 out) e a linha do teste. Os números e as mensagens são os do contrato.
import { ErroApi } from "@/lib/api/tipos";
import type {
  Assinatura,
  CobrancaDaFatura,
  ConfirmacaoDeMudanca,
  CorrecaoDeDadosFiscais,
  DadosFiscais,
  FaturaDaAssinatura,
  FaturaDetalhada,
  FormaDaAssinatura,
  ListaDeFaturas,
  MeioDePagarFatura,
  MotivoCancelamento,
  PedidoDeCancelamentoDaAssinatura,
  PedidoDeMudancaDePlano,
  PedidoDePausa,
  PlanoParaMudar,
  PlanosParaMudar,
  RespostaDaForma,
  SimulacaoDeMudanca,
  TelaDoCancelamento,
} from "@/lib/api/tipos-assinatura";
import { nomeConfere } from "@/lib/assinatura";
import { dataCurta } from "@/lib/formatos";
import { pausa } from "./falso";

// T-195: na `em_teste`, o administrador pode cancelar; pausar só na `ativa` (PLT-06).
const ACOES = {
  mudar_plano: true,
  desfazer_mudanca_plano: false,
  escolher_forma_pagamento: true,
  editar_dados_fiscais: true,
  cancelar: true,
  desfazer_cancelamento: false,
  pausar: false,
  voltar_pausa: false,
  desistir_pausa: false,
};

const MOTIVOS: { codigo: MotivoCancelamento; rotulo: string }[] = [
  { codigo: "preco_alto", rotulo: "Preço alto para o meu tamanho" },
  { codigo: "faltou_funcao", rotulo: "Faltou alguma função" },
  { codigo: "outro_sistema", rotulo: "Vou usar outro sistema" },
  { codigo: "fechar_ou_pausar", rotulo: "Vou fechar ou pausar a locadora" },
  { codigo: "outro", rotulo: "Outro motivo" },
];

const SEED: Assinatura = {
  plano: { id: 2, nome: "Profissional", preco_contratado_centavos: 44900, ciclo: "mensal" },
  status: "em_teste",
  teste: { inicio: "2026-10-07", fim: "2026-10-21", dias_restantes: 14 },
  proxima_fatura: { vencimento: "2026-10-22", valor_centavos: 44900, descricao: "Plano Profissional · 22 out a 21 nov" },
  plano_proximo: null,
  cancelamento: null,
  pausa: null,
  faixa_aviso: null,
  uso: {
    veiculos: { usado: 86, limite: 150, aviso: false, bloqueado: false },
    filiais: { usado: 1, limite: 3, aviso: false, bloqueado: false },
    usuarios: { usado: 5, limite: 10, aviso: false, bloqueado: false },
  },
  somente_leitura: false,
  forma_pagamento: {
    forma: null,
    situacao: { codigo: "sem_forma", rotulo: "Nenhuma cadastrada. Escolha até 21 out para não perder o acesso.", tom: "alerta" },
    cartao: null,
    prazo: "2026-10-21",
  },
  dados_fiscais: {
    razao_social: "Moto Rápida Locações Ltda",
    cnpj: "12345678000195",
    endereco: { cep: "60325000", logradouro: "Av. Bezerra de Menezes", numero: "1200", complemento: null, bairro: "São Gerardo", cidade: "Fortaleza", uf: "CE" },
    email_cobranca: "financeiro@motorapida.com.br",
  },
  oferta: {
    titulo: "Precisa de mais veículos ou filiais?",
    plano: { id: 3, nome: "Completo", preco_mensal_centavos: 89900 },
    itens: ["Veículos, filiais e usuários sem limite", "Implantação acompanhada por chamada", "Suporte prioritário"],
  },
  acoes: ACOES,
};

const PLANOS: PlanoParaMudar[] = [
  {
    id: 1,
    nome: "Essencial",
    ordem: 1,
    atual: false,
    preco_mensal_centavos: 19900,
    preco_anual_centavos: 199000,
    limite_veiculos: 30,
    limite_filiais: 1,
    limite_usuarios: 3,
    itens: ["Locação, vistoria e contas a receber", "Contrato digital, assinado pelo cliente no celular", "Sua marca e seu endereço de acesso"],
    mudanca: "downgrade",
    cabe: false,
    excede: {
      veiculos: { usado: 86, limite: 30 },
      usuarios: { usado: 5, limite: 3 },
      abertos: [
        { grupo: "despesas_aguardando_aprovacao", quantidade: 1, texto: "1 despesa aguardando aprovação" },
        { grupo: "despesas_a_pagar", quantidade: 2, texto: "2 despesas a pagar" },
      ],
      abertos_texto: "1 despesa aguardando aprovação e 2 despesas a pagar",
    },
  },
  {
    id: 2,
    nome: "Profissional",
    ordem: 2,
    atual: true,
    preco_mensal_centavos: 44900,
    preco_anual_centavos: 449000,
    preco_contratado_centavos: 44900,
    limite_veiculos: 150,
    limite_filiais: 3,
    limite_usuarios: 10,
    itens: ["Vendas, manutenção e despesas", "Pix e boleto automáticos, cobrança pelo WhatsApp", "Comissão de vendedores e relatórios", "Até 150 veículos, 3 filiais e 10 usuários"],
    mudanca: null,
    cabe: true,
    excede: {},
  },
  {
    id: 3,
    nome: "Completo",
    ordem: 3,
    atual: false,
    preco_mensal_centavos: 89900,
    preco_anual_centavos: 899000,
    limite_veiculos: null,
    limite_filiais: null,
    limite_usuarios: null,
    itens: ["Tudo do Profissional", "Veículos, filiais e usuários sem limite", "Implantação acompanhada por chamada", "Suporte prioritário"],
    mudanca: "upgrade",
    cabe: true,
    excede: {},
  },
];

function faturaAberta(forma: FormaDaAssinatura | null): FaturaDaAssinatura {
  return {
    tipo: "fatura",
    codigo: "FAT-0001",
    vencimento: "2026-10-22",
    descricao: "Plano Profissional · 22 out a 21 nov",
    periodo: { inicio: "2026-10-22", fim: "2026-11-21" },
    valor_centavos: 44900,
    status: "aberta",
    forma: null,
    pago_em: null,
    situacao: forma ? { codigo: "aguardando", rotulo: "Vence em 22 out", tom: "info" } : { codigo: "sem_forma", rotulo: "Sem forma de pagamento", tom: "alerta" },
    acoes: { pagar: forma !== null, recibo: false, nota_fiscal: false },
  };
}

const LINHA_DO_TESTE: FaturaDaAssinatura = {
  tipo: "teste",
  codigo: null,
  vencimento: "2026-10-07",
  descricao: "Teste grátis de 14 dias",
  periodo: { inicio: "2026-10-07", fim: "2026-10-21" },
  valor_centavos: 0,
  status: null,
  forma: null,
  pago_em: null,
  situacao: { codigo: "teste_ativo", rotulo: "Ativo", tom: "info" },
  acoes: { pagar: false, recibo: false, nota_fiscal: false },
};

let atual: Assinatura = structuredClone(SEED);
let dadosFiscais: DadosFiscais = structuredClone(SEED.dados_fiscais as DadosFiscais);
let faturaPaga = false;
let mudancaCancelamento: Partial<TelaDoCancelamento> | null = null;

/** Troca partes da assinatura para o teste de um estado (inadimplente, suspensa, uso perto do limite). */
export function definirAssinaturaFalsa(mudanca: Partial<Assinatura> | null) {
  atual = mudanca ? { ...structuredClone(SEED), ...mudanca } : structuredClone(SEED);
  dadosFiscais = structuredClone(atual.dados_fiscais ?? (SEED.dados_fiscais as DadosFiscais));
  faturaPaga = false;
  if (!mudanca) mudancaCancelamento = null;
}

/** Ajusta a resposta de `GET /api/assinatura/cancelamento/` para cenários específicos (ex.: CA-ASS-69). */
export function definirCancelamentoFalso(mudanca: Partial<TelaDoCancelamento> | null) {
  mudancaCancelamento = mudanca;
}

/** A baixa da FAT-0001 vem do webhook na API real; no teste, esta função a simula. */
export function pagarFaturaNoParceiroFalso() {
  faturaPaga = true;
}

const ROTULO_DA_FORMA: Record<FormaDaAssinatura, string> = {
  cartao: "Você cadastra o cartão ao pagar a primeira fatura.",
  pix_automatico: "Autorize o Pix automático no app do seu banco.",
  boleto: "Boleto enviado por e-mail 5 dias antes",
};

function garantirEmpresaAtiva() {
  if (atual.status === "cancelada") {
    throw new ErroApi(403, "empresa_cancelada", "Esta assinatura foi cancelada. Para pedir seus dados ou voltar, fale com a equipe Giro.");
  }
}

const comDados = (): Assinatura => structuredClone({ ...atual, dados_fiscais: dadosFiscais });

function planoDe(id: number): PlanoParaMudar {
  const p = PLANOS.find((x) => x.id === id);
  if (!p) throw new ErroApi(404, "nao_encontrado", "Plano não encontrado.");
  return p;
}

/** Como a API: 422 `PLT-04` com `detalhes` quando o uso não cabe; 409 com cancelamento marcado (CA-ASS-56). */
function conferir(corpo: PedidoDeMudancaDePlano): PlanoParaMudar {
  if (atual.cancelamento) throw new ErroApi(409, "transicao_empresa", "Desfaça o cancelamento antes de mudar de plano.");
  const p = planoDe(corpo.plano_id);
  if (corpo.ciclo !== "mensal") throw new ErroApi(422, "mudanca_ciclo", "Para mudar entre mensal e anual, fale com o suporte.");
  if (p.atual) throw new ErroApi(422, "mesmo_plano", "Este já é o seu plano.");
  if (!p.cabe) {
    throw new ErroApi(
      422,
      "PLT-04",
      `Seu uso não cabe no plano ${p.nome}. Desative veículos ou usuários e resolva o que está aberto antes de mudar: ${p.excede.abertos_texto}.`,
      p.excede as Record<string, unknown>,
    );
  }
  return p;
}

function montarTelaCancelamento(): TelaDoCancelamento {
  const terminaAgora = atual.status === "inadimplente" || atual.status === "suspensa" || atual.status === "pausada";
  const anual = atual.plano.ciclo === "anual";
  const acessoAte = terminaAgora ? null : atual.status === "em_teste" && !faturaPaga ? "2026-10-21" : anual ? "2027-10-21" : "2026-11-21";
  const canceladaEm = terminaAgora ? "2026-10-25" : acessoAte === "2026-10-21" ? "2026-10-22" : anual ? "2027-10-22" : "2026-11-22";
  const apagarEm = terminaAgora ? "2027-01-23" : acessoAte === "2026-10-21" ? "2027-01-20" : anual ? "2028-01-20" : "2027-02-20";
  const acessoValor =
    acessoAte === null
      ? "termina agora"
      : anual && acessoAte === "2027-10-21"
        ? "continua até 21 out 2027, sem devolução"
        : `continua até ${dataCurta(acessoAte)}`;
  const cobrancasValor =
    atual.status === "inadimplente" || atual.status === "suspensa"
      ? "nenhuma nova. A fatura em atraso continua devida."
      : anual && acessoAte === "2027-10-21"
        ? "nenhuma. Os meses que faltam não são devolvidos."
        : "nenhuma";
  const planoResumo =
    atual.status === "em_teste" && atual.teste
      ? `Plano ${atual.plano.nome} · em teste até ${dataCurta(atual.teste.fim)}`
      : anual
        ? `Plano ${atual.plano.nome} · anual até 21 out 2027`
        : `Plano ${atual.plano.nome} · mensal`;
  const podePausar = atual.status === "ativa" && !atual.cancelamento && !atual.pausa && atual.acoes?.pausar !== false;
  const podeMudar = (atual.status === "em_teste" || atual.status === "ativa") && !atual.cancelamento && atual.plano.nome !== "Essencial";

  const base: TelaDoCancelamento = {
    empresa: "Moto Rápida",
    plano_resumo: planoResumo,
    motivos: structuredClone(MOTIVOS),
    alternativas: {
      pausar: podePausar ? { meses: [1, 2, 3], inicio: "2026-11-22", texto: "A pausa começa em 22 nov, no fim do período pago." } : null,
      mudar_para_essencial: podeMudar
        ? {
            plano: { id: 1, nome: "Essencial", preco_mensal_centavos: 19900 },
            resumo: "Até 30 veículos, 1 filial e 3 usuários.",
            cabe: PLANOS[0]?.cabe ?? false,
            excede: structuredClone(PLANOS[0]?.excede ?? {}),
          }
        : null,
    },
    o_que_acontece: [
      { codigo: "acesso", rotulo: "Acesso", valor: acessoValor },
      { codigo: "cobrancas", rotulo: "Cobranças futuras", valor: cobrancasValor },
      { codigo: "dados", rotulo: "Seus dados", valor: "guardados por 90 dias" },
      { codigo: "apagamento", rotulo: "Depois de 90 dias", valor: "apagados de vez" },
      { codigo: "contratos", rotulo: "Contratos dos seus clientes", valor: "continuam válidos" },
    ],
    acesso_ate: acessoAte,
    cancelada_em: canceladaEm,
    apagar_em: apagarEm,
    confirmacao: { nome: "Moto Rápida" },
    exportar: { texto: "Exportar baixa a auditoria em CSV. O resto dos seus dados você pede à equipe Giro." },
  };
  return mudancaCancelamento ? { ...base, ...structuredClone(mudancaCancelamento) } : base;
}

export const assinaturaFalso = {
  async obter(): Promise<Assinatura> {
    await pausa(40);
    garantirEmpresaAtiva();
    return comDados();
  },

  async planos(): Promise<PlanosParaMudar> {
    await pausa(40);
    garantirEmpresaAtiva();
    return { ciclo_atual: "mensal", resultados: structuredClone(PLANOS) };
  },

  async simularMudanca(corpo: PedidoDeMudancaDePlano): Promise<SimulacaoDeMudanca> {
    await pausa(40);
    garantirEmpresaAtiva();
    const p = conferir(corpo);
    if (p.mudanca === "downgrade") {
      return {
        tipo: "downgrade",
        vale_em: "2026-11-22",
        preco_novo_centavos: p.preco_mensal_centavos,
        diferenca_centavos: 0,
        fatura_diferenca: null,
        proxima_fatura: null,
        mensagem: `O plano ${p.nome} vale a partir de 22 nov. Até lá, você continua no Profissional.`,
      };
    }
    return {
      tipo: "upgrade",
      vale_em: "2026-10-10",
      preco_novo_centavos: p.preco_mensal_centavos,
      diferenca_centavos: 0,
      fatura_diferenca: null,
      proxima_fatura: { vencimento: "2026-10-22", valor_centavos: p.preco_mensal_centavos, descricao: `Plano ${p.nome} · 22 out a 21 nov` },
      mensagem: `O plano ${p.nome} vale agora. A primeira fatura, em 22 out, fica em R$ 899,00.`,
    };
  },

  async mudarPlano(corpo: ConfirmacaoDeMudanca): Promise<Assinatura> {
    await pausa(60);
    garantirEmpresaAtiva();
    const p = conferir(corpo);
    const simulacao = await assinaturaFalso.simularMudanca(corpo);
    if (corpo.confirmar_valor_centavos !== simulacao.diferenca_centavos) {
      throw new ErroApi(409, "valor_mudou", "O valor da diferença mudou. Confira o novo valor antes de confirmar.", { diferenca_centavos: simulacao.diferenca_centavos });
    }
    if (p.mudanca === "downgrade") {
      atual = { ...atual, plano_proximo: { id: p.id, nome: p.nome, ciclo: "mensal", vale_em: "2026-11-22" }, acoes: { ...ACOES, desfazer_mudanca_plano: true } };
    } else {
      atual = { ...atual, plano: { id: p.id, nome: p.nome, preco_contratado_centavos: p.preco_mensal_centavos, ciclo: "mensal" }, proxima_fatura: simulacao.proxima_fatura, oferta: null };
    }
    return comDados();
  },

  async desfazerMudanca(): Promise<Assinatura> {
    await pausa(40);
    garantirEmpresaAtiva();
    if (atual.cancelamento) throw new ErroApi(409, "transicao_empresa", "Desfaça o cancelamento antes de mudar de plano.");
    if (!atual.plano_proximo) throw new ErroApi(404, "nao_encontrado", "Não há mudança de plano agendada.");
    atual = { ...atual, plano_proximo: null, acoes: ACOES };
    return comDados();
  },

  async escolherForma(forma: FormaDaAssinatura): Promise<RespostaDaForma> {
    await pausa(60);
    garantirEmpresaAtiva();
    const situacao =
      forma === "pix_automatico"
        ? { codigo: "aguardando_autorizacao", rotulo: ROTULO_DA_FORMA[forma], tom: "alerta" }
        : forma === "cartao"
          ? { codigo: "cartao_na_primeira_fatura", rotulo: ROTULO_DA_FORMA[forma], tom: "info" }
          : { codigo: "ativa", rotulo: ROTULO_DA_FORMA[forma], tom: "sucesso" };
    const nova = { forma, situacao, cartao: null, prazo: null };
    atual = { ...atual, forma_pagamento: nova };
    return {
      forma_pagamento: structuredClone(nova),
      proximo_passo:
        forma === "pix_automatico"
          ? { tipo: "autorizar_pix", pix_copia_e_cola: "00020126580014br.gov.bcb.pix0136giro-autorizacao-recorrente5204000053039865802BR5909MotoRapida6007Fortaleza62070503***6304ABCD", expira_em: "2026-10-08T15:00:00Z" }
          : forma === "cartao"
            ? { tipo: "pagina_parceiro", url: "https://pagamentos.example/fatura/FAT-0001", fatura: "FAT-0001" }
            : null,
    };
  },

  async faturas(): Promise<ListaDeFaturas> {
    await pausa(40);
    garantirEmpresaAtiva();
    const forma = atual.forma_pagamento?.forma ?? null;
    const primeira = atual.cancelamento && atual.status === "em_teste" && !faturaPaga
      ? { ...faturaAberta(forma), status: "cancelada" as const, situacao: { codigo: "cancelada", rotulo: "Cancelada", tom: "neutro" }, acoes: { pagar: false, recibo: false, nota_fiscal: false } }
      : faturaAberta(forma);
    return { resultados: structuredClone([primeira, LINHA_DO_TESTE]), proximo: null, anterior: null };
  },

  async fatura(codigo: string): Promise<FaturaDetalhada> {
    await pausa(40);
    garantirEmpresaAtiva();
    if (codigo !== "FAT-0001") throw new ErroApi(404, "nao_encontrado", "Fatura não encontrada.");
    const base = faturaAberta(atual.forma_pagamento?.forma ?? null);
    if (faturaPaga) {
      return {
        ...base,
        status: "paga",
        forma: "pix",
        pago_em: "2026-10-18T13:00:00Z",
        situacao: { codigo: "paga", rotulo: "Paga em 18 out", tom: "sucesso" },
        acoes: { pagar: false, recibo: true, nota_fiscal: false },
        cobranca: null,
        recibo_url: "https://pagamentos.example/recibo/FAT-0001",
        nota_fiscal: null,
      };
    }
    return { ...base, cobranca: null, recibo_url: null, nota_fiscal: null };
  },

  async pagarFatura(codigo: string, meio?: MeioDePagarFatura): Promise<CobrancaDaFatura> {
    await pausa(60);
    garantirEmpresaAtiva();
    if (codigo !== "FAT-0001") throw new ErroApi(404, "nao_encontrado", "Fatura não encontrada.");
    if (faturaPaga) throw new ErroApi(409, "fatura_nao_pagavel", "Esta fatura já foi paga ou cancelada.");
    const forma = atual.forma_pagamento?.forma ?? null;
    const escolhido = meio ?? (forma === "cartao" ? "cartao" : forma === "boleto" ? "boleto" : forma === "pix_automatico" ? "pix" : null);
    if (!escolhido) throw new ErroApi(422, "sem_forma_pagamento", "Escolha a forma de pagamento antes.");
    return {
      forma: escolhido,
      linha_digitavel: escolhido === "boleto" ? "34191.79001 01043.510047 91020.150008 5 91070026000" : null,
      url_boleto: escolhido === "boleto" ? "https://pagamentos.example/boleto/FAT-0001" : null,
      pix_copia_e_cola: escolhido === "pix" || escolhido === "boleto" ? "00020126360014br.gov.bcb.pix0114giro-fatura-0001520400005303986540544.905802BR5909MotoRapida6007Fortaleza62070503***6304EF01" : null,
      url_pagina: escolhido === "cartao" ? "https://pagamentos.example/fatura/FAT-0001" : null,
      vencimento: "2026-10-22",
    };
  },

  async editarDadosFiscais(corpo: CorrecaoDeDadosFiscais & { cnpj?: string }): Promise<{ dados_fiscais: DadosFiscais }> {
    await pausa(60);
    garantirEmpresaAtiva();
    const campos: Record<string, string> = {};
    if (corpo.cnpj !== undefined) campos.cnpj = "O CNPJ não muda por aqui. Fale com o suporte.";
    if (corpo.razao_social !== undefined && !corpo.razao_social.trim()) campos.razao_social = "Informe a razão social.";
    if (corpo.email_cobranca !== undefined && !/^\S+@\S+\.\S+$/.test(corpo.email_cobranca)) campos.email_cobranca = "Informe um e-mail válido.";
    if (corpo.endereco !== undefined && !/^\d{8}$/.test(corpo.endereco.cep)) campos.endereco = "O CEP tem 8 números.";
    if (Object.keys(campos).length > 0) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, campos);
    dadosFiscais = {
      ...dadosFiscais,
      ...(corpo.razao_social !== undefined && { razao_social: corpo.razao_social.trim() }),
      ...(corpo.email_cobranca !== undefined && { email_cobranca: corpo.email_cobranca.trim() }),
      ...(corpo.endereco !== undefined && { endereco: corpo.endereco }),
    };
    return { dados_fiscais: structuredClone(dadosFiscais) };
  },

  async telaCancelamento(): Promise<TelaDoCancelamento> {
    await pausa(40);
    garantirEmpresaAtiva();
    if (atual.cancelamento) {
      throw new ErroApi(409, "transicao_empresa", `A assinatura já está cancelada. Você tem acesso até ${dataCurta(atual.cancelamento.acesso_ate)}.`);
    }
    return montarTelaCancelamento();
  },

  async cancelar(corpo: PedidoDeCancelamentoDaAssinatura): Promise<Assinatura> {
    await pausa(60);
    garantirEmpresaAtiva();
    if (atual.cancelamento) {
      throw new ErroApi(409, "transicao_empresa", `A assinatura já está cancelada. Você tem acesso até ${dataCurta(atual.cancelamento.acesso_ate)}.`);
    }
    if (!corpo.motivo || !MOTIVOS.some((m) => m.codigo === corpo.motivo)) {
      throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { motivo: "Escolha o motivo." });
    }
    const tela = montarTelaCancelamento();
    if (!nomeConfere(corpo.nome_confirmacao ?? "", tela.confirmacao.nome)) {
      throw new ErroApi(422, "nome_nao_confere", "O nome digitado não confere com o nome da empresa.");
    }
    if (tela.acesso_ate === null) {
      atual = {
        ...atual,
        status: "cancelada",
        cancelamento: null,
        pausa: null,
        proxima_fatura: null,
        acoes: {
          mudar_plano: false,
          desfazer_mudanca_plano: false,
          escolher_forma_pagamento: false,
          editar_dados_fiscais: false,
          cancelar: false,
          desfazer_cancelamento: false,
          pausar: false,
          voltar_pausa: false,
          desistir_pausa: false,
        },
      };
      return comDados();
    }
    const rotuloData = atual.plano.ciclo === "anual" && tela.acesso_ate === "2027-10-21" ? "21 out 2027" : dataCurta(tela.acesso_ate);
    atual = {
      ...atual,
      proxima_fatura: null,
      pausa: null,
      cancelamento: {
        pedido_em: "2026-10-10T13:00:00Z",
        motivo: corpo.motivo,
        acesso_ate: tela.acesso_ate,
        rotulo: `Assinatura cancelada. Você tem acesso até ${rotuloData}.`,
      },
      acoes: {
        ...(atual.acoes ?? ACOES),
        mudar_plano: false,
        desfazer_mudanca_plano: false,
        cancelar: false,
        desfazer_cancelamento: true,
        pausar: false,
        voltar_pausa: false,
        desistir_pausa: false,
      },
    };
    return comDados();
  },

  async desfazerCancelamento(): Promise<Assinatura> {
    await pausa(60);
    garantirEmpresaAtiva();
    if (!atual.cancelamento) {
      throw new ErroApi(409, "transicao_empresa", "Não há cancelamento para desfazer.");
    }
    atual = {
      ...atual,
      cancelamento: null,
      proxima_fatura: structuredClone(SEED.proxima_fatura),
      acoes: {
        ...(atual.acoes ?? ACOES),
        mudar_plano: atual.status === "em_teste" || atual.status === "ativa",
        desfazer_mudanca_plano: atual.plano_proximo !== null,
        cancelar: true,
        desfazer_cancelamento: false,
        pausar: atual.status === "ativa",
      },
    };
    return comDados();
  },

  async pausar(corpo: PedidoDePausa): Promise<Assinatura> {
    await pausa(60);
    garantirEmpresaAtiva();
    if (![1, 2, 3].includes(corpo.meses)) {
      throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { meses: "Escolha de 1 a 3 meses." });
    }
    if (atual.cancelamento) {
      throw new ErroApi(409, "transicao_empresa", "Desfaça o cancelamento antes de pausar.");
    }
    if (atual.pausa) {
      throw new ErroApi(409, "transicao_empresa", `Já existe uma pausa marcada até ${dataCurta(atual.pausa.ate)}.`);
    }
    if (atual.status === "em_teste") {
      throw new ErroApi(409, "transicao_empresa", "A pausa só vale para a assinatura ativa. No teste, você pode cancelar ou mudar de plano.");
    }
    if (atual.status === "inadimplente" || atual.status === "suspensa") {
      throw new ErroApi(409, "transicao_empresa", "Pague a fatura em atraso antes de pausar.");
    }
    if (atual.status === "pausada") {
      throw new ErroApi(403, "empresa_sem_operacao", "Sua empresa está só para consulta no momento.");
    }
    const ate = corpo.meses === 1 ? "2026-12-21" : corpo.meses === 2 ? "2027-01-21" : "2027-02-21";
    const volta = corpo.meses === 1 ? "2026-12-22" : corpo.meses === 2 ? "2027-01-22" : "2027-02-22";
    atual = {
      ...atual,
      proxima_fatura: null,
      pausa: {
        situacao: "agendada",
        meses: corpo.meses,
        inicio: "2026-11-22",
        ate,
        volta_em: volta,
        rotulo: `Pausa marcada de 22 nov a ${dataCurta(ate)}. Até lá, tudo continua.`,
      },
      acoes: {
        ...(atual.acoes ?? ACOES),
        pausar: false,
        desistir_pausa: true,
        voltar_pausa: false,
      },
    };
    return comDados();
  },

  async encerrarPausa(): Promise<Assinatura> {
    await pausa(60);
    garantirEmpresaAtiva();
    if (!atual.pausa && atual.status !== "pausada") {
      throw new ErroApi(409, "transicao_empresa", "Não há pausa para encerrar.");
    }
    atual = {
      ...atual,
      status: "ativa",
      pausa: null,
      faixa_aviso: null,
      somente_leitura: false,
      proxima_fatura: structuredClone(SEED.proxima_fatura),
      acoes: {
        ...(atual.acoes ?? ACOES),
        mudar_plano: true,
        cancelar: true,
        pausar: true,
        voltar_pausa: false,
        desistir_pausa: false,
      },
    };
    return comDados();
  },
};
