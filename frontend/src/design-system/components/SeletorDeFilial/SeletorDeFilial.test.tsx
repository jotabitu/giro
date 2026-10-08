import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Dialogo } from "../Dialogo/Dialogo";
import { Gaveta } from "../Gaveta/Gaveta";
import { KpiGrid, KpiTile } from "../KpiTile/KpiTile";
import { Sidebar } from "../Sidebar/Sidebar";
import { SeletorDeFilial } from "./SeletorDeFilial";
import { deveMostrar, destinoNaLista, itemAtivo, montarItens, TODAS } from "./logica";

const filiais = [
  { id: "centro", nome: "Filial Centro", cidade: "Fortaleza, CE" },
  { id: "aldeota", nome: "Filial Aldeota", cidade: "Fortaleza, CE" },
];

describe("lógica do seletor de filial", () => {
  it("administrador ganha Todas as filiais no topo, com a contagem", () => {
    const itens = montarItens(filiais, true);
    expect(itens.map((i) => i.id)).toEqual([TODAS, "centro", "aldeota"]);
    expect(itens[0]?.detalhe).toBe("2 filiais");
  });

  it("sem permissão, só as filiais da pessoa (USR-07)", () => {
    expect(montarItens(filiais, false).map((i) => i.id)).toEqual(["centro", "aldeota"]);
  });

  it("uma filial só e sem Todas: o seletor esconde", () => {
    expect(deveMostrar(filiais.slice(0, 1), false)).toBe(false);
    expect(deveMostrar(filiais.slice(0, 1), true)).toBe(true);
    expect(deveMostrar(filiais, false)).toBe(true);
  });

  it("item ativo desconhecido cai no primeiro", () => {
    expect(itemAtivo(montarItens(filiais, false), "xyz")?.id).toBe("centro");
    expect(itemAtivo(montarItens(filiais, true), TODAS)?.nome).toBe("Todas as filiais");
  });

  it("setas, Home e End não dão a volta", () => {
    expect(destinoNaLista("ArrowDown", 0, 3)).toBe(1);
    expect(destinoNaLista("ArrowDown", 2, 3)).toBe(2);
    expect(destinoNaLista("ArrowUp", 0, 3)).toBe(0);
    expect(destinoNaLista("ArrowUp", 2, 3)).toBe(1);
    expect(destinoNaLista("Home", 2, 3)).toBe(0);
    expect(destinoNaLista("End", 0, 3)).toBe(2);
    expect(destinoNaLista("a", 0, 3)).toBeNull();
  });
});

describe("SeletorDeFilial (marcação)", () => {
  it("mostra a filial ativa num botão que abre uma lista", () => {
    const html = renderToStaticMarkup(<SeletorDeFilial filiais={filiais} valor="aldeota" aoMudar={() => {}} />);
    expect(html).toContain("Filial Aldeota");
    expect(html).toContain('aria-haspopup="listbox"');
    expect(html).toContain('aria-expanded="false"');
    expect(html).not.toContain('role="listbox"');
  });

  it("não renderiza nada com uma filial só", () => {
    expect(renderToStaticMarkup(<SeletorDeFilial filiais={filiais.slice(0, 1)} valor="centro" aoMudar={() => {}} />)).toBe("");
  });

  it("a Sidebar usa o seletor no lugar da filial fixa", () => {
    const html = renderToStaticMarkup(
      <Sidebar
        marca={{ nome: "Moto Rápida" }}
        filial={{ nome: "Fixa", cidade: "X" }}
        seletorDeFilial={<SeletorDeFilial filiais={filiais} valor="centro" aoMudar={() => {}} />}
        grupos={[]}
      />,
    );
    expect(html).toContain("wl-switcher--botao");
    expect(html).not.toContain("Fixa");
  });
});

describe("Dialogo e Gaveta (marcação)", () => {
  it("é um dialog nativo nomeado pelo título; fechado, não renderiza o conteúdo", () => {
    const html = renderToStaticMarkup(
      <Dialogo aberto={false} aoFechar={() => {}} titulo="Encerrar a sessão?" descricao="Você precisará entrar de novo.">
        <span>CONTEUDO</span>
      </Dialogo>,
    );
    expect(html).toMatch(/^<dialog /);
    expect(html).toMatch(/aria-labelledby="[^"]+-titulo"/);
    expect(html).toMatch(/aria-describedby="[^"]+-descricao"/);
    expect(html).toContain("Encerrar a sessão?");
    expect(html).toContain('aria-label="Fechar"');
    expect(html).not.toContain("CONTEUDO");
  });

  it("aberto, mostra conteúdo e ações", () => {
    const html = renderToStaticMarkup(
      <Dialogo aberto aoFechar={() => {}} titulo="T" acoes={<button>OK</button>}>
        <span>CONTEUDO</span>
      </Dialogo>,
    );
    expect(html).toContain("CONTEUDO");
    expect(html).toContain("wl-modal__acoes");
  });

  it("Gaveta escolhe o lado pela classe", () => {
    for (const lado of ["esquerda", "direita", "baixo"] as const) {
      expect(renderToStaticMarkup(<Gaveta aberto={false} aoFechar={() => {}} titulo="Menu" lado={lado} />)).toContain(`wl-gaveta--${lado}`);
    }
  });
});

describe("KpiTile com valor longo", () => {
  it("passa o tamanho do texto ao CSS para o número encolher", () => {
    const html = renderToStaticMarkup(
      <KpiGrid>
        <KpiTile rotulo="Receita do mês" valor="R$ 1.284.350,00" />
        <KpiTile rotulo="Ocupação" valor="71%" />
      </KpiGrid>,
    );
    expect(html).toContain("--chars:15");
    expect(html).toContain("--chars:3");
    expect(html).toContain("R$ 1.284.350,00");
  });
});
