import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { regrasDeSenha } from "@/lib/senha";
import { RegrasDeSenha } from "./RegrasDeSenha";

describe("RegrasDeSenha", () => {
  it("diz em texto se cada regra está cumprida, sem depender de cor", () => {
    const html = renderToStaticMarkup(<RegrasDeSenha regras={regrasDeSenha("curta1", "a@b.com")} />);
    expect(html).toContain("12 caracteres ou mais");
    expect(html).toContain("(pendente)");
    expect(html).toContain("(cumprida)");
  });
});
