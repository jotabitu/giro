// Casca do assistente de implantação (T-335) contra docs/telas/html/Onboarding-*.dc.html e docs/api/plataforma.md (GET /api/implantacao/, IMP-05).
// Os passos, a ordem e o "Passo N de M" vêm da API; a tela não conta nada.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { contas, type AndamentoDoAssistente, type Eu } from "@/lib/api";
import { destinoAntesDe, destinoDepoisDe, passoTemTela, rotaDoPasso, vizinhos } from "@/lib/implantacao";
import { MARCA_FALSA } from "@/testes/falsos/falso";
import { andamentoFalso, ANDAMENTO_PROFISSIONAL } from "@/testes/falsos/falso-implantacao";
import { RAMO_ESSENCIAL, RAMO_PROFISSIONAL } from "@/testes/falsos/falso-ramo";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {}, replace: () => {} }) }));

import { CascaDoAssistente } from "./CascaDoAssistente";
import { CorpoDoPasso } from "./PassoDoAssistente";
import { PassoRamo } from "./PassoRamo";

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

function comCache(tela: React.ReactNode, andamento: AndamentoDoAssistente | null = ANDAMENTO_PROFISSIONAL): string {
  const cache = new QueryClient();
  cache.setQueryData(["marca"], MARCA_FALSA);
  if (andamento) cache.setQueryData(["implantacao"], andamento);
  cache.setQueryData(["ramo"], RAMO_PROFISSIONAL);
  return renderToStaticMarkup(<QueryClientProvider client={cache}>{tela}</QueryClientProvider>);
}

const ESSENCIAL = andamentoFalso(["marca", "filial"], ["recebimentos"]);

describe("navegação entre passos (lib/implantacao)", () => {
  it("segue a ordem que a API mandou: continuar vai ao seguinte e voltar ao anterior", () => {
    expect(vizinhos(ANDAMENTO_PROFISSIONAL, "ramo").anterior?.passo).toBe("filial");
    expect(destinoDepoisDe(ANDAMENTO_PROFISSIONAL, "ramo")).toBe("/implantacao/precos");
    expect(destinoAntesDe(ANDAMENTO_PROFISSIONAL, "ramo")).toBe("/implantacao/filial");
  });

  it("no Essencial o passo recebimentos não existe: depois do contrato vem importar", () => {
    expect(destinoDepoisDe(ESSENCIAL, "contrato")).toBe("/implantacao/importar");
    expect(ESSENCIAL.total).toBe(7);
  });

  it("nas pontas volta ao início; passo desconhecido não tem vizinhos", () => {
    expect(destinoAntesDe(ANDAMENTO_PROFISSIONAL, "marca")).toBe("/inicio");
    expect(destinoDepoisDe(ANDAMENTO_PROFISSIONAL, "equipe")).toBe("/inicio");
    expect(vizinhos(ANDAMENTO_PROFISSIONAL, "xyz")).toEqual({ anterior: null, seguinte: null });
  });

  it("todos os passos têm tela, menos recebimentos (T-366); a rota é a mesma da chave", () => {
    expect(["marca", "ramo", "importar", "filial", "precos", "contrato", "recebimentos", "equipe"].filter((p) => !passoTemTela(p))).toEqual(["recebimentos"]);
    expect(rotaDoPasso("ramo")).toBe("/implantacao/ramo");
  });
});

describe("CascaDoAssistente", () => {
  it("desktop: marca da empresa, Passo 3 de 8 e os oito passos na ordem da API", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CascaDoAssistente passo="ramo">{() => <p>corpo</p>}</CascaDoAssistente>);
    for (const t of ["Moto Rápida", "Configuração inicial", "Salvar e sair", "Passo 3 de 8", "Empresa e marca", "Primeira filial", "O que a empresa faz", "Tabela de preços", "Modelo de contrato", "Recebimentos", "Importar dados", "Convidar equipe", "corpo"]) expect(h).toContain(t);
    expect(h.indexOf("Empresa e marca")).toBeLessThan(h.indexOf("Convidar equipe"));
    expect(h).toContain('aria-current="step"');
    expect(h).toContain("Tabela de preços a seguir");
  });

  it("os passos com tela viram link; o atual e os recebimentos (sem tela) não", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CascaDoAssistente passo="ramo">{() => null}</CascaDoAssistente>);
    expect(h).toContain('href="/implantacao/marca"');
    expect(h).toContain('href="/implantacao/importar"');
    expect(h).not.toContain('href="/implantacao/ramo"');
    expect(h).toContain('href="/implantacao/contrato"');
    expect(h).toContain('href="/implantacao/equipe"');
    expect(h).not.toContain('href="/implantacao/recebimentos"');
  });

  it("Essencial: o número vem da API (importar é o 6 de 7)", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CascaDoAssistente passo="importar">{() => null}</CascaDoAssistente>, ESSENCIAL);
    expect(h).toContain("Passo 6 de 7");
    expect(h).not.toContain("Recebimentos");
  });

  it("passo fora do plano: avisa e leva ao próximo da API", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CascaDoAssistente passo="recebimentos">{() => <p>corpo</p>}</CascaDoAssistente>, ESSENCIAL);
    expect(h).toContain("Este passo não faz parte da configuração inicial do seu plano.");
    expect(ESSENCIAL.proximo).toBe("ramo");
    expect(h).toContain('href="/implantacao/ramo"');
    expect(h).not.toContain("corpo");
  });

  it("sem os dados da API mostra o carregando, sem passos inventados", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CascaDoAssistente passo="ramo">{() => <p>corpo</p>}</CascaDoAssistente>, null);
    expect(h).toContain("Carregando os passos…");
    expect(h).not.toContain("Passo ");
  });

  it("quem não é administrador não vê a configuração inicial", async () => {
    await entrar("bruna@motorapida.com.br");
    const h = comCache(<CascaDoAssistente passo="ramo">{() => <p>corpo</p>}</CascaDoAssistente>);
    expect(h).toContain("Só o administrador faz a configuração inicial.");
    expect(h).not.toContain("corpo");
  });
});

describe("passos ligados na casca", () => {
  it("Marca: o PassoMarca da T-154, com a marca lida da API", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CorpoDoPasso andamento={ANDAMENTO_PROFISSIONAL} passo="marca" />);
    expect(h).toContain("Sua empresa e sua marca");
    expect(h).toContain("Pular por agora");
    expect(h).toContain("Continuar");
  });

  it("Ramo: pergunta com o nome da empresa, opções e módulos da API, Voltar e Continuar", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CorpoDoPasso andamento={ANDAMENTO_PROFISSIONAL} passo="ramo" />);
    expect(h).toContain("O que a Moto Rápida faz?");
    for (const t of ["Locação", "Venda de veículos", "Motos", "Carros", "6 módulos no seu plano", "Dá para mudar depois"]) expect(h).toContain(t);
    expect(h).toContain('href="/implantacao/filial"');
    expect(h).toContain(">Continuar<");
  });

  it("Ramo no Essencial: Vendas traz o aviso da API e o 'Locação' fica travado", () => {
    const h = comCache(<PassoRamo guardado={RAMO_ESSENCIAL} nomeDaEmpresa="Moto Rápida" voltarPara="/implantacao/filial" aoContinuar={() => {}} />);
    expect(h).toContain("Vendas faz parte do plano Profissional.");
    expect(h).toContain('aria-disabled="true"');
    expect(h).toContain("3 módulos no seu plano");
  });

  it("recebimentos, sem tela até a T-366: mostra o rótulo da API e só navega (Voltar e Pular por agora)", async () => {
    await entrar("mariana@motorapida.com.br");
    const h = comCache(<CorpoDoPasso andamento={ANDAMENTO_PROFISSIONAL} passo="recebimentos" />);
    expect(h).toContain("Recebimentos");
    expect(h).toContain("Esta etapa ainda não está disponível aqui.");
    expect(h).toContain('href="/implantacao/contrato"');
    expect(h).toContain('href="/implantacao/importar"');
  });
});
