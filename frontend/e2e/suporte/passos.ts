// Os passos do fluxo de locação, pelas telas (T-025). Cada função faz uma coisa, confere o que a tela mostra
// contra os números das regras e devolve o que o passo seguinte precisa. Desktop e celular usam os mesmos passos.
import { expect, type Browser, type Locator, type Page, type TestInfo } from "@playwright/test";
import { executarNoBackend } from "./ambiente";
import { aquietar, defeitoConhecido, entrar, fotoDeTeste, novaSessao, visivel } from "./tela";

export const CLIENTE = {
  nome: "Paulo Henrique Lima",
  cpf: "529.982.247-25",
  nascimento: "1994-03-12",
  celular: "(85) 98765-4321",
  email: "paulo.lima@example.com",
  profissao: "Entregador",
  cnh: { numero: "04512345678", categoria: "A", validade: "2029-05-20", primeira: "2014-06-01" },
  endereco: { cep: "60325-000", logradouro: "Av. Bezerra de Menezes", numero: "1200", bairro: "São Gerardo", cidade: "Fortaleza", uf: "CE" },
  referencia: { nome: "Marta Lima", parentesco: "Mãe", telefone: "(85) 98888-7777" },
};
/** CPF da Juliana Rocha, que já está no seed: o cadastro de um segundo cliente com ele é recusado (CLI-01). */
export const CPF_JA_CADASTRADO = "052.218.330-18";

const DOCUMENTOS = ["CNH · frente", "CNH · verso", "Selfie com documento", "Comprovante de residência"] as const;
const FOTOS_OBRIGATORIAS = ["Frente", "Traseira", "Lateral esquerda", "Lateral direita", "Painel e hodômetro"] as const;
const ITENS = ["Pneus e freios", "Luzes e buzina", "Retrovisores", "Documento e chave", "Acessórios entregues"] as const;

export const VEICULO = { busca: "CG 160", modelo: "Honda CG 160 Fan" };
export const KM_DO_CADASTRO = 28_420;
export const KM_RODADOS = 420;
export const AVARIA_ANTIGA = "risco no para-lama";
export const AVARIA_NOVA = { descricao: "carenagem lateral quebrada", valor: "380,00" };

// --- Cliente ---

export async function preencherCliente(page: Page, cpf: string, nome: string) {
  await page.locator("input[name=nome]").fill(nome);
  await page.locator("input[name=documento]").fill(cpf);
  await page.locator("input[name=nascimento]").fill(CLIENTE.nascimento);
  await page.locator("input[name=celular]").fill(CLIENTE.celular);
  await page.locator("input[name=email]").fill(CLIENTE.email);
  await page.locator("input[name=profissao]").fill(CLIENTE.profissao);
  await page.locator("input[name='cnh.numero']").fill(CLIENTE.cnh.numero);
  await page.locator("select[name='cnh.categoria']").selectOption(CLIENTE.cnh.categoria);
  await page.locator("input[name='cnh.validade']").fill(CLIENTE.cnh.validade);
  await page.locator("input[name='cnh.primeira_habilitacao']").fill(CLIENTE.cnh.primeira);
  const e = CLIENTE.endereco;
  await page.locator("input[name='endereco.cep']").fill(e.cep);
  await page.locator("input[name='endereco.logradouro']").fill(e.logradouro);
  await page.locator("input[name='endereco.numero']").fill(e.numero);
  await page.locator("input[name='endereco.bairro']").fill(e.bairro);
  await page.locator("input[name='endereco.cidade']").fill(e.cidade);
  await page.locator("input[name='endereco.uf']").fill(e.uf);
  const r = CLIENTE.referencia;
  await page.locator("input[name='referencia.nome']").fill(r.nome);
  await page.locator("input[name='referencia.parentesco']").fill(r.parentesco);
  await page.locator("input[name='referencia.telefone']").fill(r.telefone);
  await page.locator("input[name=consentimento]").check();
}

/** CLI-01: o CPF da Juliana já existe e a tela recusa com o aviso e o link para o cadastro dela. */
export async function recusarCpfJaCadastrado(page: Page) {
  await page.goto("/clientes/novo");
  await preencherCliente(page, CPF_JA_CADASTRADO, "Outra Pessoa");
  await page.getByRole("button", { name: "Salvar cliente" }).click();
  await expect(page.getByText(/já está cadastrado/).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Abrir o cadastro existente" })).toBeVisible();
}

/**
 * CLI-03: antes das fotos a análise mostra o cadastro incompleto; as fotos só se enviam depois de salvar
 * (a tela não aceita arquivo antes do primeiro "Salvar cliente"). Devolve o id do cliente.
 */
export async function cadastrarCliente(page: Page): Promise<number> {
  await page.goto("/clientes/novo");
  await preencherCliente(page, CLIENTE.cpf, CLIENTE.nome);
  await expect(page.getByText("CPF válido")).toBeVisible();
  await expect(page.getByText("CNH categoria A, válida")).toBeVisible();
  await expect(page.getByText("Faltam 4 documentos")).toBeVisible();
  await page.getByRole("button", { name: "Salvar cliente" }).click();
  await expect(page).toHaveURL(/\/clientes\/\d+$/);
  const id = Number(/\/clientes\/(\d+)$/.exec(page.url())?.[1]);
  await expect(page.getByRole("heading", { name: CLIENTE.nome })).toBeVisible();

  for (const [i, nome] of DOCUMENTOS.entries()) {
    await page.getByLabel(nome, { exact: true }).setInputFiles(fotoDeTeste());
    await expect(page.getByText("enviado", { exact: true }).filter({ visible: true })).toHaveCount(i + 1);
  }
  return id;
}

// --- Nova locação ---

export type LocacaoCriada = { id: number; codigo: string };

/** Passo 1 · Dados. Plano semanal, início hoje na hora de agora, pagamento em dinheiro: R$ 329,00 + caução R$ 300,00 (LOC-04, LOC-05). */
export async function criarLocacao(page: Page, clienteId: number, horaDeRetirada: string, dia = "2026-10-07"): Promise<LocacaoCriada> {
  await page.goto(`/locacoes/nova?cliente=${clienteId}`);
  await expect(page.getByText(CLIENTE.nome)).toBeVisible();
  await expect(page.getByText("CNH A · válida até 2029")).toBeVisible();

  await page.getByRole("button", { name: "Veículo: escolher" }).click();
  const busca = page.getByRole("dialog").getByPlaceholder("Placa ou modelo");
  await busca.fill(VEICULO.busca);
  const primeiro = page.getByRole("dialog").locator("li button").first();
  await expect(primeiro).toContainText(VEICULO.modelo);
  await primeiro.click();
  await expect(page.getByText(VEICULO.modelo)).toBeVisible();

  await page.getByRole("button", { name: /^Semanal/ }).click();
  await page.locator("input[name=inicio]").fill(`${dia}T${horaDeRetirada}`);
  await page.getByLabel("Forma de pagamento").selectOption({ label: "Dinheiro" });

  // O resumo vem da simulação da API (ADR 0005): período, caução e o total da retirada.
  const resumo = page.locator("section", { hasText: "Hoje, na retirada" }).last();
  await expect(resumo).toContainText("1 semana × R$ 329,00");
  await expect(resumo).toContainText("R$ 329,00");
  await expect(resumo).toContainText("Caução (devolvida no fim)");
  await expect(resumo).toContainText("R$ 300,00");
  await expect(resumo.getByText("R$ 629,00")).toBeVisible();

  await page.getByRole("button", { name: "Continuar para vistoria" }).click();
  await expect(page).toHaveURL(/\/locacoes\/\d+\/vistoria$/);
  const id = Number(/\/locacoes\/(\d+)\/vistoria$/.exec(page.url())?.[1]);
  const codigo = (await page.getByText(/^Locações \/ LOC-\d+$/).first().innerText()).replace("Locações / ", "");
  expect(codigo).toMatch(/^LOC-\d{4}$/);
  return { id, codigo };
}

// --- Vistoria ---

function inputDaFoto(page: Page, posicao: string): Locator {
  // O botão da posição e o <input type=file> escondido são irmãos. Depois da foto, o nome do botão vira "Frente: foto de 14:05…".
  return page.getByRole("button", { name: new RegExp(`^${posicao}:`) }).locator("xpath=following-sibling::input[1]");
}

async function nivelCheio(page: Page) {
  const cheio = page.getByRole("group", { name: "Nível de combustível" }).getByRole("button").last();
  await cheio.click();
  await expect(cheio).toHaveAttribute("aria-pressed", "true");
}

async function marcarItens(page: Page) {
  for (const nome of ITENS) {
    const caixa = page.getByRole("checkbox", { name: nome });
    await caixa.click();
    await expect(caixa).toBeChecked();
  }
}

async function enviarFotos(page: Page) {
  for (const [i, posicao] of FOTOS_OBRIGATORIAS.entries()) {
    await inputDaFoto(page, posicao).setInputFiles(fotoDeTeste());
    await expect(page.getByText(`${i + 1} de 5 obrigatórias`).or(page.getByText(`${i + 1} de 5 fotos obrigatórias`))).toBeVisible();
  }
}

async function registrarAvaria(page: Page, descricao: string, oficina = false) {
  await page.getByRole("button", { name: "Registrar avaria", exact: true }).click();
  const dialogo = page.getByRole("dialog");
  await dialogo.getByLabel("O que aconteceu").fill(descricao);
  await dialogo.locator("#foto-da-avaria").setInputFiles(fotoDeTeste());
  if (oficina) await dialogo.getByLabel("O veículo vai para a oficina").check();
  await dialogo.getByRole("button", { name: "Registrar avaria" }).click();
  await expect(dialogo).toBeHidden();
  await expect(page.getByText(descricao, { exact: false }).first()).toBeVisible();
}

async function digitarKm(page: Page, rotulo: string, km: number) {
  const campo = page.getByLabel(rotulo);
  await campo.fill(String(km));
  await campo.blur();
  await expect(campo).toHaveValue(new Intl.NumberFormat("pt-BR").format(km));
}

/**
 * Passo 2 · Vistoria de saída (VIS-01 a VIS-04, VEI-01), na tela `/locacoes/{id}/vistoria`.
 * Confere o que não deixa concluir (sem fotos, km menor) antes do caminho certo.
 */
export async function vistoriaDeSaida(page: Page, locacaoId: number, opcoes: { verValores: boolean }) {
  await page.goto(`/locacoes/${locacaoId}/vistoria`);
  await expect(page.getByRole("heading", { name: /^Check-out da/ })).toBeVisible();
  const concluir = page.getByRole("button", { name: "Continuar para assinatura" });

  // VIS-02: sem as 5 fotos a tela não deixa concluir e diz o que falta.
  await expect(concluir).toBeDisabled();
  await expect(page.getByText("Faltam 5 fotos obrigatórias")).toBeVisible();

  // O cliente na vistoria: o vistoriador vê nome, celular e se a retirada está liberada, sem valores (USR-09).
  await expect(visivel(page.getByText(CLIENTE.nome))).toBeVisible();
  await expect(visivel(page.getByText("Liberada"))).toBeVisible();
  if (opcoes.verValores) {
    await expect(visivel(page.getByText("R$ 300,00 a receber"))).toBeVisible();
  } else {
    await expect(page.getByText(/R\$ \d/).filter({ visible: true })).toHaveCount(0);
  }

  await enviarFotos(page);
  await nivelCheio(page);
  await marcarItens(page);
  await registrarAvaria(page, AVARIA_ANTIGA);

  // VEI-01: km menor que o do veículo é recusado com a mensagem da API; o km do cadastro passa.
  const kmDaSaida = page.getByLabel("Quilometragem na saída");
  await kmDaSaida.fill(String(KM_DO_CADASTRO - 420));
  await kmDaSaida.blur();
  await expect(concluir).toBeDisabled();
  // D-02: o botão fica desligado com o texto genérico "Informe a quilometragem"; a mensagem do VEI-01 (km menor que o atual) não chega à tela.
  await defeitoConhecido("D-02", "km menor que o do veículo (VEI-01): a tela não mostra a mensagem da API", async () => {
    await expect(visivel(page.getByText(/menor que o atual/))).toBeVisible({ timeout: 3000 });
  });
  await expect(page).toHaveURL(/\/vistoria$/);

  await digitarKm(page, "Quilometragem na saída", KM_DO_CADASTRO);
  await expect(concluir).toBeEnabled();
  await concluir.click();
  await expect(page).toHaveURL(new RegExp(`/locacoes/${locacaoId}$`));
}

/** A vistoria concluída não abre mais para edição (VIS-04). */
export async function vistoriaFechadaParaEdicao(page: Page, locacaoId: number) {
  await page.goto(`/locacoes/${locacaoId}/vistoria`);
  await expect(page.getByRole("alert").filter({ hasText: "Esta vistoria já foi concluída" })).toBeVisible();
  await expect(page.getByLabel("Quilometragem na saída")).toHaveCount(0);
}

// --- Contrato e assinatura (CA-025-05) ---

/**
 * Gera o contrato e o link de assinatura. A tela ainda não tem o botão de enviar o contrato (a API é
 * `POST /api/locacoes/{id}/contrato/`), então o teste chama o mesmo serviço do backend e pega o token do link.
 * Lacuna registrada no handoff da T-025: o frontend precisa do botão e da página `/assinar`.
 */
export function gerarContratoEPegarToken(codigo: string): string {
  const saida = executarNoBackend(`
import time
from django_tenants.utils import schema_context
from apps.plataforma.models import Empresa
from apps.locacoes.models import Locacao
from apps.locacoes import contrato
from apps.contratos.models import Contrato
from apps.contratos.services import novo_token
empresa = Empresa.objects.get(subdominio="motorapida")
with schema_context(empresa.schema_name):
    locacao = Locacao.objects.get(codigo="${codigo}")
    gerado = Contrato.objects.filter(origem_id=locacao.pk).first() or contrato.gerar(locacao)
    for _ in range(60):
        gerado.refresh_from_db()
        if gerado.status != "gerado":
            break
        time.sleep(0.5)
    print("STATUS=" + gerado.status)
    print("TOKEN=" + novo_token(Contrato.objects.get(pk=gerado.pk)))
`);
  expect(saida.STATUS, "o contrato é gerado e enviado em segundo plano").toBe("enviado");
  expect(saida.TOKEN).toBeTruthy();
  return saida.TOKEN as string;
}

/**
 * O cliente abre o link numa sessão sem login, no tamanho do celular, e assina com o nome completo.
 * Sem a página `/assinar`, o teste chama as duas rotas públicas do link (consultar e assinar) de dentro do navegador.
 */
export async function assinarPeloLink(browser: Browser, info: TestInfo, token: string) {
  const contexto = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, baseURL: info.project.use.baseURL });
  const page = await contexto.newPage();
  await page.goto("/entrar");
  const resultado = await page.evaluate(
    async ({ token: t, nome }) => {
      const chamar = async (rota: string, corpo: object) => {
        const r = await fetch(`/api/publico/assinaturas/${rota}/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
        return { status: r.status, corpo: (await r.json()) as Record<string, unknown> };
      };
      const consulta = await chamar("consultar", { token: t });
      const assinatura = await chamar("assinar", { token: t, aceite: true, nome_completo: nome });
      return { consulta, assinatura };
    },
    { token, nome: CLIENTE.nome },
  );
  expect(resultado.consulta.status).toBe(200);
  expect(resultado.assinatura.status).toBe(200);
  expect(resultado.assinatura.corpo.status).toBe("assinado");
  await contexto.close();
}

// --- Caixa ---

async function buscarContaNoCaixa(page: Page, texto: string) {
  const campo = page.getByLabel("Buscar a conta a receber");
  await campo.fill(texto);
  return page.getByRole("list", { name: "Contas em aberto" });
}

/** Recebe em dinheiro a conta que a busca achar (`linha` identifica a linha pelo valor). O valor vem da API, nunca é digitado. */
export async function receberEmDinheiro(page: Page, busca: string, linha: RegExp) {
  const lista = await buscarContaNoCaixa(page, busca);
  const conta = lista.locator("li button").filter({ hasText: linha });
  await expect(conta).toBeVisible();
  await conta.click();
  await page.getByRole("radio", { name: "Dinheiro" }).check({ force: true });
  const receber = page.getByRole("button", { name: /^Receber R\$/ });
  const valor = (await receber.innerText()).replace("Receber ", "");
  await receber.click();
  await expect(page.getByText(new RegExp(`${valor.replace(/[$.]/g, "\\$&")} recebidos de ${CLIENTE.nome}`))).toBeVisible();
  await page.getByRole("button", { name: "Receber outro pagamento" }).click();
  return valor;
}

/** A caução pode não aparecer na busca (D-01 do handoff); aí o teste a recebe pelo serviço e segue, com a falha registrada. */
export function receberCaucaoPeloBackend(locacaoId: number, valorCentavos: number) {
  const saida = executarNoBackend(`
from django_tenants.utils import schema_context
from apps.plataforma.models import Empresa
from apps.financeiro.models import ContaReceber
from apps.financeiro import services
from apps.contas.models import Usuario
empresa = Empresa.objects.get(subdominio="motorapida")
with schema_context(empresa.schema_name):
    usuario = Usuario.objects.get(email="bruna@motorapida.com.br")
    conta = ContaReceber.objects.get(origem_id=${locacaoId}, tipo="caucao", status="aberta")
    services.receber(conta, usuario, forma="dinheiro", valor_centavos=${valorCentavos}, filial_id=conta.filial_id)
    print("PAGO=sim")
`);
  expect(saida.PAGO).toBe("sim");
}

export async function caixaMostra(page: Page, esperado: { entrou: string; recebimentos: string; gaveta: string; movimentos: number }) {
  await page.goto("/financeiro/caixa");
  await aquietar(page);
  const ver = (texto: string) => visivel(page.getByText(texto, { exact: true }));
  await expect(ver("Entrou hoje")).toBeVisible();
  await expect(ver(esperado.entrou)).toBeVisible();
  await expect(ver(esperado.gaveta)).toBeVisible();
  const celular = (page.viewportSize()?.width ?? 1440) < 768;
  if (celular) {
    // No celular o cartão não traz "N recebimentos": a lista de movimentos (entradas e saídas) fecha a conta.
    await expect(page.getByRole("list", { name: "Movimentos do caixa" }).locator("li")).toHaveCount(esperado.movimentos);
  } else {
    await expect(ver(esperado.recebimentos)).toBeVisible();
    await expect(ver("Dinheiro na gaveta")).toBeVisible();
  }
}

// --- Sessões extras ---

export { novaSessao };

// --- Devolução (14 out) ---

/** Abre a devolução pela ficha da locação (botão "Registrar devolução"). */
export async function abrirDevolucao(page: Page, locacaoId: number) {
  await page.goto(`/locacoes/${locacaoId}`);
  await visivel(page.getByRole("button", { name: "Registrar devolução" }).or(page.getByRole("link", { name: "Registrar devolução" }))).click();
  await expect(page).toHaveURL(new RegExp(`/locacoes/${locacaoId}/devolucao$`));
  await expect(page.getByRole("heading", { name: "Devolução" })).toBeVisible();
}

/**
 * Etapa 1 · Vistoria de chegada (DEV-08): o lado "saída" mostra o km e o combustível da vistoria de saída.
 * Km de chegada = saída + 420, tanque cheio, o risco antigo fica sem cobrança e a carenagem nova entra com foto,
 * sem "vai para oficina". Quem faz a vistoria não dá o valor da avaria: ele é dado no acerto, por quem fecha a conta.
 */
export async function vistoriaDeChegada(page: Page, locacaoId: number, opcoes: { pelaAgenda?: boolean } = {}) {
  if (opcoes.pelaAgenda) await abrirPelaAgenda(page, "devolucao", locacaoId);
  else await abrirDevolucao(page, locacaoId);
  const concluir = page.getByRole("button", { name: "Concluir vistoria" });
  await expect(concluir).toBeDisabled();

  await expect(visivel(page.getByLabel("Km na saída"))).toHaveValue(new Intl.NumberFormat("pt-BR").format(KM_DO_CADASTRO));
  await expect(visivel(page.getByText(/saiu com tanque cheio/))).toBeVisible();
  await expect(visivel(page.getByText(new RegExp(`${AVARIA_ANTIGA}\. Registrado na vistoria anterior; não será cobrado`)))).toBeVisible();

  await digitarKm(page, "Km agora", KM_DO_CADASTRO + KM_RODADOS);
  await nivelCheio(page);
  await page.getByRole("button", { name: "Tirar mais fotos" }).click();
  await enviarFotos(page);
  await marcarItens(page);
  await registrarAvaria(page, AVARIA_NOVA.descricao, false);

  await expect(concluir).toBeEnabled();
  await concluir.click();
}

/** Etapa 2 · Acerto (DEV-01, DEV-02): avaria R$ 380,00, sem combustível nem atraso, caução R$ 300,00: cobrar R$ 80,00 em 17 out. */
export async function acertarEEncerrar(page: Page, locacaoId: number) {
  await page.goto(`/locacoes/${locacaoId}/devolucao`);
  await expect(page.getByRole("heading", { name: "Devolução" })).toBeVisible();
  await visivel(page.getByRole("button", { name: /^(2 · )?Acerto$/ })).click();

  const valor = page.getByLabel(AVARIA_NOVA.descricao, { exact: false });
  await valor.fill(AVARIA_NOVA.valor);
  await valor.blur();

  const resumo = visivel(page.locator("section", { hasText: "Caução a devolver" }));
  await expect(resumo).toContainText("R$ 380,00");
  await expect(resumo).toContainText("Atraso");
  await expect(resumo).toContainText("R$ 0,00");
  await expect(resumo).toContainText("− R$ 300,00");
  await expect(resumo).toContainText("Cobrar do cliente");
  await expect(resumo).toContainText("R$ 80,00");
  await expect(resumo).toContainText("vencimento em 3 dias");

  await visivel(page.getByRole("button", { name: /^Encerrar e cobrar/ })).click();
  await expect(visivel(page.getByText(/Devolução encerrada/))).toBeVisible();
  await expect(visivel(page.getByText(/está encerrada/))).toBeVisible();
}

/** Cadastro sem as fotos: o cliente fica incompleto e a retirada não é liberada (CLI-03). */
export async function cadastrarClienteSemFotos(page: Page): Promise<number> {
  await page.goto("/clientes/novo");
  await preencherCliente(page, CLIENTE.cpf, CLIENTE.nome);
  await page.getByRole("button", { name: "Salvar cliente" }).click();
  await expect(page).toHaveURL(/\/clientes\/\d+$/);
  await expect(page.getByRole("heading", { name: CLIENTE.nome })).toBeVisible();
  return Number(/\/clientes\/(\d+)$/.exec(page.url())?.[1]);
}

/** Abre a devolução pela agenda do vistoriador (VIS-05), sem passar pela ficha da locação. */
export async function abrirPelaAgenda(page: Page, tipo: "vistoria" | "devolucao", locacaoId: number) {
  await page.goto("/vistorias");
  const item = visivel(page.locator(`a[href$="/locacoes/${locacaoId}/${tipo}"]`));
  await expect(item).toBeVisible();
  await expect(item).toContainText(CLIENTE.nome);
  await item.click();
  await expect(page).toHaveURL(new RegExp(`/locacoes/${locacaoId}/${tipo}$`));
}

/** O que o vistoriador vê no menu (USR-05): só a agenda e as avarias, sem caixa, clientes nem financeiro. */
export async function menuDoVistoriador(page: Page) {
  await page.goto("/vistorias");
  await aquietar(page);
  await expect(page.getByRole("link", { name: /Caixa|Contas a receber|Despesas|Clientes/ }).filter({ visible: true })).toHaveCount(0);
}

/** Situação do veículo na Frota (a tela lista pela busca de placa). */
export async function situacaoNaFrota(browser: Browser, info: TestInfo, placaTexto: string, situacao: string) {
  // A vendedora não abre a Frota (USR-05): quem confere é o gerente, numa sessão própria.
  const { page, contexto } = await novaSessao(browser, info);
  await entrar(page, "rodrigo");
  await page.goto("/veiculos");
  await page.getByRole("searchbox").or(page.getByPlaceholder(/placa|buscar|modelo/i)).first().fill(placaTexto);
  await expect(visivel(page.locator("tr, li, a", { hasText: placaTexto }))).toContainText(situacao);
  await contexto.close();
}

/** 14 out: sem caixa aberto a tela avisa; Bruna abre com troco de R$ 200,00. */
export async function abrirCaixaDe14Out(page: Page) {
  await page.goto("/financeiro/caixa");
  await expect(page.getByText("Abrir o caixa de hoje")).toBeVisible();
  // D-03: receber sem caixa aberto deveria mostrar "Abra o caixa do dia para receber".
  await defeitoConhecido("D-03", "sem caixa aberto a tela não diz \"Abra o caixa do dia para receber\"", async () => {
    await expect(visivel(page.getByText("Abra o caixa do dia para receber"))).toBeVisible({ timeout: 3000 });
  });
  await page.getByLabel("Troco na gaveta (R$)").fill("200,00");
  await page.getByRole("button", { name: "Abrir caixa" }).click();
  await expect(visivel(page.getByText("Aberto", { exact: true }))).toBeVisible();
}

/** A conta do acerto fica paga na ficha da locação e em Contas a receber. */
export async function contaDoAcertoPaga(page: Page, locacaoId: number, codigo: string) {
  await page.goto(`/locacoes/${locacaoId}`);
  await expect(visivel(page.getByText("Encerrada", { exact: true }))).toBeVisible();
  // A tabela de pagamentos da ficha só existe no desktop; no celular a ficha resume ("1 de 1 pagos").
  if ((page.viewportSize()?.width ?? 1440) >= 768) await expect(visivel(page.getByText(/Pago · Dinheiro/))).toBeVisible();
  await page.goto(`/financeiro/receber?busca=${codigo}`);
  await visivel(page.getByRole("button", { name: /^Pagas/ })).click();
  await expect(visivel(page.getByText("R$ 80,00"))).toBeVisible();
}
