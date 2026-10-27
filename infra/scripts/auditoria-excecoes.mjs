// Apoio de infra/scripts/auditoria-deps.sh (T-361): lê infra/auditoria/excecoes.txt.
//   node auditoria-excecoes.mjs listar <pip|npm>   imprime os IDs aceitos, um por linha
//   node auditoria-excecoes.mjs npm                lê `npm audit --json` na entrada padrão e falha
//                                                  com aviso alto ou crítico sem exceção válida
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const arquivo = join(dirname(fileURLToPath(import.meta.url)), "..", "auditoria", "excecoes.txt");
const hoje = new Date().toISOString().slice(0, 10);

function ler() {
  const lista = [];
  const erros = [];
  readFileSync(arquivo, "utf8").split(/\r?\n/).forEach((linha, i) => {
    if (!linha.trim() || linha.trim().startsWith("#")) return;
    const [tipo, id, validade, ...resto] = linha.split("|").map((p) => p.trim());
    const justificativa = resto.join("|").trim();
    if (!["pip", "npm"].includes(tipo) || !id || !/^\d{4}-\d{2}-\d{2}$/.test(validade ?? "") || !justificativa) {
      erros.push(`excecoes.txt linha ${i + 1}: formato inválido`);
    } else if (validade < hoje) {
      erros.push(`excecoes.txt linha ${i + 1}: exceção de ${id} venceu em ${validade}`);
    } else {
      lista.push({ tipo, id });
    }
  });
  if (erros.length) {
    console.error(erros.join("\n"));
    process.exit(2);
  }
  return lista;
}

const [comando, alvo] = process.argv.slice(2);
const aceitos = ler();

if (comando === "listar") {
  aceitos.filter((e) => e.tipo === alvo).forEach((e) => console.log(e.id));
} else if (comando === "npm") {
  const permitidos = new Set(aceitos.filter((e) => e.tipo === "npm").map((e) => e.id));
  const relatorio = JSON.parse(readFileSync(0, "utf8"));
  const abertos = [];
  for (const [pacote, v] of Object.entries(relatorio.vulnerabilities ?? {})) {
    for (const via of v.via) {
      if (typeof via !== "object" || !["high", "critical"].includes(via.severity)) continue;
      const ghsa = String(via.url).split("/").pop();
      if (!permitidos.has(ghsa)) abertos.push(`${via.severity.padEnd(8)} ${pacote}: ${via.title} (${ghsa})`);
    }
  }
  if (abertos.length) {
    console.error("npm audit: avisos alto ou crítico sem exceção:\n" + [...new Set(abertos)].join("\n"));
    process.exit(1);
  }
  console.log("npm audit: nenhum aviso alto ou crítico sem exceção");
} else {
  console.error("uso: auditoria-excecoes.mjs listar <pip|npm> | npm");
  process.exit(2);
}
