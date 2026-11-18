import { describe, expect, it } from "vitest";
import { mostraLanding } from "./host-landing";

describe("host da landing (T-489)", () => {
  it.each(["giro.ceo", "www.giro.ceo", "WWW.Giro.ceo", "giro.ceo:443", "localhost:3000", "127.0.0.1:3000", "homolog.giro.ceo"])(
    "%s mostra a landing em /",
    (host) => expect(mostraLanding(host)).toBe(true),
  );

  it.each(["motorapida.giro.ceo", "admin.giro.ceo", "motorapida.localhost:3000", "motorapida.homolog.giro.ceo", "giro.ceo.exemplo.com", "", null])(
    "%s continua indo para /entrar",
    (host) => expect(mostraLanding(host)).toBe(false),
  );
});
