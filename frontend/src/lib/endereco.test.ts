import { describe, expect, it } from "vitest";
import { enderecoSemEmpresa } from "./endereco";

describe("enderecoSemEmpresa", () => {
  it.each(["localhost", "admin.localhost", "127.0.0.1", "admin.giro.com.br", "ADMIN.localhost"])("%s não é de locadora", (host) => {
    expect(enderecoSemEmpresa(host)).toBe(true);
  });
  it.each(["motorapida.localhost", "motorapida.giro.com.br", "adminvolta.localhost"])("%s é de locadora", (host) => {
    expect(enderecoSemEmpresa(host)).toBe(false);
  });
});
