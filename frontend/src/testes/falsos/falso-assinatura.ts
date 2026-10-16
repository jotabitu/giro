// DADOS FALSOS da assinatura nos testes (docs/api/assinatura.md). Só api-falsa.ts importa este arquivo.
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
  PedidoDeMudancaDePlano,
  PlanoParaMudar,
  PlanosParaMudar,
  RespostaDaForma,
  SimulacaoDeMudanca,
} from "@/lib/api/tipos-assinatura";
import { pausa } from "./falso";

const ACOES = { mudar_plano: true, desfazer_mudanca_plano: false, escolher_forma_pagamento: true, editar_dados_fiscais: true };

const SEED: Assinatura = {
  plano: { id: 2, nome: "Profissional", preco_contratado_centavos: 44900, ciclo: "mensal" },
  status: "em_teste",
  teste: { inicio: "2026-10-07", fim: "2026-10-21", dias_restantes: 14 },
  proxima_fatura: { vencimento: "2026-10-22", valor_centavos: 44900, descricao: "Plano Profissional · 22 out a 21 nov" },
  plano_proximo: null,
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

/** Troca partes da assinatura para o teste de um estado (inadimplente, suspensa, uso perto do limite). */
export function definirAssinaturaFalsa(mudanca: Partial<Assinatura> | null) {
  atual = mudanca ? { ...structuredClone(SEED), ...mudanca } : structuredClone(SEED);
  dadosFiscais = structuredClone(atual.dados_fiscais ?? (SEED.dados_fiscais as DadosFiscais));
  faturaPaga = false;
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

const comDados = (): Assinatura => structuredClone({ ...atual, dados_fiscais: dadosFiscais });

function planoDe(id: number): PlanoParaMudar {
  const p = PLANOS.find((x) => x.id === id);
  if (!p) throw new ErroApi(404, "nao_encontrado", "Plano não encontrado.");
  return p;
}

/** Como a API: 422 `PLT-04` com `detalhes` quando o uso não cabe. */
function conferir(corpo: PedidoDeMudancaDePlano): PlanoParaMudar {
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

export const assinaturaFalso = {
  async obter(): Promise<Assinatura> {
    await pausa(40);
    return comDados();
  },

  async planos(): Promise<PlanosParaMudar> {
    await pausa(40);
    return { ciclo_atual: "mensal", resultados: structuredClone(PLANOS) };
  },

  async simularMudanca(corpo: PedidoDeMudancaDePlano): Promise<SimulacaoDeMudanca> {
    await pausa(40);
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
    if (!atual.plano_proximo) throw new ErroApi(404, "nao_encontrado", "Não há mudança de plano agendada.");
    atual = { ...atual, plano_proximo: null, acoes: ACOES };
    return comDados();
  },

  async escolherForma(forma: FormaDaAssinatura): Promise<RespostaDaForma> {
    await pausa(60);
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
    const forma = atual.forma_pagamento?.forma ?? null;
    return { resultados: structuredClone([faturaAberta(forma), LINHA_DO_TESTE]), proximo: null, anterior: null };
  },

  async fatura(codigo: string): Promise<FaturaDetalhada> {
    await pausa(40);
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
};
