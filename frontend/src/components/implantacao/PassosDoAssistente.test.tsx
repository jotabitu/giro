// T-364 · Passos Primeira filial, Tabela de preços, Modelo de contrato e Convidar equipe dentro da casca do assistente
// (docs/api/plataforma.md, "Rotas de cada passo do assistente"; IMP-04, IMP-05, IMP-07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, filiais, modelosContrato, precos, usuarios, type AndamentoDoAssistente, type Eu } from "@/lib/api";
import { definirModelosFalsos } from "@/testes/falsos/falso-modelos-contrato";
import { definirPrecosFalsos } from "@/testes/falsos/falso-precos";
import { andamentoFalso, ANDAMENTO_PROFISSIONAL } from "@/testes/falsos/falso-implantacao";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {}, replace: () => {} }) }));

import { CorpoDoPasso } from "./PassoDoAssistente";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};
const SEM_TELA = "Esta etapa ainda não está disponível aqui.";
const botaoDesligado = (h: string, rotulo: string) => new RegExp(`<button[^>]*disabled[^>]*>${rotulo}</button>`).test(h);

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

async function passo(chave: string, andamento: AndamentoDoAssistente, semMatriz = false): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["implantacao"], andamento);
  const lista = await filiais.listar();
  cache.setQueryData(["filiais-admin", "lista"], semMatriz ? { ...lista, resultados: [] } : lista);
  cache.setQueryData(["precos", "categorias", "todas"], await precos.categorias());
  const modelos = await modelosContrato.listar();
  cache.setQueryData(["contratos", "modelos"], modelos);
  const primeiro = modelos[0]!;
  cache.setQueryData(["contratos", "modelo", primeiro.id, primeiro.editado_em], await modelosContrato.obter(primeiro.id));
  cache.setQueryData(["contratos", "previa", primeiro.id, "exemplo"], await modelosContrato.previa(primeiro.id));
  cache.setQueryData(["usuarios", "convites", "assistente"], await usuarios.listar({ situacao: "convites" }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <CorpoDoPasso andamento={andamento} passo={chave} />
    </QueryClientProvider>,
  );
}

beforeEach(async () => {
  definirPrecosFalsos(null);
  definirModelosFalsos();
  await entrar("mariana@motorapida.com.br");
});

describe("nenhum passo com tela mostra o aviso de etapa indisponível", () => {
  it("imp_05_sem_aviso: filial, preços, contrato, equipe, marca, ramo; só os recebimentos (T-366) mantêm o aviso", async () => {
    for (const chave of ["filial", "precos", "contrato", "equipe"]) {
      expect(await passo(chave, ANDAMENTO_PROFISSIONAL), chave).not.toContain(SEM_TELA);
    }
    expect(await passo("recebimentos", ANDAMENTO_PROFISSIONAL)).toContain(SEM_TELA);
  });
});

describe("Primeira filial (Onboarding-Filial)", () => {
  it("imp_07_filial_sem_matriz: pergunta onde fica a loja, pede o endereço e grava a matriz", async () => {
    const h = await passo("filial", andamentoFalso(["marca"]), true);
    ordem(texto(h), ["Onde fica sua loja principal?", "Ela vira a matriz.", "Endereço", "CEP", "Rua", "Número", "Complemento", "Bairro", "Cidade", "UF", "Nome da filial", "Nome curto no seletor", "WhatsApp de atendimento", "Horário de funcionamento", "Comercial", "Estendido", "Salvar matriz", "Voltar", "Pular por agora", "Continuar"]);
    expect(h).toContain("também vai na nota fiscal");
    expect(botaoDesligado(h, "Salvar matriz")).toBe(true);
    expect(botaoDesligado(h, "Continuar")).toBe(true);
    expect(h).toContain('href="/implantacao/marca"');
    expect(h).toContain('href="/implantacao/ramo"');
  });

  it("imp_07_filial_com_matriz: mostra a matriz que já existe e libera o Continuar", async () => {
    const h = await passo("filial", andamentoFalso(["marca", "filial"]));
    const t = texto(h);
    expect(t).toContain("Matriz");
    expect(t).toContain("A matriz já está cadastrada.");
    expect(h).not.toContain("Salvar matriz");
    expect(botaoDesligado(h, "Continuar")).toBe(false);
  });

  it("a criação da matriz vai com matriz verdadeira e a API marca o passo", async () => {
    const criada = await filiais.criar({
      nome: "Loja Principal",
      nome_curto: null,
      matriz: true,
      cnpj: null,
      inscricao_estadual: null,
      inscricao_municipal: null,
      endereco: { cep: "60325000", logradouro: "Av. Bezerra de Menezes", numero: "1200", complemento: null, bairro: "São Gerardo", cidade: "Fortaleza", uf: "CE" },
      contato: { telefone: null, whatsapp: "85988001000", email: null },
      preco_litro_centavos: null,
      horario: { seg: [{ abre: "08:00", fecha: "18:00" }], ter: [], qua: [], qui: [], sex: [], sab: [], dom: [] },
    });
    expect(criada.matriz).toBe(true);
  });
});

describe("Tabela de preços (Onboarding-Precos)", () => {
  it("imp_07_precos: reaproveita o painel de categorias e preço, com Nova categoria no cabeçalho", async () => {
    const h = await passo("precos", andamentoFalso(["marca", "filial", "ramo"]));
    ordem(texto(h), ["Quanto você cobra?", "Nova categoria", "Para continuar, crie ao menos uma categoria com preço.", "Por categoria", "Urbana 110–125", "R$ 44,90", "Street 150–160", "Voltar", "Pular por agora", "Continuar"]);
    expect(botaoDesligado(h, "Continuar")).toBe(true);
    expect(h).toContain('href="/implantacao/ramo"');
    expect(h).toContain('href="/implantacao/contrato"');
  });

  it("com o passo feito pela API, o Continuar vale e o texto de ajuda some", async () => {
    const h = await passo("precos", andamentoFalso(["marca", "filial", "ramo", "precos"]));
    expect(botaoDesligado(h, "Continuar")).toBe(false);
    expect(h).not.toContain("Para continuar, crie ao menos uma categoria");
  });
});

describe("Modelo de contrato (Onboarding-Contrato)", () => {
  it("imp_04_contrato: reaproveita a lista de modelos, com prévia, edição e publicar", async () => {
    const h = await passo("contrato", andamentoFalso(["marca", "filial", "ramo", "precos"]));
    ordem(texto(h), ["Seu contrato de locação", "Novo modelo", "Para continuar, publique ao menos um modelo de locação.", "Locação semanal", "Publicado · v3", "Ver com dados reais", "Editar texto", "Arquivar", "Campos automáticos", "Peça ao seu advogado", "Voltar", "Pular por agora", "Continuar"]);
    expect(botaoDesligado(h, "Continuar")).toBe(true);
    expect(h).toContain('href="/implantacao/precos"');
    // No Profissional o passo seguinte é o dos recebimentos; ele continua sem tela até a T-366.
    expect(h).toContain('href="/implantacao/recebimentos"');
  });

  it("no Essencial, depois do contrato vem importar (recebimentos não existe no plano)", async () => {
    const h = await passo("contrato", andamentoFalso(["marca", "filial", "ramo", "precos", "contrato"], ["recebimentos"]));
    expect(h).toContain('href="/implantacao/importar"');
    expect(h).not.toContain('href="/implantacao/recebimentos"');
    expect(botaoDesligado(h, "Continuar")).toBe(false);
  });
});

describe("Convidar equipe (Onboarding-Equipe)", () => {
  it("usr_01_equipe: convites enviados, o que cada perfil vê, Convidar depois e Concluir", async () => {
    const h = await passo("equipe", andamentoFalso(["marca", "filial", "ramo", "precos", "contrato", "importar"]));
    const t = texto(h);
    ordem(t, ["Quem trabalha com você?", "Convidar pessoa", "Convite pendente", "O que cada perfil vê", "Gerente:", "Vendedor:", "Vistoriador:", "Financeiro:", "Voltar", "Convidar depois", "Concluir"]);
    expect(h).toContain('href="/inicio"');
    expect(h).toContain('href="/implantacao/importar"');
    expect(botaoDesligado(h, "Concluir")).toBe(true);
  });

  it("depois do primeiro convite a API marca o passo e o Concluir vale", async () => {
    const h = await passo("equipe", andamentoFalso(["marca", "filial", "ramo", "precos", "contrato", "importar", "equipe"]));
    expect(botaoDesligado(h, "Concluir")).toBe(false);
  });
});
