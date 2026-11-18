import { describe, expect, it } from "vitest";
import { mostraLanding } from "./host-landing";

describe("host da landing (T-489)", () => {
  it.each(["giro.ceo", "www.giro.ceo", "WWW.Giro.ceo", "giro.ceo:443", "localhost:3000", "127.0.0.1:3000"])(
    "%s mostra a landing em / com DOMINIO_BASE=giro.ceo",
    (host) => expect(mostraLanding(host, "giro.ceo")).toBe(true),
  );

  it.each(["motorapida.giro.ceo", "admin.giro.ceo", "motorapida.localhost:3000", "homolog.giro.ceo", "giro.ceo.exemplo.com", "", null])(
    "%s continua indo para /entrar com DOMINIO_BASE=giro.ceo",
    (host) => expect(mostraLanding(host, "giro.ceo")).toBe(false),
  );

  it("em homologação a lista sai do DOMINIO_BASE de lá", () => {
    expect(mostraLanding("homolog.giro.ceo", "homolog.giro.ceo")).toBe(true);
    expect(mostraLanding("www.homolog.giro.ceo", "homolog.giro.ceo")).toBe(true);
    expect(mostraLanding("motorapida.homolog.giro.ceo", "homolog.giro.ceo")).toBe(false);
    expect(mostraLanding("giro.ceo", "homolog.giro.ceo")).toBe(false);
  });

  it("sem DOMINIO_BASE (desenvolvimento) só localhost mostra a landing", () => {
    expect(mostraLanding("localhost:3000", undefined)).toBe(true);
    expect(mostraLanding("giro.ceo", undefined)).toBe(false);
    expect(mostraLanding("localhost:3000", "localhost")).toBe(true);
  });
});
