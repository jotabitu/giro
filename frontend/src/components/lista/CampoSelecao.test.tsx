// CampoSelecao com grupos (T-417, FIN-06): as opções sem grupo ficam soltas antes dos grupos, sem <optgroup> de rótulo vazio.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CampoSelecao } from "./CampoSelecao";

const html = (opcoes: { valor: string; rotulo: string; grupo?: string }[], vazio?: string) =>
  renderToStaticMarkup(<CampoSelecao rotulo="Categoria" opcoes={opcoes} vazio={vazio} defaultValue="" />);

describe("CampoSelecao", () => {
  it("sem grupo nenhum, só opções, sem optgroup", () => {
    const h = html([
      { valor: "a", rotulo: "A" },
      { valor: "b", rotulo: "B" },
    ]);
    expect(h).not.toContain("<optgroup");
    expect(h).toMatch(/<option value="a">A<\/option><option value="b">B<\/option>/);
  });

  it("test_fin_06_opcao_sem_grupo_fica_solta_antes_dos_grupos", () => {
    const h = html(
      [
        { valor: "ipva", rotulo: "IPVA e licenciamento", grupo: "Do veículo" },
        { valor: "todas", rotulo: "Todas" },
        { valor: "fixas", rotulo: "Fixas", grupo: "Da empresa" },
        { valor: "pecas", rotulo: "Peças", grupo: "Do veículo" },
      ],
      "Escolha",
    );
    expect(h).not.toContain('label=""');
    const select = h.slice(h.indexOf("<select"), h.indexOf("</select>"));
    expect(select.replace(/<select[^>]*>/, "")).toBe(
      '<option value="" selected="">Escolha</option>' +
        '<option value="todas">Todas</option>' +
        '<optgroup label="Do veículo"><option value="ipva">IPVA e licenciamento</option><option value="pecas">Peças</option></optgroup>' +
        '<optgroup label="Da empresa"><option value="fixas">Fixas</option></optgroup>',
    );
  });
});
