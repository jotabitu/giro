// Administração › Filiais (T-168) contra docs/telas/html/Filiais-*.dc.html e Filial-*.dc.html (FIL-01 a FIL-06, PLT-03).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contas, filiais, type Eu } from "@/lib/api";
import { corpoDaFilial, filialCompleta, horarioDaApi, horarioDoFormulario, horarioPedeCuidado, mascaraTelefone, valoresDaFilial, VALORES_INICIAIS_DA_FILIAL } from "@/lib/filiais";
import { reiniciarFiliaisAdminFalso } from "@/testes/falsos/falso-filiais-admin";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("@/lib/filial-escolhida", () => ({ useFilial: () => null }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/admin/filiais", useSearchParams: () => new URLSearchParams() }));

import { FormularioDaFilial } from "./FormularioDaFilial";
import { ListaFiliais } from "./ListaFiliais";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

async function lista(): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["filiais-admin", "lista"], await filiais.listar());
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaFiliais />
    </QueryClientProvider>,
  );
}

async function formulario(id?: number): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["filiais-admin", "lista"], await filiais.listar());
  if (id) {
    cache.setQueryData(["filiais-admin", "detalhe", id], await filiais.obter(id));
    cache.setQueryData(["filiais-admin", "feriados", id, 2026], await filiais.feriados(id, 2026));
  }
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <FormularioDaFilial id={id} />
    </QueryClientProvider>,
  );
}

const CORPO = {
  nome: "Filial Messejana",
  matriz: false,
  endereco: { cep: "60840280", logradouro: "Av. Frei Cirilo", numero: "3120", complemento: null, bairro: "Messejana", cidade: "Fortaleza", uf: "CE" },
  horario: horarioDaApi(horarioDoFormulario({ seg: [{ abre: "08:00", fecha: "18:00" }], ter: [], qua: [], qui: [], sex: [], sab: [{ abre: "08:00", fecha: "12:00" }], dom: [] })),
};

beforeEach(() => reiniciarFiliaisAdminFalso());

describe("lista de filiais (Filiais)", () => {
  it("título, plano e a filial Centro com indicadores, gerente, horário e CNPJ", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await lista());
    for (const trecho of ["Administração", "Filiais", "1 de 3 filiais do plano Profissional", "Filial Centro", "Matriz", "Ativa", "Av. Bezerra de Menezes, 1200 · Fortaleza, CE", "86|veículos", "42|locações ativas", "5|usuários", "71%|ocupação", "Gerente|Rodrigo Pinheiro", "Funcionamento|seg a sex 8h–18h · sáb 8h–12h", "12.345.678/0001-95", "Editar dados", "Ver painel da filial", "Nova filial"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).toContain("Seu plano permite mais 2 filiais. Cada uma tem frota, caixa e equipe próprios.");
    expect(t).toContain("Como funciona com mais de uma filial");
    expect(t).toContain("separados por filial");
    expect(t).toContain("Filiais do plano|1 de 3");
  });

  it("só o administrador acessa (USR-05)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await lista())).toContain("Só o administrador acessa Filiais.");
  });

  it("plano cheio troca Nova filial por Mudar de plano", async () => {
    await entrar("mariana@motorapida.com.br");
    await filiais.criar({ ...CORPO, nome: "A" });
    await filiais.criar({ ...CORPO, nome: "B" });
    const t = texto(await lista());
    expect(t).toContain("3 de 3 filiais do plano Profissional");
    expect(t).toContain("Mudar de plano");
    expect(t).not.toContain("Nova filial");
    expect(t).toContain("Seu plano chegou ao limite de filiais.");
  });

  it("indicador de app que não existe vem null e sai como traço", async () => {
    await entrar("mariana@motorapida.com.br");
    await filiais.criar({ ...CORPO, nome: "Filial Messejana" });
    expect(texto(await lista())).toContain("—|veículos");
  });
});

describe("nova filial (Filial)", () => {
  it("seções, campos e o aside da referência", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await formulario();
    const t = texto(html);
    for (const trecho of ["Nova filial", "Cancelar", "Salvar filial", "Identificação", "Nome da filial", "Tipo", "CNPJ", "Inscrição estadual", "Inscrição municipal", "Endereço", "CEP", "Rua", "Número", "Complemento", "Bairro", "Cidade", "UF", "Contato e funcionamento", "Telefone", "WhatsApp de atendimento", "E-mail", "Segunda a sexta", "Sábado", "Domingo", "Fechado", "Operação", "Gerente responsável", "Filiais da empresa", "Filial Centro", "Plano Profissional", "O que é de cada filial"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).toContain("Ao salvar, são 2 de 3 filiais.");
    expect(html).toContain("Nenhum gerente ligado ainda");
    expect(t).toContain("depois de salvar a filial");
  });

  it("editar traz os dados, o tipo e os feriados confirmados", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await formulario(1);
    const t = texto(html);
    expect(t).toContain("Filial Centro");
    expect(html).toContain("Rodrigo Pinheiro");
    expect(t).toContain("12 out · Nossa Senhora Aparecida");
    expect(t).toContain("Adicionar feriado");
    expect(html).toContain('value="12.345.678/0001-95"');
    expect(html).toContain('value="Av. Bezerra de Menezes"');
  });

  it("só o administrador acessa", async () => {
    await entrar("rodrigo@motorapida.com.br");
    expect(texto(await formulario())).toContain("Só o administrador acessa Filiais.");
  });
});

describe("regras na API falsa (filiais.md)", () => {
  it("criar: nome repetido e limite do plano", async () => {
    await expect(filiais.criar({ ...CORPO, nome: "filial centro" })).rejects.toMatchObject({ codigo: "filial_nome_em_uso" });
    await filiais.criar({ ...CORPO, nome: "A" });
    await filiais.criar({ ...CORPO, nome: "B" });
    await expect(filiais.criar({ ...CORPO, nome: "C" })).rejects.toMatchObject({ codigo: "PLT-03" });
  });

  it("matriz nova tira a anterior", async () => {
    const nova = await filiais.criar({ ...CORPO, nome: "A" });
    await filiais.tornarMatriz(nova.id);
    const l = await filiais.listar();
    expect(l.resultados.filter((f) => f.matriz).map((f) => f.nome)).toEqual(["A"]);
  });

  it("desativar a matriz traz todos os impedimentos de uma vez (FIL-06)", async () => {
    await expect(filiais.desativar(1, "Fechou")).rejects.toMatchObject({ codigo: "FIL-06", detalhes: { matriz: true, ultima_filial: true, operacao: { veiculos: 86, locacoes: 42, caixas: 0 } } });
  });

  it("desativar filial sem operação libera a vaga e reativar volta", async () => {
    const nova = await filiais.criar({ ...CORPO, nome: "A" });
    await filiais.desativar(nova.id, "Fechou");
    expect((await filiais.listar()).plano.usado).toBe(1);
    expect((await filiais.reativar(nova.id, "Voltou")).ativo).toBe(true);
  });

  it("feriados: sugestão confirmada vira feriado e data repetida é ignorada", async () => {
    const antes = await filiais.sugestoesDeFeriados(1, 2026);
    expect(antes.find((s) => s.nome === "Finados")?.ja_cadastrado).toBe(false);
    await filiais.confirmarFeriados(1, [{ data: "2026-11-02", nome: "Finados", origem: "nacional" }]);
    await filiais.confirmarFeriados(1, [{ data: "2026-11-02", nome: "Finados", origem: "nacional" }]);
    expect((await filiais.feriados(1, 2026)).map((f) => f.nome)).toEqual(["Nossa Senhora Aparecida", "Finados"]);
  });

  it("CEP: preenche o endereço, e CEP desconhecido pede o preenchimento à mão", async () => {
    expect((await filiais.cep("60840280")).bairro).toBe("Messejana");
    await expect(filiais.cep("11111111")).rejects.toMatchObject({ codigo: "cep_nao_encontrado" });
  });
});

describe("apoio do formulário", () => {
  it("corpo: CEP e telefones só com dígitos, vazios viram null e os sete dias vão juntos", () => {
    const corpo = corpoDaFilial({ ...VALORES_INICIAIS_DA_FILIAL, nome: " Filial Messejana ", cnpj: "12.345.678/0003-57", cep: "60840-280", logradouro: "Av. Frei Cirilo", numero: "3120", bairro: "Messejana", cidade: "Fortaleza", whatsapp: "(85) 98800-0000", email: "Messejana@MotoRapida.com.br" });
    expect(corpo).toMatchObject({ nome: "Filial Messejana", cnpj: "12345678000357", inscricao_estadual: null, endereco: { cep: "60840280", complemento: null }, contato: { telefone: null, whatsapp: "85988000000", email: "messejana@motorapida.com.br" } });
    expect(Object.keys(corpo.horario)).toEqual(["seg", "ter", "qua", "qui", "sex", "sab", "dom"]);
    expect(corpo.horario.dom).toEqual([]);
    expect(corpo.horario.qua).toEqual([{ abre: "08:00", fecha: "18:00" }]);
  });

  it("obrigatórios: nome e endereço (menos complemento)", () => {
    expect(filialCompleta(VALORES_INICIAIS_DA_FILIAL)).toBe(false);
    expect(filialCompleta({ ...VALORES_INICIAIS_DA_FILIAL, nome: "A", cep: "60840280", logradouro: "R", numero: "1", bairro: "B", cidade: "C" })).toBe(true);
  });

  it("horário: dias úteis diferentes ou dois intervalos pedem cuidado ao editar", async () => {
    const f = await filiais.obter(1);
    expect(horarioPedeCuidado(f.horario)).toBe(false);
    expect(horarioPedeCuidado({ ...f.horario, qua: [{ abre: "09:00", fecha: "17:00" }] })).toBe(true);
    expect(horarioPedeCuidado({ ...f.horario, seg: [{ abre: "08:00", fecha: "12:00" }, { abre: "14:00", fecha: "18:00" }] })).toBe(true);
    expect(valoresDaFilial(f).horario.semana).toEqual({ fechado: false, abre: "08:00", fecha: "18:00" });
  });

  it("máscara de telefone fixo e celular", () => {
    expect(mascaraTelefone("8532740000")).toBe("(85) 3274-0000");
    expect(mascaraTelefone("85988000000")).toBe("(85) 98800-0000");
  });
});
