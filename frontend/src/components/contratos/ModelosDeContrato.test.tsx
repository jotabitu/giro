// T-363 · Modelos de contrato (IMP-04, S-09, LOC-15; docs/api/contratos.md).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, modelosContrato, ErroApi, type Eu } from "@/lib/api";
import { definirModelosFalsos } from "@/testes/falsos/falso-modelos-contrato";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { DialogoDoModelo } from "./DialogoDoModelo";
import { TelaDeModelosDeContrato } from "./TelaDeModelosDeContrato";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

async function pagina(): Promise<string> {
  const cache = new QueryClient();
  const lista = await modelosContrato.listar();
  cache.setQueryData(["contratos", "modelos"], lista);
  const primeiro = lista[0]!;
  cache.setQueryData(["contratos", "modelo", primeiro.id, primeiro.editado_em], await modelosContrato.obter(primeiro.id));
  cache.setQueryData(["contratos", "previa", primeiro.id, "exemplo"], await modelosContrato.previa(primeiro.id));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <TelaDeModelosDeContrato />
    </QueryClientProvider>,
  );
}

const falha = async (p: Promise<unknown>) => {
  try {
    await p;
  } catch (e) {
    if (e instanceof ErroApi) return e;
  }
  throw new Error("esperava ErroApi");
};

beforeEach(() => definirModelosFalsos());

describe("Modelos de contrato (/admin/contratos)", () => {
  it("imp_04_lista: o administrador vê a lista, o modelo em uso e as ações", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    ordem(t, ["Administração", "Modelos de contrato", "Novo modelo"]);
    ordem(t, ["Locação semanal", "usado em 38 locações", "Publicado · v3", "Compra e venda parcelada", "usado em 3 vendas", "Publicado · v1"]);
    ordem(t, ["Locação semanal", "Ver com dados reais", "Editar texto", "Arquivar", "Campos automáticos", "empresa.nome", "cliente.nome", "Versão 3 está em uso."]);
    expect(t).not.toContain("Publicar versão");
    expect(t).toContain("Versão 1");
  });

  it("quem não é administrador não vê a tela", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await pagina())).toContain("Só o administrador mexe nos modelos de contrato.");
  });

  it("s_09_dialogo_de_edicao: texto, campos automáticos para inserir e rascunho", async () => {
    const m = await modelosContrato.obter(10);
    const cache = new QueryClient();
    cache.setQueryData(["contratos", "marcadores"], await modelosContrato.marcadores());
    const html = renderToStaticMarkup(
      <QueryClientProvider client={cache}>
        <DialogoDoModelo modelo={m} aoFechar={() => {}} aoConcluir={() => {}} />
      </QueryClientProvider>,
    );
    ordem(texto(html), ["Editar Locação semanal", "Nome do modelo", "Texto do contrato", "Campos automáticos", "cliente.cpf", "Cancelar", "Salvar rascunho"]);
    expect(html).toContain("Inserir Nome do cliente");
  });
});

describe("Contrato dos modelos (IMP-04, S-09, LOC-15)", () => {
  it("s_09_marcador_invalido: texto com campo fora da lista volta 400 no campo texto", async () => {
    const e = await falha(modelosContrato.alterar(10, { texto: "<p>{{cliente.salario}}</p>" }));
    expect([e.status, e.codigo]).toEqual([400, "marcador_invalido"]);
    expect(e.campos?.texto).toContain("{{cliente.salario}}");
    expect((await falha(modelosContrato.criar({ nome: "Ruim", finalidade: "locacao", texto: "{{x.y}}" }))).codigo).toBe("marcador_invalido");
  });

  it("loc_15_editar_publicado: vira rascunho da versão seguinte e a publicada não muda", async () => {
    const editado = await modelosContrato.alterar(10, { texto: "<p>Novo texto de {{cliente.nome}}</p>" });
    expect(editado).toMatchObject({ tem_rascunho: true, status: "publicado", versao_publicada: 3 });
    const publicado = await modelosContrato.publicar(10);
    expect(publicado).toMatchObject({ tem_rascunho: false, versao_publicada: 4 });
    expect(publicado.versoes[0]).toMatchObject({ versao: 4 });
  });

  it("imp_04_novo_a_partir_do_pronto: nasce rascunho, publica na versão 1 e a prévia troca os marcadores", async () => {
    const prontos = await modelosContrato.prontos();
    expect(prontos.length).toBeGreaterThan(0);
    const novo = await modelosContrato.criar({ nome: "Diária de moto", finalidade: "locacao", a_partir_de: "locacao_diaria_moto" });
    expect(novo).toMatchObject({ status: "rascunho", versao_publicada: null, tem_rascunho: true });
    expect(novo.marcadores_usados).toContain("cliente.nome");
    const html = await modelosContrato.previa(novo.id);
    expect(html).toContain("Lucas Ferreira");
    expect(html).not.toContain("{{");
    expect(await modelosContrato.publicar(novo.id)).toMatchObject({ status: "publicado", versao_publicada: 1 });
  });

  it("imp_04_ultimo_modelo_de_locacao: arquivar o único publicado volta 422 IMP-04; o de venda arquiva", async () => {
    const e = await falha(modelosContrato.arquivar(10));
    expect([e.status, e.codigo]).toEqual([422, "IMP-04"]);
    expect((await modelosContrato.arquivar(11)).arquivado).toBe(true);
    const outro = await modelosContrato.criar({ nome: "Outro", finalidade: "locacao", a_partir_de: "locacao_semanal_carro" });
    await modelosContrato.publicar(outro.id);
    expect((await modelosContrato.arquivar(10)).arquivado).toBe(true);
  });
});
