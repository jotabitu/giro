import { afterEach, describe, expect, it, vi } from "vitest";
import { urlDaApi } from "./config";

afterEach(() => vi.unstubAllEnvs());

describe("urlDaApi", () => {
  it("no servidor prefere API_URL_INTERNA", () => {
    vi.stubEnv("API_URL_INTERNA", "http://backend:8000/");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    expect(urlDaApi()).toBe("http://backend:8000");
  });

  it("cai para NEXT_PUBLIC_API_URL e depois para o padrão", () => {
    vi.stubEnv("API_URL_INTERNA", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:9000");
    expect(urlDaApi()).toBe("http://localhost:9000");
  });
});
