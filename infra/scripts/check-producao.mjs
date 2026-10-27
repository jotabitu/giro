// Regras do compose de produção (T-373, ADR 0033), sobre a saída de `docker compose config --format json`.
// Uso: node infra/scripts/check-producao.mjs <config.json>
import { readFileSync } from "node:fs";

const config = JSON.parse(readFileSync(process.argv[2], "utf8"));
const servicos = config.services;
const erros = [];
const amb = (s, v) => String(servicos[s]?.environment?.[v] ?? "");

// 1. Só o proxy publica porta, e só 80 e 443 (a porta de dentro).
for (const [nome, s] of Object.entries(servicos)) {
  const publicadas = s.ports ?? [];
  if (nome === "proxy") {
    const alvos = publicadas.map((p) => Number(p.target)).sort((a, b) => a - b);
    if (alvos.join() !== "80,443") erros.push(`proxy deve publicar só 80 e 443, publica: ${alvos.join() || "nada"}`);
  } else if (publicadas.length) {
    erros.push(`${nome} publica porta; só o proxy pode`);
  }
}

// 2. DATABASE_URL_MIGRACAO só no migrar e no worker-apagamento (ADR 0016, 0025; M-01).
const comMigracao = new Set(["migrar", "worker-apagamento"]);
for (const nome of Object.keys(servicos)) {
  const tem = amb(nome, "DATABASE_URL_MIGRACAO") !== "";
  if (tem && !comMigracao.has(nome)) erros.push(`${nome} recebe a DATABASE_URL_MIGRACAO`);
  if (!tem && comMigracao.has(nome)) erros.push(`${nome} não recebe a DATABASE_URL_MIGRACAO`);
}

// 3. O worker do apagamento lê só a fila `apagamento`, e o worker comum não a lê.
const filas = (s) => {
  const c = servicos[s]?.command ?? [];
  const i = c.indexOf("-Q");
  return i >= 0 ? c[i + 1].split(",") : [];
};
if (filas("worker-apagamento").join() !== "apagamento") erros.push("worker-apagamento deve ler só a fila apagamento");
if (filas("worker").includes("apagamento")) erros.push("worker comum não pode ler a fila apagamento");

// 4. A aplicação não recebe segredo de infraestrutura (backup, DNS, banco como superusuário).
const so_da_infra = /^(PGBACKREST_|RESTIC_|AWS_|ARQUIVOS_S3_|CLOUDFLARE|ALERTA_|POSTGRES_PASSWORD|REDIS_SENHA)/;
for (const nome of ["backend", "worker", "worker-apagamento", "beat", "migrar", "estaticos", "frontend", "proxy"]) {
  for (const v of Object.keys(servicos[nome]?.environment ?? {})) {
    if (so_da_infra.test(v)) erros.push(`${nome} recebe ${v}, que é só da infraestrutura`);
  }
}
if (servicos.frontend?.env_file) erros.push("frontend não deve ler o arquivo de variáveis da aplicação");

// 5. O backup está cifrado e com retenção de 30 dias.
if (amb("db", "PGBACKREST_REPO1_CIPHER_TYPE") !== "aes-256-cbc") erros.push("pgBackRest sem cifra aes-256-cbc");
if (amb("db", "PGBACKREST_REPO1_RETENTION_FULL") !== "30") erros.push("retenção do pgBackRest diferente de 30 dias");

// 6. Banco e Redis nunca na rede do proxy por porta, e Redis exige senha.
const cmdRedis = (servicos.redis?.command ?? []).join(" ");
if (!cmdRedis.includes("--requirepass")) erros.push("redis sem --requirepass");

if (erros.length) {
  console.error("Compose de produção fora das regras:\n- " + erros.join("\n- "));
  process.exit(1);
}
console.log("Compose de produção ok: só o proxy publica 80 e 443; migração só no migrar e no worker-apagamento; backup cifrado, 30 dias");
