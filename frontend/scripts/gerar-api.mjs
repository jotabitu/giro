// Gera src/lib/api/schema.d.ts a partir de docs/api/openapi.yaml (tipos nunca à mão).
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const yaml = fileURLToPath(new URL("../../docs/api/openapi.yaml", import.meta.url));
const saida = fileURLToPath(new URL("../src/lib/api/schema.d.ts", import.meta.url));

if (!existsSync(yaml)) {
  console.warn("AVISO: docs/api/openapi.yaml ainda não existe (T-001/T-005); cliente não gerado.");
  process.exit(0);
}
const r = spawnSync("npx", ["openapi-typescript", yaml, "-o", saida], { stdio: "inherit", shell: true });
process.exit(r.status ?? 1);
