// Controle do suporte (T-372) contra docs/telas/html/Admin-Suporte-*.dc.html e docs/api/contas.md, "Controle do administrador" (PLT-07).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { configuracoes, suporte, type ControleDoSuporte as Controle, type Eu } from "@/lib/api";
import { CARTOES } from "@/lib/configuracoes";
import { reiniciarSuporteFalso } from "@/testes/falsos/falso-suporte";

const sessao = vi.hoisted(() => ({ administracao: true }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: { pode: { administracao: sessao.administracao } } as unknown as Eu, sair: async () => {} }) }));

import { ControleDoSuporte } from "./ControleDoSuporte";

async function tela(dados?: Controle): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["suporte", "todos"], dados ?? (await suporte.listar("todos")));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ControleDoSuporte />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  reiniciarSuporteFalso();
  sessao.administracao = true;
});

describe("Controle do suporte", () => {
  it("liberado: rótulo da API, contagens, lista do mais novo ao mais antigo e Revogar só no ativo", async () => {
    const h = await tela();
    expect(h).toContain("Acesso do suporte liberado");
    expect(h).toContain(">Bloquear suporte Giro</button>");
    expect(h).toContain("Revoga na hora qualquer acesso ativo");
    expect(h).not.toContain("Liberar suporte Giro");
    for (const t of ["Todos", "Ativos", "Encerrados"]) expect(h).toContain(t);
    expect(h.indexOf("Chamado #1042")).toBeLessThan(h.indexOf("Chamado #1018"));
    expect(h).toContain("Ativo agora");
    expect(h).toContain("Só ver");
    expect(h).toContain("Ver e editar");
    expect(h).toContain("Revogado");
    expect(h.match(/>Revogar acesso<\/button>/g)).toHaveLength(1);
    expect(h).not.toMatch(/@|e-mail do operador/i);
  });

  it("bloqueado: oferece Liberar suporte Giro no lugar de Bloquear", async () => {
    await suporte.bloquear();
    const h = await tela();
    expect(h).toContain("Acesso do suporte bloqueado");
    expect(h).toContain("Liberar suporte Giro");
    expect(h).not.toContain(">Bloquear suporte Giro</button>");
    expect(h).not.toContain("</span><span class=\"text-caption text-ink-muted\">Revoga na hora");
    expect(h).not.toContain(">Revogar acesso</button>");
  });

  it("filtro e contagens vêm da API: as contagens não dependem do filtro", async () => {
    const ativos = await suporte.listar("ativos");
    const encerrados = await suporte.listar("encerrados");
    expect(ativos.acessos.map((a) => a.id)).toEqual([31]);
    expect(encerrados.acessos.map((a) => a.status)).toEqual(["encerrado", "revogado"]);
    expect(ativos.contagens).toEqual({ todos: 3, ativos: 1, encerrados: 2 });
    expect(encerrados.contagens).toEqual(ativos.contagens);
  });

  it("revogar devolve o item revogado e bloquear revoga os ativos", async () => {
    const r = await suporte.revogar(31);
    expect(r.status).toBe("revogado");
    expect(r.acoes.revogar).toBe(false);
    reiniciarSuporteFalso();
    await suporte.bloquear();
    const d = await suporte.listar("ativos");
    expect(d.contagens.ativos).toBe(0);
    expect((await suporte.liberar()).bloqueado).toBe(false);
  });

  it("lista vazia no filtro mostra o texto de vazio", async () => {
    const base = await suporte.listar("todos");
    const h = await tela({ ...base, acessos: [] });
    expect(h).toContain("Nenhum acesso do suporte neste filtro.");
  });

  it("quem não é administrador vê o aviso e nenhuma ação", async () => {
    sessao.administracao = false;
    const h = await tela();
    expect(h).toContain("Só o administrador acessa o controle do suporte.");
    expect(h).not.toContain("Bloquear suporte Giro");
  });

  it("o cartão `suporte` de Configurações abre /admin/suporte; a API não manda o cartão ao token de suporte", async () => {
    expect(CARTOES.suporte.href).toBe("/admin/suporte");
    const resumo = await configuracoes.resumo();
    expect(resumo.cartoes.some((c) => c.chave === "suporte")).toBe(false);
  });
});
